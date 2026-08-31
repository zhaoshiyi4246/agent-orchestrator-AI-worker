#!/usr/bin/env python
"""closed-loop-v2 one-command mission runner.

Usage (from the closed-loop-v2 directory):
    PYTHONPATH=src .venv/Scripts/python.exe run_mission.py tasks/mission-quick.json
    ... add --dry-run to preflight Planner decomposition without touching AO.

Wires: config -> AO daemon -> MissionController (Planner/Auditor/Verifier via
Codex CLI; Workers temporarily created by the legacy AO harness;
Observer/Gate use no model) -> LoopBus projection -> memory.md / project.md
-> FINAL_REPORT.

The same wiring is importable (build_runtime / run_loop) so the web panel
drives the EXACT code path this CLI validates — no second implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from loopcore.action_executor import ActionExecutor          # noqa: E402
from loopcore.ao_adapter import AOAdapter                    # noqa: E402
from loopcore.auditor import CodexCliAuditorProvider         # noqa: E402
from loopcore.bus import BusConfig, LoopBus                  # noqa: E402
from loopcore.bus_projector import StoreBusProjector         # noqa: E402
from loopcore.memory import ProjectMemory                    # noqa: E402
from loopcore.mission import MISSION_TERMINAL, MissionController  # noqa: E402
from loopcore.mission_contracts import MissionSpec           # noqa: E402
from loopcore.mission_gate import IntegrationGate            # noqa: E402
from loopcore.planner_adapter import CodexCliPlannerProvider       # noqa: E402
from loopcore.state_store import StateStore                  # noqa: E402
from loopcore.verifier import CodexCliVerifierProvider       # noqa: E402

AO_BIN = r"E:\智理杯智能体大赛\ao-app\resources\daemon\ao.exe"
AO_DATA_DIR = r"E:\智理杯智能体大赛\ao-data"
AO_RUN_FILE = str(Path(AO_DATA_DIR) / "ao.run")


def setup_environment() -> None:
    """Process-level env every entry point needs (CLI, panel, scripts).

    This only configures AO daemon discovery and the venv-first PATH for the
    integration gate. Codex role providers do not use llm_env.
    """
    os.environ.setdefault("AO_DATA_DIR", AO_DATA_DIR)
    os.environ.setdefault("AO_RUN_FILE", AO_RUN_FILE)
    # the mission gate runs `python -m pytest` argv-style: make sure the
    # venv python (with pytest) wins PATH resolution.
    venv_scripts = str(ROOT / ".venv" / "Scripts")
    if venv_scripts not in os.environ.get("PATH", ""):
        os.environ["PATH"] = venv_scripts + os.pathsep + \
            os.environ.get("PATH", "")


def load_config() -> dict:
    return yaml.safe_load(
        (ROOT / "config" / "default.yaml").read_text("utf-8"))


def build_planner(cfg: dict, *, timeout: int = 180,
                  codex_bin: str = "codex",
                  cwd: Path | None = None) -> CodexCliPlannerProvider:
    """Build the one production Planner used by normal and dry-run paths."""
    roles = cfg.get("roles") or {}
    planner_cfg = roles.get("planner") or {}
    model = planner_cfg.get("model") or "gpt-5.6-sol"
    return CodexCliPlannerProvider(
        model=model,
        timeout=timeout,
        codex_bin=codex_bin,
        cwd=cwd or ROOT,
    )


class MissionRuntime:
    """Everything a running (or resumable) mission is made of."""

    def __init__(self, mission_dict: dict, cfg: dict, *, dry_run: bool = False):
        self.mission_dict = mission_dict
        self.cfg = cfg
        self.dry_run = dry_run
        self.runtime = ROOT / "runtime" / mission_dict["mission_id"]
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.store = StateStore(str(self.runtime / "state.db"))
        self.adapter = AOAdapter()
        wcfg = cfg.get("worker") or {}
        self.executor = ActionExecutor(
            ao_bin=AO_BIN, data_dir=AO_DATA_DIR, run_file=AO_RUN_FILE,
            store=self.store,
            worker_model=wcfg.get("model", ""),
            max_spawn_attempts=int(wcfg.get("spawn_max_attempts", 3)),
            spawn_backoff_seconds=int(wcfg.get("spawn_backoff_seconds", 30)),
            max_transient_spawn_attempts=int(
                wcfg.get("spawn_max_transient_attempts", 8)),
            transient_spawn_backoff_seconds=int(
                wcfg.get("spawn_transient_backoff_seconds", 90)))
        self.gate = IntegrationGate(self.store)
        planner = build_planner(cfg, timeout=180, cwd=ROOT)
        roles = cfg.get("roles") or {}
        auditor_cfg = roles.get("auditor") or {}
        verifier_cfg = roles.get("verifier") or {}
        auditor = CodexCliAuditorProvider(
            model=auditor_cfg.get("model") or "gpt-5.6-sol",
            timeout=120, cwd=ROOT)
        verifier = CodexCliVerifierProvider(
            model=verifier_cfg.get("model") or "gpt-5.6-sol",
            timeout=120, cwd=ROOT)
        # Keep references for lifecycle introspection and compatibility with
        # any provider that exposes optional cleanup.
        self._planner = planner
        self._auditor = auditor
        self._verifier = verifier
        self.mission = MissionSpec.from_dict(mission_dict)
        self.controller = MissionController(
            self.mission, cfg,
            planner=planner, auditor=auditor, verifier=verifier,
            executor=self.executor, adapter=self.adapter, gate=self.gate,
            store=self.store, dry_run=dry_run)
        bus_cfg = cfg.get("bus") or {}
        self.bus = LoopBus(BusConfig(
            max_hops_per_thread=int(bus_cfg.get("max_hops_per_thread", 24)),
            max_audits_per_thread=int(bus_cfg.get("max_audits_per_thread", 3)),
            overall_timeout_seconds=float(
                bus_cfg.get("overall_timeout_seconds", 600))))
        # run memory lands in runtime/, never pollutes the target repo
        self.memory = ProjectMemory(str(self.runtime))
        self.projector = StoreBusProjector(
            self.store, self.bus, self.memory,
            traffic_log=self.runtime / "bus_traffic.jsonl")

    def close(self) -> None:
        """Release optional provider resources and sqlite. Idempotent.
        The panel calls this when a mission is unloaded; the CLI path relies
        on process exit, but close() keeps long-running panel use leak-free."""
        for prov in (self._planner, self._auditor, self._verifier):
            fn = getattr(prov, "close", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
        try:
            self.store.close()
        except Exception:
            pass


def build_runtime(mission_dict: dict, cfg: dict, *,
                  dry_run: bool = False) -> MissionRuntime:
    return MissionRuntime(mission_dict, cfg, dry_run=dry_run)


def run_loop(rt: MissionRuntime, *, cap_seconds: float = 300.0,
             poll_seconds: float = 5.0, on_tick=None,
             should_stop=None) -> dict:
    """Drive the controller until terminal / cap / external stop.

    on_tick(result, projected_n, elapsed) fires every iteration (the panel
    uses it for heartbeats); should_stop() lets the panel abort without
    killing the thread (state stays resumable in the store).
    """
    started = time.monotonic()
    while True:
        result = rt.controller.step()
        n = rt.projector.project_once()
        state = result.get("state", "?")
        elapsed = time.monotonic() - started
        if on_tick:
            try:
                on_tick(result, n, elapsed)
            except Exception:
                pass
        if state in MISSION_TERMINAL:
            break
        if elapsed >= cap_seconds:
            break
        if should_stop and should_stop():
            break
        time.sleep(poll_seconds)
    rt.projector.project_once()
    return {
        "mission_id": rt.mission.mission_id,
        "final_state": rt.controller.state,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "bus_envelopes": len(rt.projector.projected),
        "bus_errors": rt.projector.errors,
        "runtime_dir": str(rt.runtime),
        "memory_md": str(rt.memory.memory_path),
        "project_md": str(rt.memory.project_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission_json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--poll-seconds", type=float, default=5.0)
    ap.add_argument("--cap-seconds", type=float, default=300.0,
                    help="hard wall-clock cap for this runner (default 5 min)")
    args = ap.parse_args()

    try:
        mission_dict = json.loads(Path(args.mission_json).read_text("utf-8"))
    except Exception as exc:
        if args.dry_run:
            print("planning dry-run error: invalid mission JSON: %s" % exc,
                  file=sys.stderr)
            return 2
        raise
    cfg = load_config()

    if args.dry_run:
        try:
            if not isinstance(mission_dict, dict):
                raise ValueError("mission must be a JSON object")
            for field in ("allowed_paths", "forbidden_paths",
                          "acceptance_criteria", "gate_commands"):
                if not isinstance(mission_dict.get(field), list):
                    raise ValueError("%s must be a list" % field)
            if not isinstance(mission_dict.get("budgets", {}), dict):
                raise ValueError("budgets must be an object")
            if not all(isinstance(path, str)
                       for path in mission_dict["allowed_paths"]
                       + mission_dict["forbidden_paths"]):
                raise ValueError("mission paths must be strings")
            if not all(isinstance(command, str)
                       for command in mission_dict["gate_commands"]):
                raise ValueError("gate_commands entries must be strings")
            if not all(isinstance(item, dict) and item.get("id")
                       and item.get("description")
                       for item in mission_dict["acceptance_criteria"]):
                raise ValueError(
                    "acceptance criteria require id and description")
            mission = MissionSpec.from_dict(mission_dict)
            if not mission.mission_id or not mission.project_id \
                    or not mission.objective:
                raise ValueError(
                    "mission_id, project_id, and objective are required")
            if not mission.allowed_paths:
                raise ValueError("allowed_paths must be non-empty")
            if not mission.acceptance_criteria:
                raise ValueError("acceptance_criteria must be non-empty")
            max_subtasks = int(
                (mission.budgets or {}).get("max_subtasks", 5) or 5)
            if max_subtasks < 1:
                raise ValueError("budgets.max_subtasks must be positive")
            planner = build_planner(cfg, timeout=180, cwd=ROOT)
            plan = planner.plan_decompose(
                mission.to_dict(), "DECOMP-%s" % mission.mission_id)
            summary = {
                "mission_id": mission.mission_id,
                "dry_run": True,
                "planner_provider": type(planner).__name__,
                "model": planner.model,
                "subtask_count": len(plan.subtasks),
                "plan": plan.to_dict(),
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2),
                  flush=True)
            return 0
        except Exception as exc:
            detail = str(exc).replace("\r", " ").replace("\n", " ")[:400]
            print("planning dry-run error: %s" % detail, file=sys.stderr)
            return 2

    setup_environment()
    rt = build_runtime(mission_dict, cfg, dry_run=False)

    print(f"[runner] mission={rt.mission.mission_id} "
          f"project={rt.mission.project_id} dry_run={args.dry_run} "
          f"cap={args.cap_seconds:g}s", flush=True)

    def _tick(result, n, elapsed):
        print(f"[runner] {elapsed:6.1f}s state={result.get('state', '?')} "
              f"acted={result.get('acted')} bus+{n}", flush=True)

    summary = run_loop(rt, cap_seconds=args.cap_seconds,
                       poll_seconds=args.poll_seconds, on_tick=_tick)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if summary["final_state"] == "MISSION_DONE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Mission layer tests: decompose -> dispatch N workers -> merge -> DONE.

Fakes only; temp SQLite; no real AO/Claude/git-remote. Verifies the core
promise: ONE user instruction drives multiple workers through their own
closed loops to a merged, verified MISSION_DONE — with budgets halting
runaways.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from loopcore.action_executor import ActionExecutor, ActionResult
from loopcore.auditor import FakeAuditorProvider
from loopcore.mission_contracts import (MissionSpec, PlannerAction, PlannerActionType,
                           ProjectState)
from loopcore.mission_gate import IntegrationGate
from loopcore.mission import MissionController
from loopcore.event_observer import Observer
from loopcore.planner_adapter import FakePlannerProvider
from loopcore.state_store import StateStore
from loopcore.verifier import FakeVerifierProvider
from tests.sidecar_port.test_budgets import _cfg


MISSION = {
    "mission_id": "MIS-TEST-1",
    "project_id": "closed-loop-demo",
    "objective": "实现 divide 和 multiply 两个函数",
    "allowed_paths": ["app.py", "math2.py"],
    "forbidden_paths": ["tests/**", ".git/**"],
    "acceptance_criteria": [
        {"id": "AC-01", "description": "divide(6,3)==2"},
        {"id": "AC-02", "description": "multiply(2,3)==6"},
    ],
    "gate_commands": ["python -m pytest -q"],
    "user_instruction": "测试全绿即完成；禁止改 tests/",
    "budgets": {"max_subtasks": 3, "max_total_replans": 2,
                "max_runtime_seconds": 1800},
}


def _mc(tmp_path, *, dry=False):
    store = StateStore(tmp_path / "m.db")
    adapter = MagicMock()
    adapter.get_recent_events.return_value = []
    adapter.get_worker_status.return_value = {"id": "w", "status": "idle",
                                              "activity": {"state": "idle"}}
    ex = ActionExecutor("ao", "d", "r", store)
    gate = IntegrationGate(store)
    mc = MissionController(
        mission=MissionSpec.from_dict(MISSION), cfg=_cfg(),
        planner=FakePlannerProvider(), auditor=FakeAuditorProvider(),
        verifier=FakeVerifierProvider(), executor=ex, adapter=adapter,
        gate=gate, store=store, dry_run=dry)
    return mc, store


def test_decompose_creates_two_subtask_loops(tmp_path):
    mc, store = _mc(tmp_path)
    r = mc.step()      # first step: decomposition
    assert r["acted"]
    assert mc.plan is not None
    assert len(mc.plan.subtasks) == 2
    assert set(mc.tasks) == {s.subtask_id for s in mc.plan.subtasks}
    # each subtask spec records subtask_of (attribution)
    for t in mc.tasks.values():
        assert t.subtask_of == "MIS-TEST-1"
    # each loop carries the user instruction (leader absorbs it)
    for loop in mc.loops.values():
        assert loop.instruct == "测试全绿即完成；禁止改 tests/"
        assert callable(loop.board)


def test_dispatch_respects_dependencies(tmp_path):
    """Fake decompose makes S2 depend on S1: only S1 spawns first."""
    mc, store = _mc(tmp_path)
    mc.step()          # decompose
    spawned = {}
    def fake_spawn(task):
        sid = "sess-" + task.task_id[-2:]
        spawned[task.task_id] = sid
        return sid
    mc.adapter.get_session_workspace.return_value = str(tmp_path)
    with patch.object(mc.executor, "spawn_initial_worker",
                      side_effect=fake_spawn), \
            patch("loopcore.mission.wt.freeze_base", return_value="BASE") as freeze:
        mc.step()      # dispatch
    s1 = [s for s in mc.plan.subtasks if not s.dependencies][0].subtask_id
    s2 = [s for s in mc.plan.subtasks if s.dependencies][0].subtask_id
    assert s1 in spawned
    assert s2 not in spawned          # dep not DONE yet -> held
    # mark S1 DONE -> S2 becomes dispatchable on the next step
    store.record_transition(task_id=s1, from_state="WORKER_RUNNING",
                            to_state="DONE", actor="t", reason="t",
                            evidence={})
    with patch.object(mc.executor, "spawn_initial_worker",
                      side_effect=fake_spawn), \
            patch("loopcore.mission.wt.freeze_base", return_value="BASE"):
        mc.step()
    assert s2 in spawned
    assert freeze.call_args.args[0] == str(tmp_path)
    assert mc.adapter.get_session_workspace.call_args_list[0].args == (
        spawned[s1],)


def test_dispatch_workspace_failure_halts_mission(tmp_path):
    from loopcore.ao_adapter import AOError

    mc, store = _mc(tmp_path)
    mc.step()
    mc.adapter.get_session_workspace.side_effect = AOError(
        "SESSION_WORKSPACE_NOT_FOUND")

    with patch.object(mc.executor, "spawn_initial_worker",
                      return_value="sess-missing"), \
            patch.object(mc.executor, "kill_worker") as kill, \
            patch("loopcore.mission.wt.freeze_base") as freeze:
        result = mc.step()

    assert result["state"] == "HUMAN"
    assert any(t.worker_session_id == "sess-missing"
               for t in mc.tasks.values())
    mc.adapter.get_session_workspace.assert_called_once_with("sess-missing")
    freeze.assert_not_called()
    kill.assert_called_once_with("sess-missing")


def _bind_done_worker(mc, store, session_id="sess-done"):
    sid = next(iter(mc.tasks))
    task = mc.tasks[sid]
    task.worker_session_id = session_id
    store.record_task(task.task_id, task.to_dict())
    store.record_transition(task_id=sid, from_state="TASK_READY",
                            to_state="WORKER_RUNNING", actor="t", reason="t",
                            evidence={})
    store.record_transition(task_id=sid, from_state="WORKER_RUNNING",
                            to_state="DONE", actor="t", reason="t",
                            evidence={})
    return sid, task


def test_merge_resolves_workspace_before_kill_and_uses_actual_path(tmp_path):
    mc, store = _mc(tmp_path)
    mc.step()
    sid, task = _bind_done_worker(mc, store)
    worker = tmp_path / "actual-worker"
    worker.mkdir()
    integration = tmp_path / "integration"
    order = []

    def workspace(session_id):
        order.append(("workspace", session_id))
        return str(worker)

    def kill(session_id):
        order.append(("kill", session_id))

    def commit(path, _message):
        order.append(("commit", path))
        return "abc123"

    def integration_wt(*, source_worktree=None):
        order.append(("integration", source_worktree))
        return str(integration)

    def merge(target, source):
        order.append(("merge", target, source))
        return MagicMock(status="ok")

    mc.adapter.get_session_workspace.side_effect = workspace
    mc.executor.kill_worker = kill
    with patch("loopcore.mission.wt.commit_all", side_effect=commit), \
            patch.object(mc, "_integration_wt",
                         side_effect=integration_wt), \
            patch("loopcore.mission.wt.merge_worktree", side_effect=merge):
        mc._merge_done()

    assert order == [
        ("workspace", task.worker_session_id),
        ("kill", task.worker_session_id),
        ("commit", str(worker)),
        ("integration", str(worker)),
        ("merge", str(integration), str(worker)),
    ]
    assert sid in mc.merged


def test_merge_workspace_failure_halts_before_commit(tmp_path):
    from loopcore.ao_adapter import AOError

    mc, store = _mc(tmp_path)
    mc.step()
    _sid, task = _bind_done_worker(mc, store, "sess-gone")
    order = []

    def missing(session_id):
        order.append(("workspace", session_id))
        raise AOError("SESSION_WORKSPACE_NOT_FOUND")

    def kill(session_id):
        order.append(("kill", session_id))

    mc.adapter.get_session_workspace.side_effect = missing
    mc.executor.kill_worker = kill
    with patch("loopcore.mission.wt.commit_all") as commit:
        mc._merge_done()

    assert mc.state == "HUMAN"
    assert order == [
        ("workspace", task.worker_session_id),
        ("kill", task.worker_session_id),
    ]
    commit.assert_not_called()


def test_full_mission_to_done_with_merge(tmp_path):
    """End-to-end fake run: 2 subtasks DONE -> merge -> final verify PASS."""
    import subprocess
    # real mini git repo with two AO Session workspaces
    data_dir = tmp_path / "ao-data"
    proj = data_dir / "worktrees" / "closed-loop-demo"
    proj.mkdir(parents=True)
    def _git(cwd, *a):
        subprocess.run(["git", "-C", str(cwd), *a], capture_output=True)
    _git(proj, "init", "-q")
    _git(proj, "config", "user.name", "t")
    _git(proj, "config", "user.email", "t@t")
    (proj / "app.py").write_text("x=1\n", encoding="utf-8")
    _git(proj, "add", "-A"); _git(proj, "commit", "-q", "-m", "init")
    # worker worktrees (as AO would create per session)
    wts = {}
    for name in ("sess-S1", "sess-S2"):
        p = proj / name
        subprocess.run(["git", "-C", str(proj), "worktree", "add", "-q",
                        "-b", name, str(p)], capture_output=True)
        wts[name] = p
    (wts["sess-S1"] / "app.py").write_text("def divide(a,b):\n"
        "    if b==0: raise ValueError\n    return a/b\n", encoding="utf-8")
    (wts["sess-S2"] / "math2.py").write_text(
        "def multiply(a,b): return a*b\n", encoding="utf-8")
    mc, store = _mc(tmp_path)
    mc.adapter.get_session_workspace.side_effect = (
        lambda session_id: str(wts[session_id]))
    mc.step()        # decompose
    spawned = {}
    def fake_spawn(task):
        sid = "sess-" + task.task_id[-2:]
        spawned[task.task_id] = sid
        return sid
    # seed both subtasks as DONE (unit test of the merge/final stage)
    with patch.object(mc.executor, "spawn_initial_worker",
                      side_effect=fake_spawn):
        mc.step()    # dispatch S1 only (S2 dep)
    s1 = [s for s in mc.plan.subtasks if not s.dependencies][0].subtask_id
    s2 = [s for s in mc.plan.subtasks if s.dependencies][0].subtask_id
    store.record_transition(task_id=s1, from_state="WORKER_RUNNING",
                            to_state="DONE", actor="t", reason="t",
                            evidence={})
    with patch.object(mc.executor, "spawn_initial_worker",
                      side_effect=fake_spawn):
        mc.step()    # S2 dispatch; S1 merge happens
    assert s1 in mc.merged, "S1 merged into integration worktree"
    store.record_transition(task_id=s2, from_state="WORKER_RUNNING",
                            to_state="DONE", actor="t", reason="t",
                            evidence={})
    # Merge S2 while its AO Session workspace remains available.
    mc._merge_done()
    assert s2 in mc.merged
    # Final verification must reuse the CL-AO integration worktree without
    # consulting either terminated Worker Session.
    from loopcore.ao_adapter import AOError
    mc.adapter.get_session_workspace.reset_mock()
    mc.adapter.get_session_workspace.side_effect = AOError(
        "SESSION_WORKSPACE_NOT_FOUND")
    gate_ok = MagicMock(ok=True, results=[
        {"command": "pytest", "stdout": "4 passed", "stderr": ""}])
    with patch.object(IntegrationGate, "run", return_value=gate_ok):
        r = mc.step()
    assert r["state"] == "MISSION_DONE"
    mc.adapter.get_session_workspace.assert_not_called()
    # merged tree contains both subtask outputs
    integ = Path(store.path).parent / "integration"
    assert data_dir not in integ.parents
    assert "divide" in (integ / "app.py").read_text(encoding="utf-8")
    assert (integ / "math2.py").exists()


def test_mission_runtime_budget_halts(tmp_path):
    mc, store = _mc(tmp_path)
    mc.step()
    store.counter_set("mission_started_at:MIS-TEST-1", 1)  # ancient start
    r = mc.step()
    assert r["state"] == "HUMAN"


def test_mission_follows_subtask_human(tmp_path):
    """All subtasks HUMAN (none dispatchable) -> mission HUMAN, watch stops."""
    mc, store = _mc(tmp_path)
    mc.step()
    for sid in mc.tasks:
        store.record_transition(task_id=sid, from_state="WORKER_RUNNING",
                                to_state="HUMAN", actor="budget",
                                reason="max_runtime_seconds exceeded",
                                evidence={})
    r = mc.step()
    assert r["state"] == "HUMAN"
    assert "halted for human" in mc._read_state().get("reason", "")


def test_mission_follows_subtask_failed(tmp_path):
    """A FAILED subtask fails the mission (cannot deliver full scope)."""
    mc, store = _mc(tmp_path)
    mc.step()
    sids = list(mc.tasks)
    store.record_transition(task_id=sids[0], from_state="WORKER_RUNNING",
                            to_state="FAILED", actor="t", reason="t",
                            evidence={})
    r = mc.step()
    assert r["state"] == "FAILED"


def test_progress_board_shape(tmp_path):
    mc, store = _mc(tmp_path)
    mc.step()
    board = mc._progress_board()
    assert board["mission_id"] == "MIS-TEST-1"
    assert len(board["subtasks"]) == 2
    assert board["user_instruction"] == "测试全绿即完成；禁止改 tests/"
    assert all("state" in s and "worker_session_id" in s
               for s in board["subtasks"])


def test_dry_run_never_spawns(tmp_path):
    mc, store = _mc(tmp_path, dry=True)
    with patch.object(mc.executor, "spawn_initial_worker") as sp:
        mc.step()   # decompose
        mc.step()   # would dispatch
        sp.assert_not_called()

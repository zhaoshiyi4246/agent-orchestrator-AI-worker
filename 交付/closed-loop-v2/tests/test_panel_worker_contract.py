"""Keep the Panel's production Mission payload on the Codex Worker contract."""

from __future__ import annotations

import ast
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1] / "panel" / "server.py"


def test_panel_mission_payload_uses_codex_worker_harness():
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    start_mission = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_start_mission"
    )
    mission_dict = next(
        node.value for node in start_mission.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "mission"
                for target in node.targets)
        and isinstance(node.value, ast.Dict)
    )
    harness_values = [
        value.value
        for key, value in zip(mission_dict.keys, mission_dict.values)
        if isinstance(key, ast.Constant) and key.value == "worker_harness"
        and isinstance(value, ast.Constant)
    ]

    assert harness_values == ["codex"]
    assert not any(
        isinstance(node, ast.Constant) and node.value == "claude-code"
        for node in ast.walk(start_mission)
    )


def test_panel_and_cli_share_build_runtime():
    panel_tree = ast.parse(SERVER.read_text(encoding="utf-8"))
    runner = SERVER.parents[1] / "run_mission.py"
    runner_tree = ast.parse(runner.read_text(encoding="utf-8"))

    def calls_build_runtime(tree, owner=None):
        scope = tree
        if owner:
            scope = next(
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == owner)
        return any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "run_mission"
            and node.func.attr == "build_runtime"
            for node in ast.walk(scope)
        ) if owner else any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "build_runtime"
            for node in ast.walk(scope)
        )

    assert calls_build_runtime(panel_tree, "start_mission")
    assert calls_build_runtime(runner_tree)

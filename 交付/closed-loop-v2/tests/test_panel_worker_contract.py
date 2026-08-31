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

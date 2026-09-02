"""Keep the Panel's production Mission payload on the Codex Worker contract."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from panel import server as panel_server


SERVER = Path(__file__).resolve().parents[1] / "panel" / "server.py"
INDEX = SERVER.with_name("index.html")


def _start_panel_mission(monkeypatch, tmp_path, max_subtasks=...):
    start = MagicMock()
    monkeypatch.setattr(panel_server, "ROOT", tmp_path)
    monkeypatch.setattr(panel_server.PANEL, "start_mission", start)
    body = {
        "objective": "implement one function",
        "allowed_paths": "app.py",
        "acceptance_criteria": "the function works",
        "gate_commands": "python -m pytest -q",
    }
    if max_subtasks is not ...:
        body["max_subtasks"] = max_subtasks
    result = panel_server.Handler._start_mission(object(), body)
    assert result["ok"] is True
    return start.call_args.args[0]


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


def test_panel_omitted_max_subtasks_defaults_to_one(monkeypatch, tmp_path):
    mission = _start_panel_mission(monkeypatch, tmp_path)
    assert mission["budgets"]["max_subtasks"] == 1


@pytest.mark.parametrize("value", [1, 2])
def test_panel_accepts_one_or_two_workers(monkeypatch, tmp_path, value):
    mission = _start_panel_mission(monkeypatch, tmp_path, value)
    assert mission["budgets"]["max_subtasks"] == value


@pytest.mark.parametrize("value", [0, -1, 3])
def test_panel_rejects_out_of_range_workers(monkeypatch, tmp_path, value):
    start = MagicMock()
    monkeypatch.setattr(panel_server, "ROOT", tmp_path)
    monkeypatch.setattr(panel_server.PANEL, "start_mission", start)
    body = {
        "objective": "implement one function",
        "allowed_paths": "app.py",
        "acceptance_criteria": "the function works",
        "gate_commands": "python -m pytest -q",
        "max_subtasks": value,
    }
    with pytest.raises(ValueError, match="must be 1 or 2"):
        panel_server.Handler._start_mission(object(), body)
    start.assert_not_called()


def test_panel_frontend_defaults_to_bounded_single_worker():
    html = INDEX.read_text(encoding="utf-8")
    assert ('id="f_sub" type="number" min="1" max="2" value="1"'
            in html)
    assert 'max_subtasks:Number($("f_sub").value)' in html
    assert 'max_subtasks:+$("f_sub").value||2' not in html

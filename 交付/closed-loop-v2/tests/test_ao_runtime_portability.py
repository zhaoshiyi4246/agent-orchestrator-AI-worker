"""Portable AO executable, runfile, endpoint, and CLI environment contract."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import run_mission
from loopcore.action_executor import ActionExecutor
from loopcore.ao_adapter import AOAdapter


def test_resolve_ao_bin_prefers_clao_override(tmp_path):
    executable = tmp_path / "ao.exe"
    executable.write_bytes(b"fake")

    def unexpected_which(_name):
        raise AssertionError("PATH lookup must not run for CLAO_AO_BIN")

    resolved = run_mission.resolve_ao_bin(
        environ={"CLAO_AO_BIN": str(executable)}, which=unexpected_which)
    assert resolved == str(executable)


def test_resolve_ao_bin_uses_path_when_unconfigured(tmp_path):
    executable = tmp_path / "ao.exe"
    executable.write_bytes(b"fake")
    calls = []

    def fake_which(name):
        calls.append(name)
        return str(executable)

    assert run_mission.resolve_ao_bin(environ={}, which=fake_which) == str(
        executable)
    assert calls == ["ao"]


def test_resolve_ao_bin_fails_fast_with_operator_hint():
    with pytest.raises(RuntimeError, match="CLAO_AO_BIN"):
        run_mission.resolve_ao_bin(environ={}, which=lambda _name: None)


def test_resolve_ao_run_file_default_and_override(tmp_path):
    assert run_mission.resolve_ao_run_file(
        environ={}, home=tmp_path) == tmp_path / ".ao" / "running.json"

    override = tmp_path / "custom" / "ao.json"
    assert run_mission.resolve_ao_run_file(
        environ={"CLAO_AO_RUN_FILE": str(override)},
        home=tmp_path) == override


def test_adapter_prefers_valid_runfile_port_then_config(tmp_path):
    run_file = tmp_path / "running.json"
    run_file.write_text('{"pid": 42, "port": 4567}', encoding="utf-8")

    dynamic = AOAdapter(
        base_url="http://127.0.0.1:4111", timeout=7, run_file=run_file)
    assert dynamic.base_url == "http://127.0.0.1:4567"
    assert dynamic.timeout == 7

    fallback = AOAdapter(
        base_url="http://127.0.0.1:4111", run_file=tmp_path / "missing")
    assert fallback.base_url == "http://127.0.0.1:4111"


def test_adapter_honors_ao_run_file_and_home_default(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit.json"
    explicit.write_text('{"port": 4568}', encoding="utf-8")
    monkeypatch.setenv("AO_RUN_FILE", str(explicit))
    assert AOAdapter().base_url == "http://127.0.0.1:4568"

    monkeypatch.delenv("AO_RUN_FILE")
    default = tmp_path / ".ao" / "running.json"
    default.parent.mkdir()
    default.write_text('{"port": 4569}', encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert AOAdapter().base_url == "http://127.0.0.1:4569"


def test_action_executor_only_adds_explicit_runfile(monkeypatch, tmp_path):
    monkeypatch.delenv("AO_DATA_DIR", raising=False)
    monkeypatch.delenv("AO_RUN_FILE", raising=False)
    run_file = tmp_path / "running.json"

    executor = ActionExecutor(
        "ao", str(tmp_path / "nonexistent-data"), str(run_file), object())
    child_env = executor._env()
    assert "AO_DATA_DIR" not in child_env
    assert child_env["AO_RUN_FILE"] == str(run_file)

    without_runfile = ActionExecutor("ao", None, None, object())._env()
    assert "AO_DATA_DIR" not in without_runfile
    assert "AO_RUN_FILE" not in without_runfile


def test_build_runtime_resolves_one_shared_ao_contract(monkeypatch, tmp_path):
    calls = {"bin": 0, "run_file": 0}
    captured = {}
    run_file = tmp_path / "running.json"

    def resolve_bin():
        calls["bin"] += 1
        return "fake-ao"

    def resolve_run_file():
        calls["run_file"] += 1
        return run_file

    class DummyRuntime:
        def __init__(self, mission, cfg, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(run_mission, "resolve_ao_bin", resolve_bin)
    monkeypatch.setattr(run_mission, "resolve_ao_run_file", resolve_run_file)
    monkeypatch.setattr(run_mission, "MissionRuntime", DummyRuntime)
    monkeypatch.delenv("AO_DATA_DIR", raising=False)

    run_mission.build_runtime({"mission_id": "M-PORTABLE"}, {})

    assert calls == {"bin": 1, "run_file": 1}
    assert captured["ao_bin"] == "fake-ao"
    assert captured["ao_run_file"] == run_file
    assert run_mission.os.environ["AO_RUN_FILE"] == str(run_file)
    assert "AO_DATA_DIR" not in run_mission.os.environ


def test_auto_ff_requires_explicit_legacy_data_root(monkeypatch):
    from panel import server

    monkeypatch.delenv("CLAO_AO_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="CLAO_AO_DATA_DIR"):
        server.ff_master_to_integration("M-PORTABLE", "project")


def test_portability_code_does_not_scan_registry_or_install_ao():
    tree = ast.parse(Path(run_mission.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "winreg" not in imported
    assert "requests" not in imported

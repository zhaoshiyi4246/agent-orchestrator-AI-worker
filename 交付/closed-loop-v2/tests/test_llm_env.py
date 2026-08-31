"""Legacy llm_env behavior and the Codex production-path boundary."""

from __future__ import annotations


def test_ensure_llm_env_sets_defaults(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_GIT_BASH_PATH", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    from loopcore import llm_env
    monkeypatch.setattr(llm_env, "find_git_bash", lambda: r"C:\git\bash.exe")
    llm_env.ensure_llm_env()
    import os
    assert os.environ["CLAUDE_CODE_GIT_BASH_PATH"] == r"C:\git\bash.exe"
    assert os.environ["ANTHROPIC_MODEL"] == llm_env.DEFAULT_MODEL


def test_ensure_llm_env_never_overrides_operator(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", r"D:\mine\bash.exe")
    monkeypatch.setenv("ANTHROPIC_MODEL", "custom-model")
    from loopcore import llm_env
    monkeypatch.setattr(llm_env, "find_git_bash", lambda: r"C:\git\bash.exe")
    llm_env.ensure_llm_env()
    import os
    assert os.environ["CLAUDE_CODE_GIT_BASH_PATH"] == r"D:\mine\bash.exe"
    assert os.environ["ANTHROPIC_MODEL"] == "custom-model"


def test_codex_audit_providers_do_not_set_anthropic_model(monkeypatch):
    import os
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    from loopcore.auditor import CodexCliAuditorProvider
    from loopcore.verifier import CodexCliVerifierProvider
    CodexCliAuditorProvider()
    CodexCliVerifierProvider()
    assert "ANTHROPIC_MODEL" not in os.environ


def test_production_setup_does_not_call_ensure_llm_env(monkeypatch):
    from loopcore import llm_env
    import run_mission
    monkeypatch.setattr(
        llm_env, "ensure_llm_env",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("production setup called legacy llm_env")))

    run_mission.setup_environment()

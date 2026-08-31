"""llm_env: Claude providers must self-sufficiently set the CLI env
(CLAUDE_CODE_GIT_BASH_PATH / ANTHROPIC_MODEL) without depending on
run_mission.py process setup — but never override operator values."""

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


def test_remaining_claude_providers_wire_ensure_env(monkeypatch):
    """Auditor and Verifier still call ensure_llm_env during R1-1."""
    import os
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    from loopcore.auditor import ClaudeCliAuditorProvider
    from loopcore.verifier import ClaudeCliVerifierProvider
    ClaudeCliAuditorProvider()
    assert os.environ.get("ANTHROPIC_MODEL")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    ClaudeCliVerifierProvider()
    assert os.environ.get("ANTHROPIC_MODEL")

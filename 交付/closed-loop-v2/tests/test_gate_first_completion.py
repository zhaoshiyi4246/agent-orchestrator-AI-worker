"""Gate-first completion regressions for a clean first Worker attempt."""
from unittest.mock import MagicMock, patch

from loopcore.mission_contracts import (
    AuditDecision,
    AuditEvidence,
    AuditResult,
    PlannerAction,
    PlannerActionType,
    ProjectState,
)
from tests.sidecar_port.test_verifier import _ScriptedVerifier, _loop
from tests.sidecar_port.util import ev


def _running_loop(tmp_path, *, gate_ok=True):
    verifier = _ScriptedVerifier("PASS")
    loop, task, store = _loop(
        tmp_path, verifier, fake_gate_run_ok=gate_ok)
    loop._transition(ProjectState.WORKER_RUNNING, "test", "setup", {})
    loop.adapter.get_worker_conversation.return_value = {"activities": []}
    return loop, task, store, verifier


def _completed_event(task, minute=0):
    return ev(
        "2026-09-02T00:%02d:00Z" % minute,
        project=task.project_id,
        worker=task.worker_session_id,
        etype="file_changed",
        progress=True,
        progress_strength="weak",
        message="modified app.py",
    )


def _to_retrying(loop):
    loop._transition(ProjectState.AUDIT_PENDING, "test", "setup", {})
    loop._transition(ProjectState.PLANNER_PENDING, "test", "setup", {})
    loop._transition(ProjectState.LOCAL_FIX_PENDING, "test", "setup", {})
    loop._transition(ProjectState.WORKER_RETRYING, "test", "setup", {})


def test_idle_changed_source_gate_pass_skips_completion_roles(tmp_path):
    loop, task, store, verifier = _running_loop(tmp_path)
    loop.auditor.audit = MagicMock()
    loop.planner.plan = MagicMock()
    loop._completion_audit = MagicMock()

    result = loop.step(injected_events=[_completed_event(task)])

    assert result == {"state": ProjectState.DONE, "acted": True}
    loop.gate.run.assert_called_once()
    loop._completion_audit.assert_not_called()
    loop.auditor.audit.assert_not_called()
    loop.planner.plan.assert_not_called()
    assert verifier.inputs == []
    transitions = store._conn.execute(
        "SELECT to_state FROM state_transitions "
        "WHERE task_id=? ORDER BY id", (task.task_id,)).fetchall()
    assert transitions == [
        (ProjectState.WORKER_RUNNING,),
        (ProjectState.GATE_PENDING,),
        (ProjectState.DONE,),
    ]


def test_idle_changed_source_gate_fail_uses_auditor_and_planner(tmp_path):
    loop, task, store, verifier = _running_loop(tmp_path, gate_ok=False)
    audit = AuditResult(
        "A-GATE-FIRST-FAIL", task.task_id, AuditDecision.HUMAN,
        [AuditEvidence("test_failure", "gate failed")],
        "gate failed", 1.0, ["AC-01"])
    loop.auditor.audit = MagicMock(return_value=audit)
    loop.planner.plan = MagicMock(return_value=PlannerAction(
        "ACT-GATE-FIRST-FAIL", task.task_id, PlannerActionType.HUMAN,
        reason="gate failure requires human"))
    loop.executor.execute = MagicMock(return_value=MagicMock(
        ok=True, new_state=ProjectState.HUMAN,
        new_worker_session_id=None, detail="halted"))

    result = loop.step(injected_events=[_completed_event(task)])

    assert result["state"] == ProjectState.HUMAN
    assert loop.state != ProjectState.DONE
    loop.gate.run.assert_called_once()
    loop.auditor.audit.assert_called_once()
    loop.planner.plan.assert_called_once()
    assert verifier.inputs == []
    transitions = store._conn.execute(
        "SELECT to_state FROM state_transitions "
        "WHERE task_id=? ORDER BY id", (task.task_id,)).fetchall()
    assert transitions[:4] == [
        (ProjectState.WORKER_RUNNING,),
        (ProjectState.GATE_PENDING,),
        (ProjectState.AUDIT_PENDING,),
        (ProjectState.PLANNER_PENDING,),
    ]


def test_empty_gate_commands_keep_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    task.gate_commands = []
    loop._completion_audit = MagicMock()

    loop.step(injected_events=[_completed_event(task)])

    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()


def test_no_changed_paths_keeps_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop._completion_audit = MagicMock()

    with patch("loopcore.closed_loop.wt.changed_paths", return_value=[]):
        loop.step(injected_events=[_completed_event(task)])

    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()


def test_unknown_changed_paths_keeps_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop._completion_audit = MagicMock()

    with patch("loopcore.closed_loop.wt.changed_paths", return_value=None):
        loop.step(injected_events=[_completed_event(task)])

    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()


def test_unresolved_workspace_keeps_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop.adapter.get_session_workspace.return_value = None
    loop._completion_audit = MagicMock()

    loop.step(injected_events=[_completed_event(task)])

    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()


def test_pending_approval_blocks_gate_first_completion(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    worktree = loop.adapter.get_session_workspace.return_value
    loop.adapter.get_worker_conversation.return_value = {
        "activities": [{
            "id": "approval-outside",
            "activityKind": "approval",
            "status": "pending",
            "detail": {"input": {"file_path": worktree + "/outside.py"}},
        }]}
    loop._completion_audit = MagicMock()

    loop.step(injected_events=[_completed_event(task)])

    assert loop.state == ProjectState.WORKER_RUNNING
    loop.gate.run.assert_not_called()
    loop._completion_audit.assert_not_called()


def test_fresh_error_awaiting_l0_keeps_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop._completion_audit = MagicMock()
    loop.executor.nudge_worker = MagicMock()
    error = ev(
        "2026-09-02T00:00:00Z",
        project=task.project_id,
        worker=task.worker_session_id,
        etype="error",
        message="fresh failure",
        fingerprint="fresh-failure",
    )

    loop.step(injected_events=[error])

    # First sighting stamps the hatch-grace clock; the L0 nudge is still
    # pending, so this tick must not be reclassified as a clean Gate-first.
    loop.executor.nudge_worker.assert_not_called()
    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()


def test_actionable_repeated_error_blocks_gate_first_completion(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop._handle_alerts = MagicMock()
    errors = [
        ev(
            "2026-09-02T00:0%d:00Z" % i,
            project=task.project_id,
            worker=task.worker_session_id,
            etype="error",
            message="same failure",
            fingerprint="same-failure",
        )
        for i in range(3)
    ]

    loop.step(injected_events=errors)

    loop._handle_alerts.assert_called_once()
    loop.gate.run.assert_not_called()


def test_actionable_no_progress_blocks_gate_first_completion(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    loop._handle_alerts = MagicMock()
    activity = [
        ev(
            "2026-09-02T00:%02d:00Z" % i,
            project=task.project_id,
            worker=task.worker_session_id,
            etype="command_executed",
            message="command %d" % i,
        )
        for i in range(8)
    ]

    loop.step(injected_events=activity)

    loop._handle_alerts.assert_called_once()
    loop.gate.run.assert_not_called()


def test_worker_retrying_idle_keeps_completion_audit(tmp_path):
    loop, task, _store, _verifier = _running_loop(tmp_path)
    _to_retrying(loop)
    loop._completion_audit = MagicMock()

    loop.step(injected_events=[_completed_event(task)])

    loop._completion_audit.assert_called_once()
    loop.gate.run.assert_not_called()

from codex_autoloop.codex_runner import InactivitySnapshot
from codex_autoloop.stall_subagent import analyze_stall


def test_stall_subagent_restart_on_stream_disconnect() -> None:
    snapshot = InactivitySnapshot(
        idle_seconds=1210,
        command=["codex", "exec"],
        thread_id="thread1",
        last_agent_message="",
        stdout_tail=[
            "stream disconnected before completion: An error occurred while processing your request."
        ],
        stderr_tail=[],
        run_label="main",
    )
    decision = analyze_stall(snapshot)
    assert decision.should_restart is True
    assert decision.matched_pattern == "stream disconnected before completion"


def test_stall_subagent_continue_without_error_signature() -> None:
    snapshot = InactivitySnapshot(
        idle_seconds=1500,
        command=["codex", "exec"],
        thread_id="thread1",
        last_agent_message="Working on complex migration",
        stdout_tail=["step 40/500 complete", "running heavy refactor"],
        stderr_tail=[],
        run_label="main",
    )
    decision = analyze_stall(snapshot)
    assert decision.should_restart is False
    assert "No explicit error signature found" in decision.reason

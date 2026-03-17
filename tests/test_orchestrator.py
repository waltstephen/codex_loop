from codex_autoloop.models import CodexRunResult
from codex_autoloop.models import ReviewDecision
from codex_autoloop.orchestrator import AutoLoopConfig, AutoLoopOrchestrator


class _InterruptingRunner:
    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        return CodexRunResult(
            command=["codex", "exec"],
            exit_code=0,
            thread_id="thread-1",
            agent_messages=["still working"],
            turn_completed=False,
            turn_failed=True,
            fatal_error="External interrupt: terminal requested instruction update",
        )


class _UnusedReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("reviewer should not run for external interrupts")


def test_external_interrupt_is_not_persisted_as_failure() -> None:
    events: list[dict] = []
    stop_checks = {"calls": 0}

    def should_stop() -> bool:
        stop_checks["calls"] += 1
        return stop_checks["calls"] >= 2

    orchestrator = AutoLoopOrchestrator(
        runner=_InterruptingRunner(),  # type: ignore[arg-type]
        reviewer=_UnusedReviewer(),  # type: ignore[arg-type]
        config=AutoLoopConfig(
            objective="continue work",
            max_rounds=3,
            stop_requested_checker=should_stop,
            pending_instruction_consumer=lambda: "new instruction",
            loop_event_callback=events.append,
        ),
    )

    result = orchestrator.run()

    assert result.success is False
    assert len(result.rounds) == 1
    round_summary = result.rounds[0]
    assert round_summary.main_turn_failed is False
    assert round_summary.review.reason.endswith("New operator instruction injected and will be applied.")
    assert round_summary.review.next_action == "Apply injected operator instruction in next round."

    main_event = next(event for event in events if event.get("type") == "round.main.completed")
    assert main_event["turn_failed"] is False
    assert main_event["interrupted"] is True


def test_initial_prompt_uses_response_mode_for_greeting() -> None:
    prompt = AutoLoopOrchestrator._initial_main_prompt("你好")
    assert "Reply directly in the user's language." in prompt
    assert "primary implementation agent" not in prompt


def test_initial_prompt_uses_response_mode_for_bug_question() -> None:
    prompt = AutoLoopOrchestrator._initial_main_prompt("这是为啥？你分析一下bug问题所在")
    assert "Reply directly in the user's language." in prompt
    assert "Do not force code changes unless they are actually needed" in prompt


def test_initial_prompt_keeps_implementation_mode_for_fix_request() -> None:
    prompt = AutoLoopOrchestrator._initial_main_prompt("修复 failing tests 并提交 commit")
    assert "primary implementation agent" in prompt
    assert "Complete the objective end-to-end" in prompt


class _SequenceRunner:
    def __init__(self, outputs: list[CodexRunResult]) -> None:
        self.outputs = outputs
        self.calls: list[str | None] = []

    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs.get("resume_thread_id"))
        if not self.outputs:
            raise AssertionError("runner called more times than expected")
        return self.outputs.pop(0)


class _DoneReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        return ReviewDecision(
            status="done",
            confidence=1.0,
            reason="completed",
            next_action="none",
        )


class _ContinueReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        return ReviewDecision(
            status="continue",
            confidence=0.9,
            reason="retry",
            next_action="retry",
        )


def test_invalid_encrypted_content_resets_session_and_retries_fresh() -> None:
    events: list[dict] = []
    runner = _SequenceRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=1,
                thread_id="thread-old",
                agent_messages=[],
                turn_completed=False,
                turn_failed=True,
                fatal_error="invalid_encrypted_content",
            ),
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=0,
                thread_id="thread-new",
                agent_messages=["done"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
        ]
    )
    orchestrator = AutoLoopOrchestrator(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_DoneReviewer(),  # type: ignore[arg-type]
        config=AutoLoopConfig(
            objective="继续修复并提交",
            initial_session_id="thread-old",
            max_rounds=5,
            loop_event_callback=events.append,
        ),
    )

    result = orchestrator.run()
    assert result.success is True
    assert result.session_id == "thread-new"
    assert runner.calls == ["thread-old", None]
    reset_events = [item for item in events if item.get("type") == "round.session.reset"]
    assert len(reset_events) == 1
    assert reset_events[0].get("previous_session_id") == "thread-old"


def test_quota_exhaustion_stops_immediately_without_reviewer_retry() -> None:
    runner = _SequenceRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=1,
                thread_id=None,
                agent_messages=[],
                turn_completed=False,
                turn_failed=True,
                fatal_error="You exceeded your current quota, please check your plan and billing details.",
            )
        ]
    )
    orchestrator = AutoLoopOrchestrator(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_UnusedReviewer(),  # type: ignore[arg-type]
        config=AutoLoopConfig(
            objective="继续修复",
            max_rounds=5,
        ),
    )

    result = orchestrator.run()

    assert result.success is False
    assert len(result.rounds) == 1
    assert "quota" in result.stop_reason.lower()
    round_summary = result.rounds[0]
    assert round_summary.review.status == "blocked"
    assert "quota" in round_summary.review.reason.lower()


def test_no_progress_stops_when_repeated_empty_failures() -> None:
    runner = _SequenceRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=1,
                thread_id=None,
                agent_messages=[],
                turn_completed=False,
                turn_failed=True,
                fatal_error="Process exited with code 1 before turn completion.",
            ),
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=1,
                thread_id=None,
                agent_messages=[],
                turn_completed=False,
                turn_failed=True,
                fatal_error="Process exited with code 1 before turn completion.",
            ),
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=1,
                thread_id=None,
                agent_messages=[],
                turn_completed=False,
                turn_failed=True,
                fatal_error="Process exited with code 1 before turn completion.",
            ),
        ]
    )
    orchestrator = AutoLoopOrchestrator(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_ContinueReviewer(),  # type: ignore[arg-type]
        config=AutoLoopConfig(
            objective="继续",
            max_rounds=10,
            max_no_progress_rounds=2,
        ),
    )
    result = orchestrator.run()
    assert result.success is False
    assert "no-progress" in result.stop_reason.lower()

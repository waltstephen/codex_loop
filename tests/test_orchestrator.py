from codex_autoloop.models import CodexRunResult
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

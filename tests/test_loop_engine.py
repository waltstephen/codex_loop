from codex_autoloop.core.engine import LoopConfig, LoopEngine
from codex_autoloop.models import CodexRunResult, ReviewDecision


class _SequenceRunner:
    def __init__(self, outputs: list[CodexRunResult]) -> None:
        self.outputs = outputs

    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        if not self.outputs:
            raise AssertionError("runner called more times than expected")
        return self.outputs.pop(0)


class _UnusedReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("reviewer should not run for unrecoverable quota errors")


class _ContinueReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        return ReviewDecision(
            status="continue",
            confidence=0.9,
            reason="retry",
            next_action="retry",
        )


def test_loop_engine_stops_immediately_on_quota_exhaustion() -> None:
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
    engine = LoopEngine(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_UnusedReviewer(),  # type: ignore[arg-type]
        planner=None,
        config=LoopConfig(
            objective="继续修复",
            max_rounds=5,
        ),
    )

    result = engine.run()

    assert result.success is False
    assert len(result.rounds) == 1
    assert "quota" in result.stop_reason.lower()
    round_summary = result.rounds[0]
    assert round_summary.review.status == "blocked"
    assert "quota" in round_summary.review.reason.lower()


def test_loop_engine_stops_when_repeated_empty_failures_make_no_progress() -> None:
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
    engine = LoopEngine(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_ContinueReviewer(),  # type: ignore[arg-type]
        planner=None,
        config=LoopConfig(
            objective="继续",
            max_rounds=10,
            max_no_progress_rounds=2,
        ),
    )

    result = engine.run()

    assert result.success is False
    assert "no-progress" in result.stop_reason.lower()

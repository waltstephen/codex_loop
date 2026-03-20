from pathlib import Path

from codex_autoloop.core.engine import LoopConfig, LoopEngine
from codex_autoloop.core.state_store import LoopStateStore
from codex_autoloop.models import CodexRunResult, ReviewDecision


class _SequenceRunner:
    def __init__(self, outputs: list[CodexRunResult]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, object]] = []

    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
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


class _DoneReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        return ReviewDecision(
            status="done",
            confidence=1.0,
            reason="complete",
            next_action="stop",
            round_summary_markdown="## Round Summary\n- done\n",
            completion_summary_markdown="## Completion\n- all checks passed\n",
        )


class _ReportWritingRunner(_SequenceRunner):
    def __init__(self, outputs: list[CodexRunResult], report_path: Path) -> None:
        super().__init__(outputs)
        self.report_path = report_path

    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        result = super().run_exec(**kwargs)
        if kwargs.get("run_label") == "main-final-report":
            self.report_path.write_text("# Final Task Report\n\nwritten by main agent\n", encoding="utf-8")
        return result


def test_loop_engine_generates_final_report_via_main_agent(tmp_path: Path) -> None:
    report_path = tmp_path / "final-task-report.md"
    runner = _ReportWritingRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=["DONE:\n- implemented\nREMAINING:\n- none\nBLOCKERS:\n- none"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
            CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=[f"REPORT_PATH: {report_path}\nREPORT_STATUS: written"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
        ],
        report_path=report_path,
    )
    state_store = LoopStateStore(
        objective="完成实验",
        final_report_file=str(report_path),
        plan_mode="off",
    )
    engine = LoopEngine(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_DoneReviewer(),  # type: ignore[arg-type]
        planner=None,
        state_store=state_store,
        config=LoopConfig(
            objective="完成实验",
            max_rounds=3,
        ),
    )

    result = engine.run()

    assert result.success is True
    assert report_path.exists()
    assert state_store.has_final_report() is True
    assert any(call.get("run_label") == "main-final-report" for call in runner.calls)


def test_loop_engine_falls_back_when_main_agent_does_not_write_final_report(tmp_path: Path) -> None:
    report_path = tmp_path / "final-task-report.md"
    runner = _SequenceRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=["DONE:\n- implemented\nREMAINING:\n- none\nBLOCKERS:\n- none"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
            CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=1,
                thread_id="thread-1",
                agent_messages=["could not write report"],
                turn_completed=False,
                turn_failed=True,
                fatal_error="write failed",
            ),
        ]
    )
    state_store = LoopStateStore(
        objective="完成实验",
        final_report_file=str(report_path),
        plan_mode="off",
    )
    engine = LoopEngine(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_DoneReviewer(),  # type: ignore[arg-type]
        planner=None,
        state_store=state_store,
        config=LoopConfig(
            objective="完成实验",
            max_rounds=3,
        ),
    )

    result = engine.run()

    assert result.success is True
    assert report_path.exists()
    assert "fallback" in report_path.read_text(encoding="utf-8").lower()
    assert state_store.has_final_report() is True


def test_loop_engine_rewrites_stale_existing_final_report(tmp_path: Path) -> None:
    report_path = tmp_path / "final-task-report.md"
    report_path.write_text("stale report\n", encoding="utf-8")
    runner = _SequenceRunner(
        outputs=[
            CodexRunResult(
                command=["codex", "exec"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=["DONE:\n- implemented\nREMAINING:\n- none\nBLOCKERS:\n- none"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
            CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=["REPORT_PATH written"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            ),
        ]
    )
    state_store = LoopStateStore(
        objective="完成实验",
        final_report_file=str(report_path),
        plan_mode="off",
    )
    engine = LoopEngine(
        runner=runner,  # type: ignore[arg-type]
        reviewer=_DoneReviewer(),  # type: ignore[arg-type]
        planner=None,
        state_store=state_store,
        config=LoopConfig(
            objective="完成实验",
            max_rounds=3,
        ),
    )

    result = engine.run()

    assert result.success is True
    content = report_path.read_text(encoding="utf-8")
    assert "stale report" not in content
    assert "fallback" in content.lower()

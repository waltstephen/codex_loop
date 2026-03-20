from pathlib import Path

from codex_autoloop.final_report import (
    FinalReportRequest,
    build_final_report_prompt,
    infer_report_language_mode,
    write_fallback_final_report,
)
from codex_autoloop.models import ReviewDecision, RoundSummary


def _request(
    *,
    objective: str,
    operator_messages: list[str],
    main_last_message: str = "Implemented the requested report flow.",
) -> FinalReportRequest:
    review = ReviewDecision(
        status="done",
        confidence=1.0,
        reason="complete",
        next_action="report to user",
        round_summary_markdown="## Round\n- complete\n",
        completion_summary_markdown="## Completion\n- done\n",
    )
    round_summary = RoundSummary(
        round_index=3,
        thread_id="thread-1",
        main_exit_code=0,
        main_turn_completed=True,
        main_turn_failed=False,
        checks=[],
        review=review,
        main_last_message=main_last_message,
    )
    return FinalReportRequest(
        objective=objective,
        report_path="/tmp/final-task-report.md",
        session_id="thread-1",
        operator_messages=operator_messages,
        round_summary=round_summary,
    )


def test_build_final_report_prompt_uses_user_requirements_only() -> None:
    request = _request(
        objective="Please add a final report and show the report path to the user.",
        operator_messages=["Also mention the release maintenance rule."],
    )

    prompt = build_final_report_prompt(request)

    assert "Original user task:" in prompt
    assert "User follow-up requirements:" in prompt
    assert "Also mention the release maintenance rule." in prompt
    assert "Visible skill/workflow context" not in prompt


def test_infer_report_language_mode_prefers_english_for_english_task() -> None:
    request = _request(
        objective="Add a final English delivery report for the completed task.",
        operator_messages=["Include the user's original request."],
    )
    assert infer_report_language_mode(request) == "en"


def test_write_fallback_final_report_includes_original_task_and_special_notes(tmp_path: Path) -> None:
    report = tmp_path / "final-task-report.md"
    request = _request(
        objective="把用户原始任务也附加到汇报里。",
        operator_messages=["额外要求：说明后续维护规则。"],
        main_last_message="已实现最终汇报生成流程。",
    )
    request = FinalReportRequest(
        objective=request.objective,
        report_path=str(report),
        session_id=request.session_id,
        operator_messages=request.operator_messages,
        round_summary=request.round_summary,
    )

    write_fallback_final_report(request=request, failure_reason="main report write failed")

    content = report.read_text(encoding="utf-8")
    assert "## 0. 原始用户任务" in content
    assert "把用户原始任务也附加到汇报里。" in content
    assert "## 4. 特殊说明" in content
    assert "skill/workflow" not in content

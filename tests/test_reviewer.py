from codex_autoloop.models import CheckResult
from codex_autoloop.reviewer import Reviewer, _coerce_decision_against_main_summary, parse_decision_text


def test_parse_decision_plain_json() -> None:
    decision = parse_decision_text(
        '{"status":"continue","confidence":0.7,"reason":"tests failing","next_action":"fix tests","round_summary_markdown":"# Round\\n","completion_summary_markdown":""}'
    )
    assert decision is not None
    assert decision.status == "continue"
    assert decision.confidence == 0.7
    assert decision.round_summary_markdown == "# Round"


def test_parse_decision_embedded_json() -> None:
    decision = parse_decision_text(
        "Here is my decision:\n"
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    assert decision.status == "done"


def test_parse_decision_invalid() -> None:
    decision = parse_decision_text("not json")
    assert decision is None


def test_parse_decision_rejects_missing_required_fields() -> None:
    decision = parse_decision_text(
        '{"status":"done","reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is None


def test_parse_decision_rejects_out_of_range_confidence() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1.2,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is None


def test_parse_decision_derives_reason_from_completion_summary() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":0.97,"next_action":"No further action needed. Objective complete.","round_summary_markdown":"## Round 1 Summary\\n\\n- Completed the analysis.\\n","completion_summary_markdown":"## Project Understanding Complete\\n\\nThe project objective is fully satisfied.\\n"}'
    )
    assert decision is not None
    assert decision.status == "done"
    assert decision.reason == "The project objective is fully satisfied."


def test_parse_decision_derives_next_action_for_continue() -> None:
    decision = parse_decision_text(
        '{"status":"continue","confidence":0.5,"reason":"Need to finish the test fixes.","round_summary_markdown":"# Review Summary\\n\\n- Need to finish the test fixes.\\n","completion_summary_markdown":""}'
    )
    assert decision is not None
    assert decision.next_action == "Continue implementation and include clear completion evidence."


def test_coerce_decision_downgrades_generic_main_summary() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    coerced = _coerce_decision_against_main_summary(
        decision,
        main_summary="I’m the primary implementation agent for this workspace. I’ll handle the main task directly.",
    )
    assert coerced.status == "continue"
    assert "generic role acknowledgment" in coerced.reason


def test_coerce_decision_downgrades_act_as_primary_ack() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    coerced = _coerce_decision_against_main_summary(
        decision,
        main_summary="Understood. I’ll act as the primary implementation agent and handle the main task directly.",
    )
    assert coerced.status == "continue"
    assert "generic role acknowledgment" in coerced.reason


def test_coerce_decision_keeps_done_when_summary_has_execution_evidence() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    kept = _coerce_decision_against_main_summary(
        decision,
        main_summary=(
            "I’ll act as the primary implementation agent. "
            "I ran pytest and updated tests/test_planner.py after inspecting codex_autoloop/core/engine.py."
        ),
    )
    assert kept.status == "done"
    assert kept.reason == "all checks pass"


def test_coerce_decision_downgrades_future_intent_without_execution_evidence() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    coerced = _coerce_decision_against_main_summary(
        decision,
        main_summary=(
            "I’ll act as the primary implementation agent. "
            "Next I will run pytest and update tests/test_planner.py after I inspect codex_autoloop/core/engine.py."
        ),
    )
    assert coerced.status == "continue"
    assert "generic role acknowledgment" in coerced.reason


def test_coerce_decision_downgrades_when_thread_id_contains_read_substring() -> None:
    decision = parse_decision_text(
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop","round_summary_markdown":"# Round\\n","completion_summary_markdown":"# Final\\n"}'
    )
    assert decision is not None
    coerced = _coerce_decision_against_main_summary(
        decision,
        main_summary=(
            "I’ll act as the primary implementation agent. "
            "Session is thread-1 and I already know the repo context."
        ),
    )
    assert coerced.status == "continue"
    assert "generic role acknowledgment" in coerced.reason


def test_reviewer_prompt_requires_raw_json_response() -> None:
    reviewer = Reviewer(runner=None)  # type: ignore[arg-type]
    prompt = reviewer._build_prompt(
        objective="ship feature",
        operator_messages=["keep it concise"],
        planner_review_instruction="focus on acceptance evidence",
        round_index=1,
        session_id="thread-1",
        main_summary="Implemented the feature.",
        main_error=None,
        checks=[CheckResult(command="pytest -q", exit_code=0, passed=True, output_tail="ok")],
    )
    assert "Return valid JSON matching the provided schema." in prompt
    assert "Do not wrap the response in markdown fences." in prompt

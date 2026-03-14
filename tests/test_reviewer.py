from codex_autoloop.reviewer import _coerce_decision_against_main_summary, parse_decision_text


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

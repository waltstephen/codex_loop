from codex_autoloop.reviewer import parse_decision_text


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

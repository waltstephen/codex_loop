from codex_autoloop.reviewer import parse_decision_text


def test_parse_decision_plain_json() -> None:
    decision = parse_decision_text(
        '{"status":"continue","confidence":0.7,"reason":"tests failing","next_action":"fix tests"}'
    )
    assert decision is not None
    assert decision.status == "continue"
    assert decision.confidence == 0.7


def test_parse_decision_embedded_json() -> None:
    decision = parse_decision_text(
        "Here is my decision:\n"
        '{"status":"done","confidence":1,"reason":"all checks pass","next_action":"stop"}'
    )
    assert decision is not None
    assert decision.status == "done"


def test_parse_decision_invalid() -> None:
    decision = parse_decision_text("not json")
    assert decision is None

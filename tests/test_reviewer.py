from codex_autoloop.codex_runner import CodexRunner
from codex_autoloop.reviewer import Reviewer, parse_decision_text


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


def test_build_prompt_includes_structured_main_run_facts() -> None:
    reviewer = Reviewer(CodexRunner(codex_bin="codex"))
    prompt = reviewer._build_prompt(
        objective="say hello",
        operator_messages=["用户只说了你好"],
        round_index=1,
        session_id="thread-1",
        main_exit_code=0,
        main_turn_completed=False,
        main_turn_failed=False,
        main_agent_message_count=1,
        main_summary="你好！有什么我可以帮你的吗？",
        main_error=None,
        checks=[],
    )

    assert "Do not speculate about crashes or missing replies" in prompt
    assert "Main agent exit code: 0" in prompt
    assert "Main agent turn completed: false" in prompt
    assert "Main agent turn failed: false" in prompt
    assert "Main agent emitted agent messages: 1" in prompt

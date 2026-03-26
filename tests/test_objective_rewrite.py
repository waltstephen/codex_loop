from __future__ import annotations

from codex_autoloop.objective_rewrite import (
    ObjectiveRewriteResult,
    format_objective_rewrite_message,
    parse_objective_rewrite_text,
    rewrite_run_objective,
)


class _FakeResult:
    def __init__(self, payload: str) -> None:
        self.last_agent_message = payload
        self.fatal_error = None
        self.exit_code = 0


class _FakeRunner:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def run_exec(self, **kwargs):
        return _FakeResult(self.payload)


def test_parse_objective_rewrite_text_reads_json_object() -> None:
    text = '{"rewritten_objective":"Final Goal:\\nShip docs"}'
    assert parse_objective_rewrite_text(text) == "Final Goal:\nShip docs"


def test_rewrite_run_objective_returns_runner_output() -> None:
    runner = _FakeRunner('{"rewritten_objective":"Final Goal:\\nShip docs\\n\\nCurrent Task:\\nUpdate README"}')
    result = rewrite_run_objective(
        runner=runner,
        objective="更新文档",
        working_dir=".",
        project_name="ArgusBot",
        model=None,
        reasoning_effort=None,
    )
    assert result.failure_reason is None
    assert result.applied is True
    assert "Final Goal:" in result.rewritten_objective


def test_rewrite_run_objective_falls_back_when_output_is_invalid() -> None:
    runner = _FakeRunner("not json")
    result = rewrite_run_objective(
        runner=runner,
        objective="更新文档",
        working_dir=".",
        project_name="ArgusBot",
        model=None,
        reasoning_effort=None,
    )
    assert result.rewritten_objective == "更新文档"
    assert result.failure_reason is not None


def test_format_objective_rewrite_message_is_bilingual() -> None:
    message = format_objective_rewrite_message(
        ObjectiveRewriteResult(
            original_objective="更新文档",
            rewritten_objective="Final Goal:\n更新文档",
            applied=True,
        )
    )
    assert "Original / 原始" in message
    assert "发送给 Main Agent" in message

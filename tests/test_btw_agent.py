import time
from pathlib import Path

from codex_autoloop.btw_agent import BtwAgent, BtwConfig
from codex_autoloop.models import CodexRunResult


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, str | None]] = []

    def run_exec(self, *, prompt: str, resume_thread_id: str | None, options, run_label: str | None = None):
        self.calls.append((prompt, resume_thread_id, options.working_dir))
        turn_index = len(self.calls)
        return CodexRunResult(
            command=["codex", "exec"],
            exit_code=0,
            thread_id=f"btw-thread-{turn_index}",
            agent_messages=[f"btw-answer-{turn_index}"],
            turn_completed=True,
            turn_failed=False,
        )


def test_btw_agent_keeps_its_own_session_and_log(tmp_path: Path) -> None:
    runner = _FakeRunner()
    agent = BtwAgent(
        runner=runner,
        config=BtwConfig(
            working_dir=str(tmp_path),
            messages_file=str(tmp_path / "btw_messages.md"),
        ),
    )
    answers: list[str] = []
    assert agent.start_async(question="first question", on_complete=lambda result: answers.append(result.answer)) is True
    while agent.status_snapshot().busy or len(answers) < 1:
        time.sleep(0.01)
    assert answers == ["btw-answer-1"]
    assert agent.start_async(question="second question", on_complete=lambda result: answers.append(result.answer)) is True
    while agent.status_snapshot().busy or len(answers) < 2:
        time.sleep(0.01)
    assert answers == ["btw-answer-1", "btw-answer-2"]
    assert runner.calls[0][1] is None
    assert runner.calls[1][1] == "btw-thread-1"
    content = (tmp_path / "btw_messages.md").read_text(encoding="utf-8")
    assert "first question" in content
    assert "btw-answer-2" in content


def test_btw_agent_file_request_returns_attachments_without_runner(tmp_path: Path) -> None:
    runner = _FakeRunner()
    images = tmp_path / "images"
    images.mkdir()
    target = images / "effect_result.png"
    target.write_bytes(b"png")
    agent = BtwAgent(
        runner=runner,
        config=BtwConfig(
            working_dir=str(tmp_path),
            messages_file=str(tmp_path / "btw_messages.md"),
        ),
    )
    results = []
    assert agent.start_async(question="我要看看效果图", on_complete=lambda result: results.append(result)) is True
    while agent.status_snapshot().busy or len(results) < 1:
        time.sleep(0.01)
    assert runner.calls == []
    assert results[0].attachments
    assert results[0].attachments[0].path.endswith("effect_result.png")

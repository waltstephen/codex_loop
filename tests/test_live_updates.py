import json

from codex_autoloop.live_updates import (
    TelegramStreamReporter,
    TelegramStreamReporterConfig,
    extract_agent_message,
)


class _FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, message: str) -> None:
        self.messages.append(message)


def test_extract_agent_message() -> None:
    line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "hello world"},
        }
    )
    parsed = extract_agent_message("main.stdout", line)
    assert parsed == ("main", "hello world")


def test_extract_agent_message_ignores_non_message() -> None:
    line = json.dumps({"type": "item.completed", "item": {"type": "reasoning", "text": "x"}})
    assert extract_agent_message("main.stdout", line) is None


def test_reporter_flush_only_when_changed() -> None:
    notifier = _FakeNotifier()
    reporter = TelegramStreamReporter(
        notifier=notifier, config=TelegramStreamReporterConfig(interval_seconds=30)
    )
    reporter.add_message("main", "first")
    reporter.add_message("main", "first")
    reporter.add_message("reviewer", "ok")
    sent = reporter.flush()
    assert sent is True
    assert len(notifier.messages) == 1
    assert "main: first" in notifier.messages[0]
    assert "reviewer: ok" in notifier.messages[0]
    assert reporter.flush() is False

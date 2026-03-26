import json

from codex_autoloop.live_updates import (
    TelegramStreamReporter,
    TelegramStreamReporterConfig,
    extract_agent_message,
    extract_stream_report_message,
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


def test_extract_stream_report_message_accumulates_copilot_deltas() -> None:
    first = extract_stream_report_message(
        "main.stdout",
        json.dumps(
            {
                "type": "assistant.message_delta",
                "data": {"messageId": "msg-1", "deltaContent": "Hello"},
            }
        ),
    )
    second = extract_stream_report_message(
        "main.stdout",
        json.dumps(
            {
                "type": "assistant.message_delta",
                "data": {"messageId": "msg-1", "deltaContent": " world"},
            }
        ),
    )
    assert first is not None
    assert first.actor == "main"
    assert first.message == "Hello"
    assert first.replace_pending is True
    assert second is not None
    assert second.message == "Hello world"
    assert second.replace_pending is True


def test_extract_stream_report_message_prefers_copilot_final_message() -> None:
    extracted = extract_stream_report_message(
        "main.stdout",
        json.dumps(
            {
                "type": "assistant.message",
                "data": {"messageId": "msg-2", "content": "Final answer"},
            }
        ),
    )
    assert extracted is not None
    assert extracted.actor == "main"
    assert extracted.message == "Final answer"
    assert extracted.replace_pending is True


def test_reporter_flush_only_when_changed() -> None:
    notifier = _FakeNotifier()
    reporter = TelegramStreamReporter(
        notifier=notifier, config=TelegramStreamReporterConfig(interval_seconds=30)
    )
    reporter.add_message("main", "first")
    reporter.add_message("main", "first")  # Duplicate, should be skipped
    reporter.add_message("reviewer", "ok")
    sent = reporter.flush()
    assert sent is True
    # Each actor gets a separate message now
    assert len(notifier.messages) == 2
    # Check main message
    assert "**main:**" in notifier.messages[0]
    assert "first" in notifier.messages[0]
    # Check reviewer message
    assert "**reviewer:**" in notifier.messages[1]
    assert "ok" in notifier.messages[1]
    # Verify newlines are preserved for Markdown rendering
    assert "\n\n" in notifier.messages[0]
    assert "\n\n" in notifier.messages[1]
    # Duplicate messages should not be sent again
    assert reporter.flush() is False


def test_reporter_replace_message_keeps_only_latest_pending_message_per_actor() -> None:
    notifier = _FakeNotifier()
    reporter = TelegramStreamReporter(
        notifier=notifier, config=TelegramStreamReporterConfig(interval_seconds=30)
    )
    reporter.replace_message("main", "step 1")
    reporter.replace_message("main", "step 2")
    reporter.add_message("reviewer", "ok")
    sent = reporter.flush()
    assert sent is True
    assert len(notifier.messages) == 2
    assert "step 2" in notifier.messages[0]
    assert "step 1" not in notifier.messages[0]
    assert "ok" in notifier.messages[1]

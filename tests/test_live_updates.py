import json

from codex_autoloop.live_updates import (
    GenericStreamReporter,
    TelegramStreamReporter,
    TelegramStreamReporterConfig,
    extract_agent_message,
    parse_child_actor_line,
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


def test_generic_reporter_flush_only_when_changed() -> None:
    notifier = _FakeNotifier()
    reporter = GenericStreamReporter(
        notifier=notifier,
        config=TelegramStreamReporterConfig(interval_seconds=30),
        error_label="generic",
    )
    reporter.add_message("main", "first")
    reporter.add_message("main", "first")
    reporter.add_message("reviewer", "ok")
    assert reporter.flush() is True
    assert len(notifier.messages) == 1
    assert "main: first" in notifier.messages[0]
    assert "reviewer: ok" in notifier.messages[0]


def test_parse_child_actor_line() -> None:
    assert parse_child_actor_line("[main agent]") == "main"
    assert parse_child_actor_line("[reviewer agent]") == "reviewer"
    assert parse_child_actor_line("plain text") is None


def test_generic_reporter_can_preserve_full_multiline_text() -> None:
    notifier = _FakeNotifier()
    reporter = GenericStreamReporter(
        notifier=notifier,
        config=TelegramStreamReporterConfig(
            interval_seconds=30,
            max_chars=None,
            max_item_chars=None,
            compact_items=False,
        ),
        error_label="generic",
    )
    reporter.add_message("main", "line1\nline2")
    assert reporter.flush() is True
    assert "[main agent]" in notifier.messages[0]
    assert "line1\nline2" in notifier.messages[0]


def test_generic_reporter_can_filter_actors() -> None:
    notifier = _FakeNotifier()
    reporter = GenericStreamReporter(
        notifier=notifier,
        config=TelegramStreamReporterConfig(interval_seconds=30),
        allowed_actors={"main"},
    )
    reporter.add_message("reviewer", "should be dropped")
    reporter.add_message("main", "should stay")
    assert reporter.flush() is True
    assert "main: should stay" in notifier.messages[0]
    assert "reviewer" not in notifier.messages[0]


def test_generic_reporter_can_omit_live_update_header() -> None:
    notifier = _FakeNotifier()
    reporter = GenericStreamReporter(
        notifier=notifier,
        config=TelegramStreamReporterConfig(
            interval_seconds=30,
            max_chars=None,
            max_item_chars=None,
            compact_items=False,
            header_template=None,
        ),
    )
    reporter.add_message("main", "hello")
    assert reporter.flush() is True
    assert notifier.messages[0].startswith("[main agent]\nhello")
    assert "live update" not in notifier.messages[0]

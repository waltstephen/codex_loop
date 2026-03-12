import urllib.error

from codex_autoloop.cli import looks_like_bot_token
from codex_autoloop.telegram_notifier import (
    TelegramConfig,
    TelegramNotifier,
    extract_chat_id_from_update,
    format_event_message,
)


def test_format_started() -> None:
    message = format_event_message(
        {
            "type": "loop.started",
            "objective": "implement pipeline",
            "max_rounds": 10,
        }
    )
    assert "started" in message
    assert "implement pipeline" in message


def test_format_review() -> None:
    message = format_event_message(
        {
            "type": "round.review.completed",
            "round_index": 2,
            "status": "continue",
            "confidence": 0.7,
            "reason": "tests still failing",
            "next_action": "fix tests",
        }
    )
    assert "reviewer decision" in message
    assert "status=continue" in message


def test_unknown_event_empty() -> None:
    assert format_event_message({"type": "x.unknown"}) == ""


def test_format_plan_finalized() -> None:
    message = format_event_message(
        {
            "type": "plan.finalized",
            "trigger": "final",
            "terminal": True,
            "summary": "core implementation is complete",
            "suggested_next_objective": "benchmark the new pipeline end-to-end",
        }
    )
    assert "planner final" in message
    assert "benchmark the new pipeline" in message


def test_token_shape_validation() -> None:
    assert looks_like_bot_token("123456:ABCDEFGHIJK")
    assert not looks_like_bot_token("ABCDEFGHIJK")
    assert not looks_like_bot_token("abc:ABCDEFGHIJK")


def test_typing_disabled_does_not_start_thread() -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
            typing_enabled=False,
        )
    )
    notifier.notify_event({"type": "loop.started"})
    assert notifier._typing_thread is None


def test_extract_chat_id_from_message_update() -> None:
    update = {"message": {"chat": {"id": 12345}}}
    assert extract_chat_id_from_update(update) == "12345"


def test_send_message_timeout_does_not_raise(monkeypatch) -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
        )
    )
    errors: list[str] = []
    notifier.on_error = errors.append

    def fake_urlopen(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise TimeoutError("read timed out")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    notifier.send_message("hello")
    assert errors
    assert "timeout" in errors[-1].lower()


def test_send_message_urlerror_does_not_raise(monkeypatch) -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
        )
    )
    errors: list[str] = []
    notifier.on_error = errors.append

    def fake_urlopen(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError("network down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    notifier.send_message("hello")
    assert errors
    assert "network" in errors[-1].lower()

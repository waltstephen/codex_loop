from pathlib import Path

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


def test_format_plan() -> None:
    message = format_event_message(
        {
            "type": "plan.completed",
            "round_index": 2,
            "plan_mode": "auto",
            "next_explore": "inspect parser",
            "main_instruction": "fix parser",
        }
    )
    assert "plan updated" in message
    assert "inspect parser" in message


def test_unknown_event_empty() -> None:
    assert format_event_message({"type": "x.unknown"}) == ""


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


def test_send_local_file_uses_photo_for_images(tmp_path: Path) -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
        )
    )
    calls = []
    notifier._post_multipart_file = lambda **kwargs: calls.append(kwargs) or True  # type: ignore[attr-defined]
    image = tmp_path / "preview.png"
    image.write_bytes(b"png")
    assert notifier.send_local_file(image, caption="preview") is True
    assert calls[0]["field_name"] == "photo"


def test_send_local_file_uses_document_for_non_images(tmp_path: Path) -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
        )
    )
    calls = []
    notifier._post_multipart_file = lambda **kwargs: calls.append(kwargs) or True  # type: ignore[attr-defined]
    file_path = tmp_path / "report.md"
    file_path.write_text("hello", encoding="utf-8")
    assert notifier.send_local_file(file_path, caption="report") is True
    assert calls[0]["field_name"] == "document"


def test_send_message_returns_post_result() -> None:
    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token="123456:ABCDEFGHIJK",
            chat_id="1",
            events=set(),
        )
    )
    notifier._post_form = lambda url, payload: False  # type: ignore[attr-defined]
    assert notifier.send_message("hello") is False

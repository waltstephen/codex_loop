from codex_autoloop.telegram_control import (
    TelegramCommand,
    TelegramCommandPoller,
    TelegramWhisperTranscriber,
    extract_audio_file_from_message,
    parse_command_from_update,
)


def _wrap(text: str, chat_id: int = 100) -> dict:
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": chat_id},
            "text": text,
        },
    }


def _wrap_voice(file_id: str = "voice-file", chat_id: int = 100) -> dict:
    return {
        "update_id": 2,
        "message": {
            "chat": {"id": chat_id},
            "voice": {"file_id": file_id},
        },
    }


def _wrap_callback(data: str, chat_id: int = 100) -> dict:
    return {
        "update_id": 3,
        "callback_query": {
            "id": "cb-1",
            "data": data,
            "message": {
                "chat": {"id": chat_id},
            },
        },
    }


def test_parse_new_command() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/new"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "new"


def test_parse_inject_command() -> None:
    command = parse_command_from_update(
        update=_wrap("/inject fix the parser"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is not None
    assert command.kind == "inject"
    assert command.text == "fix the parser"


def test_parse_plain_text_as_inject() -> None:
    command = parse_command_from_update(
        update=_wrap("continue with the stalled round"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is not None
    assert command.kind == "inject"


def test_parse_stop_and_status() -> None:
    stop = parse_command_from_update(
        update=_wrap("/stop"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    status = parse_command_from_update(
        update=_wrap("/status"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert stop is not None and stop.kind == "stop"
    assert status is not None and status.kind == "status"


def test_parse_fresh_session_command() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/fresh"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "fresh-session"


def test_parse_mode_command() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/mode record"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "mode"
    assert cmd.text == "record"


def test_parse_mode_menu_command() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/mode"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "mode-menu"


def test_parse_btw_command() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/btw 这个项目的 planner 怎么接的"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "btw"


def test_parse_plan_and_review_commands() -> None:
    plan = parse_command_from_update(
        update=_wrap("/plan focus on state persistence"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    review = parse_command_from_update(
        update=_wrap("/review must pass pytest -q"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert plan is not None and plan.kind == "plan"
    assert review is not None and review.kind == "review"


def test_parse_show_commands() -> None:
    show_main = parse_command_from_update(
        update=_wrap("/show-main-prompt"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    show_plan = parse_command_from_update(
        update=_wrap("/show-plan"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    show_plan_context = parse_command_from_update(
        update=_wrap("/show-plan-context"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    show_review = parse_command_from_update(
        update=_wrap("/show-review 3"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    show_review_context = parse_command_from_update(
        update=_wrap("/show-review-context"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert show_main is not None and show_main.kind == "show-main-prompt"
    assert show_plan is not None and show_plan.kind == "show-plan"
    assert show_plan_context is not None and show_plan_context.kind == "show-plan-context"
    assert show_review is not None and show_review.kind == "show-review" and show_review.text == "3"
    assert show_review_context is not None and show_review_context.kind == "show-review-context"


def test_parse_help_with_cjk_punctuation_prefix() -> None:
    help_cmd = parse_command_from_update(
        update=_wrap("、help"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    status_cmd = parse_command_from_update(
        update=_wrap("／status"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert help_cmd is not None and help_cmd.kind == "help"
    assert status_cmd is not None and status_cmd.kind == "status"


def test_parse_daemon_stop() -> None:
    cmd = parse_command_from_update(
        update=_wrap("/daemon-stop"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert cmd is not None
    assert cmd.kind == "daemon-stop"


def test_parse_run_command() -> None:
    run = parse_command_from_update(
        update=_wrap("/run build training pipeline"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert run is not None
    assert run.kind == "run"
    assert run.text == "build training pipeline"


def test_parse_plan_callback_command() -> None:
    command = parse_command_from_update(
        update=_wrap_callback("plan_run:plan-123"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is not None
    assert command.kind == "plan-run"
    assert command.text == "plan-123"
    assert command.callback_query_id == "cb-1"


def test_parse_plan_modify_and_reject_callback_command() -> None:
    modify = parse_command_from_update(
        update=_wrap_callback("plan_modify:plan-123"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    reject = parse_command_from_update(
        update=_wrap_callback("plan_reject:plan-123"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert modify is not None and modify.kind == "plan-modify"
    assert reject is not None and reject.kind == "plan-reject"


def test_ignore_other_chat() -> None:
    command = parse_command_from_update(
        update=_wrap("/inject x", chat_id=999),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is None


def test_parse_caption_command() -> None:
    command = parse_command_from_update(
        update={
            "update_id": 9,
            "message": {
                "chat": {"id": 100},
                "caption": "/run review open prs",
            },
        },
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is not None
    assert command.kind == "run"
    assert command.text == "review open prs"


def test_extract_audio_file_from_message_voice() -> None:
    audio = extract_audio_file_from_message({"voice": {"file_id": "abc"}})
    assert audio is not None
    assert audio.file_id == "abc"
    assert audio.file_name == "voice.ogg"


def test_extract_audio_file_from_message_audio_and_document() -> None:
    from_audio = extract_audio_file_from_message(
        {"audio": {"file_id": "audio-id", "file_name": "memo.m4a"}}
    )
    from_document = extract_audio_file_from_message(
        {"document": {"file_id": "doc-id", "mime_type": "audio/ogg", "file_name": "clip.ogg"}}
    )
    assert from_audio is not None and from_audio.file_name == "memo.m4a"
    assert from_document is not None and from_document.file_id == "doc-id"


def test_whisper_transcriber_missing_key_reports_once() -> None:
    errors: list[str] = []
    transcriber = TelegramWhisperTranscriber(
        bot_token="123:abc",
        api_key="",
        on_error=errors.append,
    )
    first = transcriber.transcribe_update(update=_wrap_voice(), expected_chat_id="100")
    second = transcriber.transcribe_update(update=_wrap_voice(file_id="other"), expected_chat_id="100")
    assert first is None
    assert second is None
    assert len(errors) == 1
    assert "missing OPENAI_API_KEY" in errors[0]


def test_fetch_updates_timeout_is_reported(monkeypatch) -> None:
    errors: list[str] = []
    poller = TelegramCommandPoller(
        bot_token="123:abc",
        chat_id="100",
        on_command=lambda command: None,
        on_error=errors.append,
    )

    def fake_urlopen(req, timeout):  # type: ignore[no-untyped-def]
        raise TimeoutError("timed out")

    monkeypatch.setattr("codex_autoloop.telegram_control.urllib.request.urlopen", fake_urlopen)
    assert poller._fetch_updates() is None
    assert errors
    assert "network error" in errors[0]


def test_run_loop_survives_unexpected_fetch_error(monkeypatch) -> None:
    errors: list[str] = []
    commands: list[TelegramCommand] = []
    poller = TelegramCommandPoller(
        bot_token="123:abc",
        chat_id="100",
        on_command=commands.append,
        on_error=errors.append,
        poll_interval_seconds=1,
    )
    calls = {"count": 0}

    def fake_fetch_updates():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        poller._stop_event.set()
        return []

    monkeypatch.setattr(poller, "_fetch_updates", fake_fetch_updates)
    poller._run()
    assert calls["count"] == 2
    assert errors
    assert "unexpected error" in errors[0]
    assert commands == []

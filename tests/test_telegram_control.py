from codex_autoloop.telegram_control import parse_command_from_update


def _wrap(text: str, chat_id: int = 100) -> dict:
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": chat_id},
            "text": text,
        },
    }


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


def test_parse_run_command() -> None:
    run = parse_command_from_update(
        update=_wrap("/run build training pipeline"),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert run is not None
    assert run.kind == "run"
    assert run.text == "build training pipeline"


def test_ignore_other_chat() -> None:
    command = parse_command_from_update(
        update=_wrap("/inject x", chat_id=999),
        expected_chat_id="100",
        plain_text_as_inject=True,
    )
    assert command is None

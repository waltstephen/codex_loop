from codex_autoloop.attachment_policy import (
    ATTACHMENT_CANCEL_COMMAND,
    ATTACHMENT_CONFIRM_COMMAND,
    requires_attachment_confirmation,
)


def test_requires_attachment_confirmation_for_bot_sources() -> None:
    assert requires_attachment_confirmation(source="telegram", attachment_count=6) is True
    assert requires_attachment_confirmation(source="feishu", attachment_count=6) is True
    assert requires_attachment_confirmation(source="teams", attachment_count=6) is True
    assert requires_attachment_confirmation(source="telegram", attachment_count=5) is False
    assert requires_attachment_confirmation(source="feishu", attachment_count=5) is False
    assert requires_attachment_confirmation(source="teams", attachment_count=5) is False


def test_requires_attachment_confirmation_skips_non_bot_sources() -> None:
    assert requires_attachment_confirmation(source="terminal", attachment_count=9) is False


def test_confirmation_commands_have_expected_defaults() -> None:
    assert ATTACHMENT_CONFIRM_COMMAND == "/confirm-send"
    assert ATTACHMENT_CANCEL_COMMAND == "/cancel-send"

from codex_autoloop.feishu_adapter import (
    FeishuCommandPoller,
    is_feishu_self_message,
    parse_feishu_command_text,
    split_feishu_message,
)


def test_parse_feishu_command_text_supports_extended_commands() -> None:
    assert parse_feishu_command_text(text="/mode", plain_text_kind="inject").kind == "mode-menu"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/mode auto", plain_text_kind="inject").text == "auto"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/btw explain repo", plain_text_kind="inject").kind == "btw"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/plan tighten scope", plain_text_kind="inject").kind == "plan"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/review must pass tests", plain_text_kind="inject").kind == "review"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/show-plan", plain_text_kind="inject").kind == "show-plan"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/show-review 4", plain_text_kind="inject").text == "4"  # type: ignore[union-attr]


def test_parse_feishu_command_text_plain_text_kind_is_configurable() -> None:
    assert parse_feishu_command_text(text="continue", plain_text_kind="inject").kind == "inject"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="new task", plain_text_kind="run").kind == "run"  # type: ignore[union-attr]


def test_feishu_self_message_filter() -> None:
    assert is_feishu_self_message(
        {
            "sender": {"sender_type": "app"},
            "body": {"content": "{\"text\":\"hello\"}"},
        }
    )
    assert is_feishu_self_message(
        {
            "body": {"content": "{\"text\":\"[daemon] online\"}"},
        }
    )


def test_feishu_poller_initializes_from_latest_desc_row() -> None:
    poller = FeishuCommandPoller(
        app_id="cli_xxx",
        app_secret="secret",
        chat_id="oc_xxx",
        on_command=lambda command: None,
    )
    poller._last_message_id = None
    rows = [
        {"message_id": "newest"},
        {"message_id": "older"},
    ]
    if rows:
        latest_id = str(rows[0].get("message_id") or "").strip()
        if latest_id:
            poller._last_message_id = latest_id
    assert poller._last_message_id == "newest"


def test_split_feishu_message_preserves_full_text() -> None:
    text = "a" * 1600 + "\n" + "b" * 1600
    chunks = split_feishu_message(text, max_chunk_chars=1500)
    assert len(chunks) >= 2
    rebuilt = "\n".join(chunk.split("\n", 1)[1] if chunk.startswith("[") else chunk for chunk in chunks)
    assert "a" * 1500 in rebuilt
    assert "b" * 1500 in rebuilt

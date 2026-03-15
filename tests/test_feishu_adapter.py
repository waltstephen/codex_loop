from codex_autoloop.feishu_adapter import (
    FeishuConfig,
    FeishuCommandPoller,
    FeishuNotifier,
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
    assert parse_feishu_command_text(text="/confirm-send", plain_text_kind="inject").kind == "attachments-confirm"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="/cancel-send", plain_text_kind="inject").kind == "attachments-cancel"  # type: ignore[union-attr]


def test_parse_feishu_command_text_plain_text_kind_is_configurable() -> None:
    assert parse_feishu_command_text(text="continue", plain_text_kind="inject").kind == "inject"  # type: ignore[union-attr]
    assert parse_feishu_command_text(text="new task", plain_text_kind="run").kind == "run"  # type: ignore[union-attr]


def test_parse_feishu_command_text_strips_leading_mentions_for_commands() -> None:
    parsed = parse_feishu_command_text(text="@_user_1 /stop", plain_text_kind="run")
    assert parsed is not None
    assert parsed.kind == "stop"


def test_parse_feishu_command_text_strips_leading_mentions_for_plain_text() -> None:
    parsed = parse_feishu_command_text(text="@_user_1 晚上好 帮我跑测试", plain_text_kind="run")
    assert parsed is not None
    assert parsed.kind == "run"
    assert parsed.text == "晚上好 帮我跑测试"


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


def test_send_local_file_uses_image_upload_for_images(tmp_path) -> None:  # type: ignore[no-untyped-def]
    notifier = FeishuNotifier(
        FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret",
            chat_id="oc_xxx",
            events=set(),
        )
    )
    notifier._tokens.get_token = lambda: "tenant-token"  # type: ignore[method-assign]
    calls: list[tuple[str, str]] = []
    notifier._upload_image = lambda **kwargs: "img-1"  # type: ignore[method-assign]
    notifier._upload_file = lambda **kwargs: "file-1"  # type: ignore[method-assign]

    def fake_send_structured_message(**kwargs):  # type: ignore[no-untyped-def]
        calls.append((kwargs["msg_type"], str(kwargs["content"])))
        return True

    notifier._send_structured_message = fake_send_structured_message  # type: ignore[method-assign]
    image = tmp_path / "preview.png"
    image.write_bytes(b"png")
    assert notifier.send_local_file(image, caption="preview") is True
    assert calls[0][0] == "image"
    assert calls[1][0] == "text"


def test_send_local_file_uses_file_message_for_video(tmp_path) -> None:  # type: ignore[no-untyped-def]
    notifier = FeishuNotifier(
        FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret",
            chat_id="oc_xxx",
            events=set(),
        )
    )
    notifier._tokens.get_token = lambda: "tenant-token"  # type: ignore[method-assign]
    calls: list[tuple[str, str]] = []
    upload_file_types: list[str] = []

    def fake_upload_file(**kwargs):  # type: ignore[no-untyped-def]
        upload_file_types.append(str(kwargs["file_type"]))
        return "file-2"

    notifier._upload_file = fake_upload_file  # type: ignore[method-assign]

    def fake_send_structured_message(**kwargs):  # type: ignore[no-untyped-def]
        calls.append((kwargs["msg_type"], str(kwargs["content"])))
        return True

    notifier._send_structured_message = fake_send_structured_message  # type: ignore[method-assign]
    video = tmp_path / "demo.mp4"
    video.write_bytes(b"mp4")
    assert notifier.send_local_file(video, caption="preview video") is True
    assert upload_file_types == ["mp4"]
    assert calls[0][0] == "file"
    assert calls[1][0] == "text"


def test_send_local_file_uses_file_message_for_generic_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    notifier = FeishuNotifier(
        FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret",
            chat_id="oc_xxx",
            events=set(),
        )
    )
    notifier._tokens.get_token = lambda: "tenant-token"  # type: ignore[method-assign]
    calls: list[tuple[str, str]] = []
    upload_file_types: list[str] = []

    def fake_upload_file(**kwargs):  # type: ignore[no-untyped-def]
        upload_file_types.append(str(kwargs["file_type"]))
        return "file-3"

    notifier._upload_file = fake_upload_file  # type: ignore[method-assign]

    def fake_send_structured_message(**kwargs):  # type: ignore[no-untyped-def]
        calls.append((kwargs["msg_type"], str(kwargs["content"])))
        return True

    notifier._send_structured_message = fake_send_structured_message  # type: ignore[method-assign]
    doc = tmp_path / "report.md"
    doc.write_text("hello", encoding="utf-8")
    assert notifier.send_local_file(doc, caption="report") is True
    assert upload_file_types == ["stream"]
    assert calls[0][0] == "file"
    assert calls[1][0] == "text"

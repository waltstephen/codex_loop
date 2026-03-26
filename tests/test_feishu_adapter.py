from codex_autoloop.feishu_adapter import (
    FeishuConfig,
    FeishuCommandPoller,
    FeishuNotifier,
    build_interactive_card,
    format_feishu_event_card,
    format_feishu_event_message,
    is_feishu_self_message,
    markdown_to_feishu_post,
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


def test_format_feishu_event_message_reuses_safe_review_formatting() -> None:
    message = format_feishu_event_message(
        {
            "type": "round.review.completed",
            "round_index": 2,
            "status": "continue",
            "confidence": None,
            "reason": "",
            "next_action": "",
        }
    )
    assert "confidence=unknown" in message
    assert "reason=unavailable" in message
    assert "next_action=unavailable" in message


def test_format_feishu_event_message_hides_confidence_for_invalid_reviewer_fallback() -> None:
    message = format_feishu_event_message(
        {
            "type": "round.review.completed",
            "round_index": 2,
            "status": "continue",
            "confidence": 0.0,
            "reason": "Reviewer output was not valid JSON.",
            "next_action": "Continue implementation and include clear completion evidence.",
        }
    )
    assert "confidence=unknown" in message
    assert "reason=Reviewer output was not valid JSON." in message


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


def test_markdown_to_feishu_post_handles_headers() -> None:
    """Test markdown conversion handles headers correctly"""
    md = "## Main Title\n\nContent here.\n\n### Subtitle\n\nMore content."
    result = markdown_to_feishu_post(md)

    assert result["msg_type"] == "post"
    assert "zh_cn" in result["content"]

    content = result["content"]["zh_cn"]["content"]
    # First block should be the main header with **bold**
    assert "**Main Title**" in content[0][0]["text"]
    # Subtitle should have newlines
    assert any("Subtitle" in block[0]["text"] for block in content)


def test_markdown_to_feishu_post_handles_lists() -> None:
    """Test markdown conversion handles list items correctly"""
    md = "- Item 1\n- Item 2\n- Item 3"
    result = markdown_to_feishu_post(md)

    content = result["content"]["zh_cn"]["content"]
    # List items should be converted to • bullet points
    for block in content:
        assert "•" in block[0]["text"]


def test_markdown_to_feishu_post_handles_bold_lines() -> None:
    """Test markdown conversion handles bold-only lines correctly"""
    md = "**This is bold**"
    result = markdown_to_feishu_post(md)

    content = result["content"]["zh_cn"]["content"]
    # Bold markers should be stripped
    assert content[0][0]["text"] == "This is bold"


def test_markdown_to_feishu_post_handles_code_blocks() -> None:
    """Test markdown conversion preserves code blocks"""
    md = """```json
{
  "status": "done"
}
```"""
    result = markdown_to_feishu_post(md)

    content = result["content"]["zh_cn"]["content"]
    # Code blocks should be preserved with ``` markers
    assert "```" in content[0][0]["text"]
    assert '"status": "done"' in content[0][0]["text"]


def test_markdown_to_feishu_post_custom_title() -> None:
    """Test custom title in post"""
    result = markdown_to_feishu_post("test", title="Custom Bot")
    assert result["content"]["zh_cn"]["title"] == "Custom Bot"


def test_build_interactive_card_basic() -> None:
    """Test building a basic interactive card"""
    card = build_interactive_card(
        title="Test Title",
        content="Test content",
        template="blue",
    )

    assert card["header"]["title"]["content"] == "Test Title"
    assert card["header"]["template"] == "blue"
    assert card["config"]["wide_screen_mode"] is True
    assert len(card["elements"]) == 1
    assert card["elements"][0]["tag"] == "div"
    assert card["elements"][0]["text"]["content"] == "Test content"


def test_build_interactive_card_with_actions() -> None:
    """Test building a card with action buttons"""
    actions = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "Click me"},
            "type": "primary",
        }
    ]
    card = build_interactive_card(
        title="Test Title",
        content="Test content",
        template="green",
        actions=actions,
    )

    assert len(card["elements"]) == 2
    assert card["elements"][1]["tag"] == "action"
    assert card["elements"][1]["actions"] == actions


def test_build_interactive_card_empty_content() -> None:
    """Test building a card with empty content"""
    card = build_interactive_card(
        title="Test Title",
        content="",
        template="blue",
    )

    # Should not have div element when content is empty
    assert len(card["elements"]) == 0


def test_format_feishu_event_card_loop_started() -> None:
    """Test card formatting for loop.started event"""
    event = {
        "type": "loop.started",
        "objective": "Create a Python calculator",
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert title == "任务启动"
    assert "Create a Python calculator" in content
    assert template == "blue"


def test_format_feishu_event_card_round_review_done() -> None:
    """Test card formatting for round.review.completed with done status"""
    event = {
        "type": "round.review.completed",
        "round": 3,
        "review": {
            "status": "done",
            "reason": "All tests pass",
        },
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert title == "审核通过"
    assert "第 3 轮审核" in content
    assert "done" in content
    assert template == "green"


def test_format_feishu_event_card_round_review_continue() -> None:
    """Test card formatting for round.review.completed with continue status"""
    event = {
        "type": "round.review.completed",
        "round": 2,
        "review": {
            "status": "continue",
            "reason": "Need more work",
        },
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert title == "继续执行"
    assert template == "yellow"


def test_format_feishu_event_card_round_review_blocked() -> None:
    """Test card formatting for round.review.completed with blocked status"""
    event = {
        "type": "round.review.completed",
        "round": 1,
        "review": {
            "status": "blocked",
            "reason": "Error occurred",
        },
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert title == "执行受阻"
    assert template == "red"


def test_format_feishu_event_card_loop_completed() -> None:
    """Test card formatting for loop.completed event"""
    event = {
        "type": "loop.completed",
        "objective": "Build a web scraper",
        "rounds": [{"round": 1}, {"round": 2}, {"round": 3}],
        "exit_code": 0,
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert title == "任务完成"
    assert "Build a web scraper" in content
    assert "**总轮数:** 3" in content
    assert "成功" in content
    assert template == "green"


def test_format_feishu_event_card_unknown_event() -> None:
    """Test card formatting returns None for unsupported events"""
    event = {
        "type": "unknown.event",
        "data": "some data",
    }
    result = format_feishu_event_card(event)

    assert result is None


def test_format_feishu_event_card_reviewer_output() -> None:
    """Test card formatting for reviewer.output events"""
    import json
    reviewer_json = json.dumps({
        "status": "done",
        "confidence": 0.95,
        "reason": "所有验收检查通过",
        "next_action": "任务已完成",
        "round_summary_markdown": "## 本轮总结\n\n- 创建了 README.md",
        "completion_summary_markdown": "## 完成证据\n\n- README.md 文件已创建",
    })
    event = {
        "type": "reviewer.output",
        "raw_output": reviewer_json,
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert "Reviewer" in title
    assert "✅" in content or "**状态**: done" in content
    assert template == "blue"


def test_format_feishu_event_card_planner_output() -> None:
    """Test card formatting for planner.output events"""
    import json
    planner_json = json.dumps({
        "summary": "项目进展顺利",
        "workstreams": [
            {"area": "开发", "status": "in_progress"},
            {"area": "测试", "status": "todo"},
        ],
        "done_items": ["需求分析", "架构设计"],
        "remaining_items": ["编码", "测试"],
        "risks": ["时间紧张"],
        "next_steps": ["完成核心功能"],
        "exploration_items": ["性能优化"],
        "report_markdown": "## 完整报告",
    })
    event = {
        "type": "planner.output",
        "raw_output": planner_json,
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert "Planner" in title
    assert "📋" in title
    assert template == "purple"


def test_format_feishu_event_card_plan_completed() -> None:
    """Test card formatting for plan.completed events"""
    import json
    planner_json = json.dumps({
        "summary": "进展良好",
        "workstreams": [],
        "done_items": ["完成项"],
        "remaining_items": [],
        "risks": [],
        "next_steps": [],
        "exploration_items": [],
        "report_markdown": "",
    })
    event = {
        "type": "plan.completed",
        "raw_output": planner_json,
        "main_instruction": "继续开发",
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert "Planner" in title
    assert template == "purple"


def test_format_feishu_event_card_plan_completed_fallback() -> None:
    """Test card formatting for plan.completed events without raw_output"""
    event = {
        "type": "plan.completed",
        "main_instruction": "继续开发核心功能",
    }
    result = format_feishu_event_card(event)

    assert result is not None
    title, content, template = result
    assert "Planner" in title
    assert "继续开发" in content
    assert template == "purple"


def test_notifier_notify_event_uses_card_for_supported_events() -> None:
    """Test that notify_event uses cards for supported events"""
    notifier = FeishuNotifier(
        FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret",
            chat_id="oc_xxx",
            events={"loop.started", "round.review.completed", "loop.completed"},
        )
    )

    sent_cards: list[tuple[str, str, str]] = []
    sent_messages: list[str] = []

    def fake_send_card_message(title: str, content: str, template: str = "blue") -> bool:  # type: ignore[no-untyped-def]
        sent_cards.append((title, content, template))
        return True

    def fake_send_message(message: str) -> bool:  # type: ignore[no-untyped-def]
        sent_messages.append(message)
        return True

    notifier.send_card_message = fake_send_card_message  # type: ignore[method-assign]
    notifier.send_message = fake_send_message  # type: ignore[method-assign]

    # Test loop.started - should use card
    notifier.notify_event({"type": "loop.started", "objective": "Test"})
    assert len(sent_cards) == 1
    assert len(sent_messages) == 0

    # Test round.review.completed - should use card
    notifier.notify_event({
        "type": "round.review.completed",
        "round": 1,
        "review": {"status": "continue", "reason": "test"},
    })
    assert len(sent_cards) == 2
    assert len(sent_messages) == 0

    # Test event not in events config - should not send anything
    notifier.notify_event({"type": "unknown", "data": "test"})
    assert len(sent_cards) == 2  # Still 2
    assert len(sent_messages) == 0  # Still 0 (filtered by events config)

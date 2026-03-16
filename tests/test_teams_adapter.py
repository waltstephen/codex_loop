import json

from codex_autoloop.teams_adapter import (
    TeamsConfig,
    TeamsNotifier,
    extract_teams_activity_text,
    extract_teams_conversation_reference,
    parse_teams_command_text,
    split_teams_message,
)


def test_parse_teams_command_text_supports_extended_commands() -> None:
    assert parse_teams_command_text(text="<at>ArgusBot</at> /mode", plain_text_kind="inject").kind == "mode-menu"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/mode auto", plain_text_kind="inject").text == "auto"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/btw explain repo", plain_text_kind="inject").kind == "btw"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/plan tighten scope", plain_text_kind="inject").kind == "plan"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/review must pass tests", plain_text_kind="inject").kind == "review"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/show-plan", plain_text_kind="inject").kind == "show-plan"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/show-review 4", plain_text_kind="inject").text == "4"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/confirm-send", plain_text_kind="inject").kind == "attachments-confirm"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="/cancel-send", plain_text_kind="inject").kind == "attachments-cancel"  # type: ignore[union-attr]


def test_parse_teams_command_text_plain_text_kind_is_configurable() -> None:
    assert parse_teams_command_text(text="continue", plain_text_kind="inject").kind == "inject"  # type: ignore[union-attr]
    assert parse_teams_command_text(text="new task", plain_text_kind="run").kind == "run"  # type: ignore[union-attr]


def test_extract_teams_activity_text_strips_tags_and_mentions() -> None:
    activity = {"text": "<div><at>ArgusBot</at> /run build dashboard</div>"}
    assert extract_teams_activity_text(activity) == "/run build dashboard"


def test_extract_teams_conversation_reference_from_activity() -> None:
    activity = {
        "type": "message",
        "id": "activity-1",
        "serviceUrl": "https://smba.trafficmanager.net/amer/",
        "channelId": "msteams",
        "from": {"id": "29:user", "name": "User"},
        "recipient": {"id": "28:bot", "name": "ArgusBot"},
        "conversation": {"id": "conv-123"},
        "channelData": {"tenant": {"id": "tenant-1"}},
    }
    reference = extract_teams_conversation_reference(
        activity=activity,
        fallback_bot_id="app-id",
        fallback_bot_name="ArgusBot",
    )
    assert reference is not None
    assert reference.conversation_id == "conv-123"
    assert reference.service_url == "https://smba.trafficmanager.net/amer/"
    assert reference.bot_id == "28:bot"
    assert reference.user_id == "29:user"
    assert reference.tenant_id == "tenant-1"


def test_teams_notifier_updates_and_persists_reference(tmp_path) -> None:  # type: ignore[no-untyped-def]
    reference_file = tmp_path / "teams_reference.json"
    notifier = TeamsNotifier(
        TeamsConfig(
            app_id="app-id",
            app_password="secret",
            reference_file=str(reference_file),
            events=set(),
        )
    )
    notifier.update_reference_from_activity(
        {
            "type": "message",
            "id": "activity-1",
            "serviceUrl": "https://smba.trafficmanager.net/amer/",
            "channelId": "msteams",
            "from": {"id": "29:user", "name": "User"},
            "recipient": {"id": "28:bot", "name": "ArgusBot"},
            "conversation": {"id": "conv-123"},
            "channelData": {"tenant": {"id": "tenant-1"}},
        }
    )
    payload = json.loads(reference_file.read_text(encoding="utf-8"))
    assert payload["conversation_id"] == "conv-123"
    assert payload["service_url"] == "https://smba.trafficmanager.net/amer/"


def test_split_teams_message_preserves_full_text() -> None:
    text = "a" * 1700 + "\n" + "b" * 1700
    chunks = split_teams_message(text, max_chunk_chars=1500)
    assert len(chunks) >= 2
    assert "".join(chunk.replace("\n", "") for chunk in chunks).count("a") >= 1500
    assert "".join(chunk.replace("\n", "") for chunk in chunks).count("b") >= 1500

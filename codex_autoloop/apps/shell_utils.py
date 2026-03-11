from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_telegram_events(raw: str) -> set[str]:
    values = [item.strip() for item in raw.split(",")]
    return {item for item in values if item}


def looks_like_bot_token(token: str) -> bool:
    if ":" not in token:
        return False
    left, right = token.split(":", 1)
    return left.isdigit() and len(right) >= 10


def resolve_operator_messages_file(
    *,
    explicit_path: str | None,
    control_file: str | None,
    state_file: str | None,
) -> str | None:
    if explicit_path:
        return explicit_path
    if control_file:
        return str(Path(control_file).resolve().parent / "operator_messages.md")
    if state_file:
        return str(Path(state_file).resolve().parent / "operator_messages.md")
    return None


def format_control_status(state: dict[str, Any]) -> str:
    status = state.get("status", "unknown")
    round_index = state.get("round", 0)
    session_id = state.get("session_id")
    success = state.get("success")
    stop_reason = state.get("stop_reason")
    lines = [
        "[autoloop] status",
        f"status={status}",
        f"round={round_index}",
        f"session_id={session_id}",
    ]
    if success is not None:
        lines.append(f"success={success}")
    if stop_reason:
        lines.append(f"stop_reason={stop_reason}")
    return "\n".join(lines)


def control_help_text() -> str:
    return (
        "[autoloop] control commands\n"
        "/status - show loop status\n"
        "/inject <instruction> - interrupt main agent and apply new instruction\n"
        "/stop - interrupt and stop loop\n"
        "/help - show command help\n"
        "Plain text message is treated as instruction inject by default.\n"
        "Voice/audio message will be transcribed by Whisper when enabled."
    )

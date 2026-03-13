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
    default_root: str | None = None,
) -> str | None:
    if explicit_path:
        return explicit_path
    if control_file:
        return str(Path(control_file).resolve().parent / "operator_messages.md")
    if state_file:
        return str(Path(state_file).resolve().parent / "operator_messages.md")
    if default_root:
        return str(Path(default_root).resolve() / "operator_messages.md")
    return None


def resolve_plan_overview_file(
    *,
    explicit_path: str | None,
    operator_messages_file: str | None,
    control_file: str | None,
    state_file: str | None,
    default_root: str | None = None,
) -> str:
    if explicit_path:
        return explicit_path
    base = _resolve_artifact_dir(
        operator_messages_file=operator_messages_file,
        control_file=control_file,
        state_file=state_file,
        default_root=default_root,
    )
    return str(base / "plan_overview.md")


def resolve_review_summaries_dir(
    *,
    explicit_path: str | None,
    operator_messages_file: str | None,
    control_file: str | None,
    state_file: str | None,
    default_root: str | None = None,
) -> str:
    if explicit_path:
        return explicit_path
    base = _resolve_artifact_dir(
        operator_messages_file=operator_messages_file,
        control_file=control_file,
        state_file=state_file,
        default_root=default_root,
    )
    return str(base / "review_summaries")


def format_control_status(state: dict[str, Any]) -> str:
    status = state.get("status", "unknown")
    round_index = state.get("round", 0)
    session_id = state.get("session_id")
    success = state.get("success")
    stop_reason = state.get("stop_reason")
    plan_mode = state.get("plan_mode")
    latest_plan_next_explore = state.get("latest_plan_next_explore")
    plan_overview_file = state.get("plan_overview_file")
    review_summaries_dir = state.get("review_summaries_dir")
    lines = [
        "[autoloop] status",
        f"status={status}",
        f"round={round_index}",
        f"session_id={session_id}",
    ]
    if plan_mode:
        lines.append(f"plan_mode={plan_mode}")
    if latest_plan_next_explore:
        lines.append(f"latest_plan_next_explore={latest_plan_next_explore}")
    if success is not None:
        lines.append(f"success={success}")
    if stop_reason:
        lines.append(f"stop_reason={stop_reason}")
    if plan_overview_file:
        lines.append(f"plan_overview_file={plan_overview_file}")
    if review_summaries_dir:
        lines.append(f"review_summaries_dir={review_summaries_dir}")
    return "\n".join(lines)


def control_help_text() -> str:
    return (
        "[autoloop] control commands\n"
        "/status - show loop status\n"
        "/inject <instruction> - interrupt main agent and apply new instruction\n"
        "/mode <off|auto|record> - hot-switch the current plan mode\n"
        "/plan <direction> - send extension/direction input to the plan agent only\n"
        "/review <criteria> - send audit criteria to the reviewer only\n"
        "/show-plan - print the current plan overview markdown\n"
        "/show-review [round] - print review summaries markdown (latest index or a specific round)\n"
        "/stop - interrupt and stop loop\n"
        "/help - show command help\n"
        "Plain text message is treated as instruction inject by default.\n"
        "Voice/audio message will be transcribed by Whisper when enabled."
    )


def _resolve_artifact_dir(
    *,
    operator_messages_file: str | None,
    control_file: str | None,
    state_file: str | None,
    default_root: str | None = None,
) -> Path:
    if operator_messages_file:
        return Path(operator_messages_file).resolve().parent
    if control_file:
        return Path(control_file).resolve().parent
    if state_file:
        return Path(state_file).resolve().parent
    if default_root:
        return Path(default_root).resolve()
    return Path(".").resolve() / ".codex_autoloop"

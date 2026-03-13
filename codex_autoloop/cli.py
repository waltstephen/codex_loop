from __future__ import annotations

import argparse
import json

from .apps.cli_app import run_cli
from .apps.shell_utils import (
    control_help_text,
    format_control_status,
    looks_like_bot_token,
    parse_telegram_events,
    resolve_plan_overview_file,
    resolve_review_summaries_dir,
    resolve_operator_messages_file,
)

__all__ = [
    "build_parser",
    "control_help_text",
    "format_control_status",
    "looks_like_bot_token",
    "parse_telegram_events",
    "resolve_plan_overview_file",
    "resolve_review_summaries_dir",
    "resolve_operator_messages_file",
]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    objective = " ".join(args.objective).strip()
    if not objective:
        parser.error("objective cannot be empty")
    if args.stall_soft_idle_seconds < 0:
        parser.error("--stall-soft-idle-seconds must be >= 0")
    if args.stall_hard_idle_seconds < 0:
        parser.error("--stall-hard-idle-seconds must be >= 0")
    if (
        args.stall_soft_idle_seconds > 0
        and args.stall_hard_idle_seconds > 0
        and args.stall_hard_idle_seconds < args.stall_soft_idle_seconds
    ):
        parser.error("--stall-hard-idle-seconds must be >= --stall-soft-idle-seconds")

    try:
        payload, exit_code = run_cli(args)
    except ValueError as exc:
        parser.error(str(exc))
        return

    print(json.dumps(payload, ensure_ascii=True, indent=2))
    raise SystemExit(exit_code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-autoloop",
        description=(
            "Run Codex in an automatic supervisor loop. "
            "A reviewer sub-agent gates completion and can force additional rounds."
        ),
    )
    parser.add_argument("objective", nargs="+", help="Task objective passed to the primary agent.")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary path.")
    parser.add_argument("--session-id", default=None, help="Resume an existing Codex exec session id.")
    parser.add_argument("--max-rounds", type=int, default=50, help="Maximum primary-agent rounds.")
    parser.add_argument(
        "--max-no-progress-rounds",
        type=int,
        default=3,
        help="Stop if repeated rounds produce identical main summary.",
    )
    parser.add_argument(
        "--check",
        action="append",
        help="Acceptance shell command (repeatable). All checks must pass before completion.",
    )
    parser.add_argument(
        "--check-timeout-seconds",
        type=int,
        default=1200,
        help="Timeout per acceptance check command.",
    )
    parser.add_argument("--main-model", default=None, help="Primary agent model override.")
    parser.add_argument("--reviewer-model", default=None, help="Reviewer sub-agent model override.")
    parser.add_argument("--plan-model", default=None, help="Plan agent model override.")
    parser.add_argument(
        "--main-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Primary agent reasoning effort override.",
    )
    parser.add_argument(
        "--reviewer-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Reviewer sub-agent reasoning effort override.",
    )
    parser.add_argument(
        "--plan-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Plan agent reasoning effort override.",
    )
    parser.add_argument(
        "--main-extra-arg",
        action="append",
        help="Extra argument passed to main `codex exec` command (repeatable).",
    )
    parser.add_argument(
        "--reviewer-extra-arg",
        action="append",
        help="Extra argument passed to reviewer `codex exec` command (repeatable).",
    )
    parser.add_argument(
        "--plan-extra-arg",
        action="append",
        help="Extra argument passed to planner `codex exec` command (repeatable).",
    )
    parser.add_argument(
        "--plan-mode",
        default="auto",
        choices=["off", "auto", "record"],
        help="Plan agent mode: off, auto follow-up, or record-only.",
    )
    parser.add_argument("--skip-git-repo-check", action="store_true", help="Pass through to Codex CLI.")
    parser.add_argument("--full-auto", action="store_true", help="Pass `--full-auto` to Codex CLI.")
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Pass `--dangerously-bypass-approvals-and-sandbox` to Codex CLI.",
    )
    parser.add_argument("--state-file", default=None, help="Write state JSON after each loop round.")
    parser.add_argument(
        "--operator-messages-file",
        default=None,
        help="Markdown document path for operator message history used by reviewer.",
    )
    parser.add_argument(
        "--plan-overview-file",
        default=None,
        help="Markdown document path for the plan agent overall summary.",
    )
    parser.add_argument(
        "--review-summaries-dir",
        default=None,
        help="Directory for per-round reviewer summary markdown files.",
    )
    parser.add_argument(
        "--control-file",
        default=None,
        help="Local JSONL control file for terminal commands (inject/stop/status).",
    )
    parser.add_argument(
        "--control-poll-interval-seconds",
        type=int,
        default=1,
        help="Polling interval for local control file.",
    )
    parser.add_argument(
        "--stall-soft-idle-seconds",
        type=int,
        default=1200,
        help=(
            "Soft idle threshold in seconds. When exceeded without new output, "
            "stall sub-agent inspects recent messages and decides whether to restart."
        ),
    )
    parser.add_argument(
        "--stall-hard-idle-seconds",
        type=int,
        default=10800,
        help=(
            "Hard idle threshold in seconds. When exceeded without new output, "
            "force a restart regardless of sub-agent decision."
        ),
    )
    parser.add_argument("--dashboard", action="store_true", help="Serve local live dashboard while running.")
    parser.add_argument("--dashboard-host", default="127.0.0.1", help="Dashboard host bind address.")
    parser.add_argument("--dashboard-port", type=int, default=8787, help="Dashboard TCP port.")
    parser.add_argument("--telegram-bot-token", default=None, help="Telegram bot token for progress messages.")
    parser.add_argument(
        "--telegram-chat-id",
        default="auto",
        help="Telegram chat id to receive messages. Use 'auto' to resolve from updates.",
    )
    parser.add_argument(
        "--telegram-events",
        default="loop.started,round.review.completed,loop.completed",
        help="Comma-separated event names to send to Telegram.",
    )
    parser.add_argument(
        "--telegram-timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout for Telegram API calls.",
    )
    parser.add_argument(
        "--telegram-chat-id-resolve-timeout-seconds",
        type=int,
        default=90,
        help="Seconds to poll getUpdates when resolving chat_id=auto.",
    )
    parser.add_argument(
        "--telegram-no-typing",
        action="store_true",
        help="Disable Telegram typing heartbeats during loop execution.",
    )
    parser.add_argument(
        "--telegram-typing-interval-seconds",
        type=int,
        default=4,
        help="Seconds between Telegram typing heartbeats.",
    )
    parser.add_argument(
        "--telegram-live-updates",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable batched live agent message push to Telegram.",
    )
    parser.add_argument(
        "--telegram-live-interval-seconds",
        type=int,
        default=30,
        help="Push interval for Telegram live updates; sends only when there are changes.",
    )
    parser.add_argument(
        "--telegram-control",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable Telegram inbound control commands (/inject, /stop, /status).",
    )
    parser.add_argument(
        "--telegram-control-poll-interval-seconds",
        type=int,
        default=2,
        help="Polling interval for Telegram control command loop.",
    )
    parser.add_argument(
        "--telegram-control-long-poll-timeout-seconds",
        type=int,
        default=20,
        help="Long-poll timeout for Telegram getUpdates control loop.",
    )
    parser.add_argument(
        "--telegram-control-plain-text-inject",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat plain text Telegram messages as injected instruction updates.",
    )
    parser.add_argument(
        "--telegram-control-whisper",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable Whisper transcription for Telegram voice/audio control messages.",
    )
    parser.add_argument(
        "--telegram-control-whisper-api-key",
        default=None,
        help="OpenAI API key for Whisper. Defaults to OPENAI_API_KEY.",
    )
    parser.add_argument(
        "--telegram-control-whisper-model",
        default="whisper-1",
        help="OpenAI transcription model used for Telegram voice/audio messages.",
    )
    parser.add_argument(
        "--telegram-control-whisper-base-url",
        default="https://api.openai.com/v1",
        help="OpenAI-compatible API base URL for Whisper transcription.",
    )
    parser.add_argument(
        "--telegram-control-whisper-timeout-seconds",
        type=int,
        default=90,
        help="Timeout in seconds for Whisper transcription requests.",
    )
    parser.add_argument(
        "--live-terminal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable realtime terminal printing of agent messages.",
    )
    parser.add_argument(
        "--verbose-events",
        action="store_true",
        help="Print raw Codex JSONL and stderr lines while running.",
    )
    return parser


if __name__ == "__main__":
    main()

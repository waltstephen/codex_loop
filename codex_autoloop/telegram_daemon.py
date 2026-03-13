from __future__ import annotations

import argparse

from .model_catalog import MODEL_PRESETS
from .apps.daemon_app import build_child_command, format_status, help_text, resolve_saved_session_id, run_telegram_daemon
from .token_lock import default_token_lock_dir

__all__ = ["build_child_command", "format_status", "help_text", "resolve_saved_session_id", "build_parser"]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run_telegram_daemon(args)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-autoloop-telegram-daemon",
        description="Keep a Telegram command daemon online and launch codex-autoloop runs on demand.",
    )
    parser.add_argument("--telegram-bot-token", required=True, help="Telegram bot token.")
    parser.add_argument(
        "--telegram-chat-id",
        default="auto",
        help="Authorized chat id. Use auto to resolve from updates.",
    )
    parser.add_argument(
        "--telegram-chat-id-resolve-timeout-seconds",
        type=int,
        default=120,
        help="Timeout for chat id auto resolution.",
    )
    parser.add_argument(
        "--codex-autoloop-bin",
        default="codex-autoloop",
        help="Executable used to launch child runs.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=2,
        help="Poll interval between retries.",
    )
    parser.add_argument(
        "--long-poll-timeout-seconds",
        type=int,
        default=20,
        help="Telegram getUpdates long-poll timeout.",
    )
    parser.add_argument(
        "--logs-dir",
        default=".codex_daemon/logs",
        help="Directory for child run logs.",
    )
    parser.add_argument(
        "--bus-dir",
        default=".codex_daemon/bus",
        help="Directory for daemon control bus files.",
    )
    parser.add_argument(
        "--token-lock-dir",
        default=default_token_lock_dir(),
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument(
        "--run-cd",
        default=".",
        help="Working directory for child codex-autoloop runs.",
    )
    parser.add_argument("--run-max-rounds", type=int, default=50, help="Child codex-autoloop max rounds.")
    parser.add_argument(
        "--run-model-preset",
        default="cheap",
        help=f"Model preset name for child runs ({', '.join(item.name for item in MODEL_PRESETS)}).",
    )
    parser.add_argument(
        "--run-plan-mode",
        default="auto",
        choices=["off", "auto", "record"],
        help="Plan agent mode for child runs.",
    )
    parser.add_argument("--run-main-model", default=None, help="Explicit main agent model override for child runs.")
    parser.add_argument(
        "--run-main-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Explicit main agent reasoning effort override for child runs.",
    )
    parser.add_argument(
        "--run-reviewer-model",
        default=None,
        help="Explicit reviewer agent model override for child runs.",
    )
    parser.add_argument(
        "--run-reviewer-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Explicit reviewer agent reasoning effort override for child runs.",
    )
    parser.add_argument("--run-plan-model", default=None, help="Explicit plan agent model override for child runs.")
    parser.add_argument(
        "--run-plan-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Explicit plan agent reasoning effort override for child runs.",
    )
    parser.add_argument("--run-check", action="append", default=[], help="Child acceptance check command (repeatable).")
    parser.add_argument(
        "--run-skip-git-repo-check",
        action="store_true",
        help="Pass --skip-git-repo-check to child run.",
    )
    parser.add_argument("--run-full-auto", action="store_true", help="Pass --full-auto to child run.")
    parser.add_argument(
        "--run-yolo",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable --yolo for child runs (default: enabled).",
    )
    parser.add_argument(
        "--run-stall-soft-idle-seconds",
        type=int,
        default=1200,
        help="Child soft idle watchdog threshold.",
    )
    parser.add_argument(
        "--run-stall-hard-idle-seconds",
        type=int,
        default=10800,
        help="Child hard idle watchdog threshold.",
    )
    parser.add_argument(
        "--run-state-file",
        default=".codex_daemon/last_state.json",
        help="Child --state-file value.",
    )
    parser.add_argument(
        "--run-telegram-events",
        default="loop.started,round.main.completed,round.review.completed,plan.completed,loop.completed",
        help="Telegram events forwarded by daemon-launched child runs.",
    )
    parser.add_argument(
        "--run-telegram-live-updates",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable child Telegram live agent message updates.",
    )
    parser.add_argument(
        "--run-telegram-live-interval-seconds",
        type=int,
        default=5,
        help="Push interval for child Telegram live updates.",
    )
    parser.add_argument(
        "--run-resume-last-session",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from last saved session_id when daemon starts a new idle run.",
    )
    parser.add_argument(
        "--run-no-dashboard",
        action="store_true",
        help="Disable dashboard in child run (default: enabled by child default args only).",
    )
    parser.add_argument(
        "--telegram-control-whisper",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable Whisper transcription for Telegram voice/audio commands.",
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
    return parser


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path

from .telegram_control import TelegramCommand, TelegramCommandPoller
from .telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    chat_id = (args.telegram_chat_id or "").strip()
    if chat_id.lower() in {"", "auto", "none", "null"}:
        print("Resolving chat_id from updates. Send /start or a message to your bot now...", file=sys.stderr)
        resolved = resolve_chat_id(
            bot_token=args.telegram_bot_token,
            timeout_seconds=args.telegram_chat_id_resolve_timeout_seconds,
            poll_interval_seconds=2,
            on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        )
        if not resolved:
            parser.error("Unable to resolve chat_id automatically.")
        chat_id = resolved
        print(f"Resolved chat_id={chat_id}", file=sys.stderr)

    notifier = TelegramNotifier(
        TelegramConfig(
            bot_token=args.telegram_bot_token,
            chat_id=chat_id,
            events=set(),
            typing_enabled=False,
        ),
        on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
    )

    child: subprocess.Popen[str] | None = None
    child_objective: str | None = None
    child_log_path: Path | None = None
    child_started_at: dt.datetime | None = None

    logs_dir = Path(args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    def start_child(objective: str) -> None:
        nonlocal child, child_objective, child_log_path, child_started_at
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        log_path = logs_dir / f"run-{timestamp}.log"
        cmd = build_child_command(args=args, objective=objective, chat_id=chat_id)
        log_file = log_path.open("w", encoding="utf-8")
        child = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, text=True)
        child_objective = objective
        child_log_path = log_path
        child_started_at = dt.datetime.utcnow()
        notifier.send_message(
            "[daemon] launched run\n"
            f"pid={child.pid}\n"
            f"objective={objective[:700]}\n"
            f"log={log_path}"
        )

    def on_command(command: TelegramCommand) -> None:
        nonlocal child
        if command.kind in {"help"}:
            notifier.send_message(help_text())
            return
        if command.kind in {"status"}:
            notifier.send_message(
                format_status(
                    child=child,
                    child_objective=child_objective,
                    child_log_path=child_log_path,
                    child_started_at=child_started_at,
                )
            )
            return
        if command.kind in {"run", "inject"}:
            objective = command.text.strip()
            if not objective:
                notifier.send_message("[daemon] missing objective. Use /run <objective>.")
                return
            if child is not None and child.poll() is None:
                notifier.send_message(
                    "[daemon] a run is already active.\n"
                    "Use /status to inspect it, or send /stop to stop it."
                )
                return
            start_child(objective)
            return
        if command.kind in {"stop"}:
            if child is None or child.poll() is not None:
                notifier.send_message("[daemon] no active run.")
                return
            child.terminate()
            notifier.send_message("[daemon] stop signal sent to active run.")
            return

    poller = TelegramCommandPoller(
        bot_token=args.telegram_bot_token,
        chat_id=chat_id,
        on_command=on_command,
        on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        poll_interval_seconds=args.poll_interval_seconds,
        long_poll_timeout_seconds=args.long_poll_timeout_seconds,
        plain_text_as_inject=True,
    )
    poller.start()
    notifier.send_message(
        "[daemon] online\n"
        "Send /run <objective> to start a new run.\n"
        "Commands: /status /stop /help"
    )

    try:
        while True:
            time.sleep(2)
            if child is None:
                continue
            rc = child.poll()
            if rc is None:
                continue
            notifier.send_message(
                "[daemon] run finished\n"
                f"exit_code={rc}\n"
                f"objective={str(child_objective or '')[:700]}\n"
                f"log={child_log_path}"
            )
            child = None
    except KeyboardInterrupt:
        print("Daemon interrupted.", file=sys.stderr)
    finally:
        poller.stop()
        if child is not None and child.poll() is None:
            child.terminate()
        notifier.close()


def build_child_command(*, args: argparse.Namespace, objective: str, chat_id: str) -> list[str]:
    cmd = [
        args.codex_autoloop_bin,
        "--max-rounds",
        str(args.run_max_rounds),
        "--telegram-bot-token",
        args.telegram_bot_token,
        "--telegram-chat-id",
        chat_id,
    ]
    if args.run_skip_git_repo_check:
        cmd.append("--skip-git-repo-check")
    if args.run_full_auto:
        cmd.append("--full-auto")
    if args.run_yolo:
        cmd.append("--yolo")
    for check in args.run_check:
        cmd.extend(["--check", check])
    if args.run_stall_soft_idle_seconds > 0:
        cmd.extend(["--stall-soft-idle-seconds", str(args.run_stall_soft_idle_seconds)])
    if args.run_stall_hard_idle_seconds > 0:
        cmd.extend(["--stall-hard-idle-seconds", str(args.run_stall_hard_idle_seconds)])
    if args.run_state_file:
        cmd.extend(["--state-file", args.run_state_file])
    if args.run_no_dashboard:
        cmd.append("--no-dashboard")
    cmd.append(objective)
    return cmd


def format_status(
    *,
    child: subprocess.Popen[str] | None,
    child_objective: str | None,
    child_log_path: Path | None,
    child_started_at: dt.datetime | None,
) -> str:
    if child is None or child.poll() is not None:
        return "[daemon] status=idle"
    elapsed = "unknown"
    if child_started_at is not None:
        elapsed_seconds = int((dt.datetime.utcnow() - child_started_at).total_seconds())
        elapsed = f"{elapsed_seconds}s"
    return (
        "[daemon] status=running\n"
        f"pid={child.pid}\n"
        f"elapsed={elapsed}\n"
        f"objective={str(child_objective or '')[:700]}\n"
        f"log={child_log_path}"
    )


def help_text() -> str:
    return (
        "[daemon] commands\n"
        "/run <objective> - start a new codex-autoloop run\n"
        "/status - daemon + child status\n"
        "/stop - stop active run\n"
        "/help - show this help\n"
        "Plain text message is treated as /run when idle."
    )


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
    parser.add_argument("--run-max-rounds", type=int, default=12, help="Child codex-autoloop max rounds.")
    parser.add_argument(
        "--run-check",
        action="append",
        default=[],
        help="Child acceptance check command (repeatable).",
    )
    parser.add_argument(
        "--run-skip-git-repo-check",
        action="store_true",
        help="Pass --skip-git-repo-check to child run.",
    )
    parser.add_argument("--run-full-auto", action="store_true", help="Pass --full-auto to child run.")
    parser.add_argument("--run-yolo", action="store_true", help="Pass --yolo to child run.")
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
        "--run-no-dashboard",
        action="store_true",
        help="Disable dashboard in child run (default: enabled by child default args only).",
    )
    return parser


if __name__ == "__main__":
    main()

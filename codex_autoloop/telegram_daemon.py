from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .daemon_bus import BusCommand, JsonlCommandBus, write_status
from .telegram_control import TelegramCommand, TelegramCommandPoller
from .telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id
from .token_lock import TokenLock, acquire_token_lock


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

    run_cwd = Path(args.run_cd).resolve()
    logs_dir = Path(args.logs_dir).resolve()
    bus_dir = Path(args.bus_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)
    bus_dir.mkdir(parents=True, exist_ok=True)
    events_log = logs_dir / "daemon-events.jsonl"

    token_lock: TokenLock | None = None
    try:
        token_lock = acquire_token_lock(
            token=args.telegram_bot_token,
            owner_info={
                "pid": os.getpid(),
                "chat_id": chat_id,
                "run_cwd": str(run_cwd),
                "bus_dir": str(bus_dir),
                "started_at": dt.datetime.utcnow().isoformat() + "Z",
            },
            lock_dir=args.token_lock_dir,
        )
    except RuntimeError as exc:
        parser.error(str(exc))

    daemon_bus = JsonlCommandBus(bus_dir / "daemon_commands.jsonl")
    status_path = bus_dir / "daemon_status.json"

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
    child_control_bus: JsonlCommandBus | None = None

    def log_event(event_type: str, **kwargs) -> None:
        payload = {
            "ts": dt.datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            **kwargs,
        }
        with events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def update_status() -> None:
        running = child is not None and child.poll() is None
        write_status(
            status_path,
            {
                "updated_at": dt.datetime.utcnow().isoformat() + "Z",
                "daemon_running": True,
                "running": running,
                "child_pid": child.pid if running else None,
                "child_objective": child_objective,
                "child_log_path": str(child_log_path) if child_log_path else None,
                "child_started_at": child_started_at.isoformat() + "Z" if child_started_at else None,
                "run_cwd": str(run_cwd),
                "logs_dir": str(logs_dir),
                "bus_dir": str(bus_dir),
                "events_log": str(events_log),
            },
        )

    def start_child(objective: str) -> None:
        nonlocal child, child_objective, child_log_path, child_started_at, child_control_bus
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        log_path = logs_dir / f"run-{timestamp}.log"
        control_path = bus_dir / f"child-control-{timestamp}.jsonl"
        messages_path = logs_dir / f"run-{timestamp}-operator_messages.md"
        child_control_bus = JsonlCommandBus(control_path)
        cmd = build_child_command(
            args=args,
            objective=objective,
            chat_id=chat_id,
            control_file=str(control_path),
            operator_messages_file=str(messages_path),
        )
        log_file = log_path.open("w", encoding="utf-8")
        child = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, text=True, cwd=run_cwd)
        child_objective = objective
        child_log_path = log_path
        child_started_at = dt.datetime.utcnow()
        notifier.send_message(
            "[daemon] launched run\n"
            f"pid={child.pid}\n"
            f"objective={objective[:700]}\n"
            f"log={log_path}"
        )
        log_event(
            "child.launched",
            pid=child.pid,
            objective=objective[:700],
            log_path=str(log_path),
            control_path=str(control_path),
            operator_messages_file=str(messages_path),
        )
        update_status()

    def send_reply(source: str, message: str) -> None:
        if source == "telegram":
            notifier.send_message(message)
        else:
            print(message, file=sys.stdout)
        log_event("reply.sent", source=source, message=message[:700])

    def forward_to_child(kind: str, text: str, source: str) -> bool:
        if child is None or child.poll() is not None:
            return False
        if child_control_bus is None:
            return False
        child_control_bus.publish(BusCommand(kind=kind, text=text, source=source, ts=time.time()))
        log_event("child.command.forwarded", source=source, kind=kind, text=text[:700])
        return True

    def handle_command(kind: str, text: str, source: str) -> None:
        nonlocal child, child_control_bus
        command = TelegramCommand(kind=kind, text=text)
        log_event("command.received", source=source, kind=kind, text=text[:700])
        if command.kind == "help":
            send_reply(source, help_text())
            return
        if command.kind == "status":
            send_reply(
                source,
                format_status(
                    child=child,
                    child_objective=child_objective,
                    child_log_path=child_log_path,
                    child_started_at=child_started_at,
                ),
            )
            return
        if command.kind in {"run", "inject"}:
            objective = command.text.strip()
            if not objective:
                send_reply(source, "[daemon] missing objective. Use /run <objective>.")
                return
            running = child is not None and child.poll() is None
            if running:
                if forward_to_child("inject", objective, source):
                    send_reply(
                        source,
                        "[daemon] inject forwarded to active run. "
                        "Child loop will interrupt and apply your new instruction.",
                    )
                else:
                    send_reply(source, "[daemon] active run exists but child control bus unavailable.")
                return
            start_child(objective)
            return
        if command.kind == "stop":
            running = child is not None and child.poll() is None
            if not running:
                send_reply(source, "[daemon] no active run.")
                return
            if forward_to_child("stop", "", source):
                send_reply(source, "[daemon] stop forwarded to active run.")
            else:
                assert child is not None
                child.terminate()
                send_reply(source, "[daemon] stop signal sent to active run.")
            return
        if command.kind == "daemon-stop":
            send_reply(source, "[daemon] stopping daemon.")
            raise SystemExit(0)

    def on_telegram_command(command: TelegramCommand) -> None:
        handle_command(command.kind, command.text, "telegram")

    poller = TelegramCommandPoller(
        bot_token=args.telegram_bot_token,
        chat_id=chat_id,
        on_command=on_telegram_command,
        on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        poll_interval_seconds=args.poll_interval_seconds,
        long_poll_timeout_seconds=args.long_poll_timeout_seconds,
        plain_text_as_inject=True,
        whisper_enabled=args.telegram_control_whisper,
        whisper_api_key=args.telegram_control_whisper_api_key,
        whisper_model=args.telegram_control_whisper_model,
        whisper_base_url=args.telegram_control_whisper_base_url,
        whisper_timeout_seconds=args.telegram_control_whisper_timeout_seconds,
    )
    poller.start()
    notifier.send_message(
        "[daemon] online\n"
        "Send /run <objective> to start a new run.\n"
        "Commands: /status /stop /help"
    )
    log_event(
        "daemon.started",
        run_cwd=str(run_cwd),
        logs_dir=str(logs_dir),
        bus_dir=str(bus_dir),
        token_hash=(token_lock.token_hash if token_lock else None),
    )
    update_status()

    try:
        while True:
            time.sleep(1)
            for item in daemon_bus.read_new():
                handle_command(item.kind, item.text, "terminal")
            if child is None:
                update_status()
                continue
            rc = child.poll()
            if rc is None:
                update_status()
                continue
            notifier.send_message(
                "[daemon] run finished\n"
                f"exit_code={rc}\n"
                f"objective={str(child_objective or '')[:700]}\n"
                f"log={child_log_path}"
            )
            log_event(
                "child.finished",
                exit_code=rc,
                objective=str(child_objective or "")[:700],
                log_path=str(child_log_path) if child_log_path else None,
            )
            child = None
            child_control_bus = None
            update_status()
    except KeyboardInterrupt:
        print("Daemon interrupted.", file=sys.stderr)
        log_event("daemon.interrupted")
    finally:
        poller.stop()
        if child is not None and child.poll() is None:
            child.terminate()
        write_status(
            status_path,
            {
                "updated_at": dt.datetime.utcnow().isoformat() + "Z",
                "daemon_running": False,
                "running": False,
            },
        )
        log_event("daemon.stopped")
        if token_lock is not None:
            token_lock.release()
        notifier.close()


def build_child_command(
    *,
    args: argparse.Namespace,
    objective: str,
    chat_id: str,
    control_file: str,
    operator_messages_file: str,
) -> list[str]:
    cmd = [
        args.codex_autoloop_bin,
        "--max-rounds",
        str(args.run_max_rounds),
        "--telegram-bot-token",
        args.telegram_bot_token,
        "--telegram-chat-id",
        chat_id,
        "--control-file",
        control_file,
        "--operator-messages-file",
        operator_messages_file,
        "--telegram-control-whisper-model",
        args.telegram_control_whisper_model,
        "--telegram-control-whisper-base-url",
        args.telegram_control_whisper_base_url,
        "--telegram-control-whisper-timeout-seconds",
        str(args.telegram_control_whisper_timeout_seconds),
    ]
    if args.telegram_control_whisper:
        cmd.append("--telegram-control-whisper")
    else:
        cmd.append("--no-telegram-control-whisper")
    if args.telegram_control_whisper_api_key:
        cmd.extend(["--telegram-control-whisper-api-key", args.telegram_control_whisper_api_key])
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
        "/inject <instruction> - inject instruction to active run (or run if idle)\n"
        "/status - daemon + child status\n"
        "/stop - stop active run\n"
        "/daemon-stop - stop daemon process\n"
        "/help - show this help\n"
        "Plain text message is treated as /run when idle.\n"
        "Voice/audio message will be transcribed by Whisper when enabled."
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
    parser.add_argument(
        "--bus-dir",
        default=".codex_daemon/bus",
        help="Directory for daemon control bus files.",
    )
    parser.add_argument(
        "--token-lock-dir",
        default="/tmp/codex-autoloop-token-locks",
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument(
        "--run-cd",
        default=".",
        help="Working directory for child codex-autoloop runs.",
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

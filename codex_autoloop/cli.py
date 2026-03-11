from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .control_state import LoopControlState
from .codex_runner import CodexRunner
from .dashboard import DashboardServer, DashboardStore
from .live_updates import (
    TelegramStreamReporter,
    TelegramStreamReporterConfig,
    extract_agent_message,
)
from .local_control import LocalControlCommand, LocalControlPoller
from .orchestrator import AutoLoopConfig, AutoLoopOrchestrator
from .reviewer import Reviewer
from .telegram_control import TelegramCommand, TelegramCommandPoller
from .telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id


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

    dashboard_store: DashboardStore | None = None
    dashboard_server: DashboardServer | None = None
    if args.dashboard:
        dashboard_store = DashboardStore(objective=objective)
        dashboard_server = DashboardServer(
            store=dashboard_store,
            host=args.dashboard_host,
            port=args.dashboard_port,
        )
        dashboard_server.start()
        print(
            f"Dashboard running at http://{args.dashboard_host}:{args.dashboard_port}",
            file=sys.stderr,
        )

    operator_messages_file = resolve_operator_messages_file(
        explicit_path=args.operator_messages_file,
        control_file=args.control_file,
        state_file=args.state_file,
    )
    telegram_notifier: TelegramNotifier | None = None
    telegram_stream_reporter: TelegramStreamReporter | None = None
    telegram_control_poller: TelegramCommandPoller | None = None
    local_control_poller: LocalControlPoller | None = None
    control_state = LoopControlState(operator_messages_file=operator_messages_file)
    control_state.record_message(text=objective, source="operator", kind="initial-objective")
    control_runtime_state: dict[str, Any] = {
        "status": "idle",
        "round": 0,
        "session_id": None,
        "updated_at": None,
    }
    raw_chat_id = (args.telegram_chat_id or "").strip()
    telegram_requested = bool(args.telegram_bot_token) or raw_chat_id.lower() not in {"", "auto"}
    if telegram_requested:
        if not args.telegram_bot_token:
            parser.error("--telegram-bot-token is required when Telegram notifications are enabled.")
        if not looks_like_bot_token(args.telegram_bot_token):
            print(
                "Warning: telegram bot token format looks wrong. "
                "Expected something like '123456:ABCDEF...'.",
                file=sys.stderr,
            )
        telegram_chat_id = raw_chat_id
        if telegram_chat_id.lower() in {"", "null", "none", "auto"}:
            print(
                "Resolving Telegram chat_id from recent updates. "
                "If needed, send /start to your bot now.",
                file=sys.stderr,
            )
            resolved_chat_id = resolve_chat_id(
                bot_token=args.telegram_bot_token,
                timeout_seconds=args.telegram_chat_id_resolve_timeout_seconds,
                poll_interval_seconds=2,
                on_error=lambda msg: print(f"[telegram] {msg}", file=sys.stderr),
            )
            if not resolved_chat_id:
                parser.error(
                    "Unable to resolve Telegram chat_id. "
                    "Send /start to bot and try again, or pass --telegram-chat-id explicitly."
                )
            telegram_chat_id = resolved_chat_id
            print(f"Resolved Telegram chat_id={telegram_chat_id}", file=sys.stderr)
        event_names = parse_telegram_events(args.telegram_events)
        telegram_notifier = TelegramNotifier(
            TelegramConfig(
                bot_token=args.telegram_bot_token,
                chat_id=telegram_chat_id,
                events=event_names,
                timeout_seconds=args.telegram_timeout_seconds,
                typing_enabled=(not args.telegram_no_typing),
                typing_interval_seconds=args.telegram_typing_interval_seconds,
            ),
            on_error=lambda msg: print(f"[telegram] {msg}", file=sys.stderr),
        )
        print("Telegram notifications enabled.", file=sys.stderr)
        if args.telegram_live_updates:
            telegram_stream_reporter = TelegramStreamReporter(
                notifier=telegram_notifier,
                config=TelegramStreamReporterConfig(
                    interval_seconds=args.telegram_live_interval_seconds,
                ),
                on_error=lambda msg: print(f"[telegram] {msg}", file=sys.stderr),
            )
            telegram_stream_reporter.start()

        if args.telegram_control:
            def on_command(command: TelegramCommand) -> None:
                if command.kind == "inject":
                    control_state.request_inject(command.text, source="telegram")
                    telegram_notifier.send_message(
                        "[autoloop] control ack\n"
                        "Action: inject\n"
                        "Main agent will be interrupted and resumed with your new instruction."
                    )
                    return
                if command.kind == "stop":
                    control_state.request_stop(source="telegram")
                    telegram_notifier.send_message(
                        "[autoloop] control ack\n"
                        "Action: stop\n"
                        "Current run will be interrupted and loop will stop."
                    )
                    return
                if command.kind == "status":
                    telegram_notifier.send_message(format_control_status(control_runtime_state))
                    return
                if command.kind == "help":
                    telegram_notifier.send_message(control_help_text())
                    return
                if command.kind == "run":
                    telegram_notifier.send_message(
                        "[autoloop] /run is available in daemon mode.\n"
                        "Current loop is already active; use /inject, /status, or /stop."
                    )
                    return

            telegram_control_poller = TelegramCommandPoller(
                bot_token=args.telegram_bot_token,
                chat_id=telegram_chat_id,
                on_command=on_command,
                on_error=lambda msg: print(f"[telegram-control] {msg}", file=sys.stderr),
                poll_interval_seconds=args.telegram_control_poll_interval_seconds,
                long_poll_timeout_seconds=args.telegram_control_long_poll_timeout_seconds,
                plain_text_as_inject=args.telegram_control_plain_text_inject,
                whisper_enabled=args.telegram_control_whisper,
                whisper_api_key=args.telegram_control_whisper_api_key,
                whisper_model=args.telegram_control_whisper_model,
                whisper_base_url=args.telegram_control_whisper_base_url,
                whisper_timeout_seconds=args.telegram_control_whisper_timeout_seconds,
            )
            telegram_control_poller.start()
            print("Telegram control channel enabled.", file=sys.stderr)

    if args.control_file:
        def on_local_control(command: LocalControlCommand) -> None:
            if command.kind == "inject":
                control_state.request_inject(command.text, source="terminal")
                print("[control] local inject received.", file=sys.stderr)
                return
            if command.kind == "stop":
                control_state.request_stop(source="terminal")
                print("[control] local stop received.", file=sys.stderr)
                return
            if command.kind == "status":
                print(format_control_status(control_runtime_state), file=sys.stderr)
                return
            if command.kind == "help":
                print(control_help_text(), file=sys.stderr)
                return

        local_control_poller = LocalControlPoller(
            control_file=args.control_file,
            on_command=on_local_control,
            on_error=lambda msg: print(f"[control] {msg}", file=sys.stderr),
            poll_interval_seconds=args.control_poll_interval_seconds,
        )
        local_control_poller.start()
        print(f"Local control channel enabled: {args.control_file}", file=sys.stderr)

    def on_event(stream: str, line: str) -> None:
        if dashboard_store is not None:
            dashboard_store.add_stream_line(stream=stream, line=line)
        extracted = extract_agent_message(stream, line)
        if extracted is not None:
            actor, message = extracted
            if args.live_terminal:
                print(f"\n[{actor} agent]\n{message}\n", file=sys.stderr)
            if telegram_stream_reporter is not None:
                telegram_stream_reporter.add_message(actor=actor, message=message)
        if not args.verbose_events:
            return
        prefix = f"[{stream}]"
        to_stderr = stream == "stderr" or stream.endswith(".stderr")
        print(f"{prefix} {line}", file=sys.stderr if to_stderr else sys.stdout)

    runner = CodexRunner(codex_bin=args.codex_bin, event_callback=on_event)
    reviewer = Reviewer(runner=runner)

    def on_loop_event(event: dict[str, Any]) -> None:
        update_runtime_state(control_runtime_state, event)
        if dashboard_store is not None:
            dashboard_store.apply_loop_event(event)
        if telegram_notifier is not None:
            telegram_notifier.notify_event(event)

    orchestrator = AutoLoopOrchestrator(
        runner=runner,
        reviewer=reviewer,
        config=AutoLoopConfig(
            objective=objective,
            max_rounds=args.max_rounds,
            max_no_progress_rounds=args.max_no_progress_rounds,
            check_commands=args.check or [],
            check_timeout_seconds=args.check_timeout_seconds,
            main_model=args.main_model,
            main_reasoning_effort=args.main_reasoning_effort,
            reviewer_model=args.reviewer_model,
            reviewer_reasoning_effort=args.reviewer_reasoning_effort,
            main_extra_args=args.main_extra_arg or [],
            reviewer_extra_args=args.reviewer_extra_arg or [],
            skip_git_repo_check=args.skip_git_repo_check,
            full_auto=args.full_auto,
            dangerous_yolo=args.yolo,
            state_file=args.state_file,
            initial_session_id=args.session_id,
            loop_event_callback=on_loop_event,
            stall_soft_idle_seconds=args.stall_soft_idle_seconds,
            stall_hard_idle_seconds=args.stall_hard_idle_seconds,
            external_interrupt_reason_provider=control_state.consume_interrupt_reason,
            pending_instruction_consumer=control_state.consume_pending_instruction,
            stop_requested_checker=control_state.is_stop_requested,
            operator_messages_provider=control_state.list_messages,
        ),
    )
    try:
        result = orchestrator.run()
        payload = {
            "success": result.success,
            "session_id": result.session_id,
            "stop_reason": result.stop_reason,
            "rounds": [
                {
                    "round": item.round_index,
                    "thread_id": item.thread_id,
                    "main_exit_code": item.main_exit_code,
                    "main_turn_completed": item.main_turn_completed,
                    "main_turn_failed": item.main_turn_failed,
                    "review_status": item.review.status,
                    "review_confidence": item.review.confidence,
                    "review_reason": item.review.reason,
                    "check_count": len(item.checks),
                    "checks_passed": all(check.passed for check in item.checks),
                }
                for item in result.rounds
            ],
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        raise SystemExit(0 if result.success else 2)
    finally:
        if telegram_stream_reporter is not None:
            telegram_stream_reporter.stop()
        if local_control_poller is not None:
            local_control_poller.stop()
        if telegram_control_poller is not None:
            telegram_control_poller.stop()
        if telegram_notifier is not None:
            telegram_notifier.close()
        if dashboard_server is not None:
            dashboard_server.stop()


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
        "--main-extra-arg",
        action="append",
        help="Extra argument passed to main `codex exec` command (repeatable).",
    )
    parser.add_argument(
        "--reviewer-extra-arg",
        action="append",
        help="Extra argument passed to reviewer `codex exec` command (repeatable).",
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


def update_runtime_state(state: dict[str, Any], event: dict[str, Any]) -> None:
    event_type = str(event.get("type", ""))
    state["updated_at"] = event.get("ts")
    if event_type == "loop.started":
        state["status"] = "running"
        state["session_id"] = event.get("session_id")
        state["round"] = 0
    elif event_type == "round.started":
        state["round"] = event.get("round_index", state.get("round", 0))
        state["session_id"] = event.get("session_id", state.get("session_id"))
    elif event_type == "round.main.completed":
        state["session_id"] = event.get("session_id", state.get("session_id"))
    elif event_type == "loop.completed":
        state["status"] = "completed"
        state["success"] = event.get("success")
        state["stop_reason"] = event.get("stop_reason")


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


if __name__ == "__main__":
    main()

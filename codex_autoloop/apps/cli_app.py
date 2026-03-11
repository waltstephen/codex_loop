from __future__ import annotations

import sys
from argparse import Namespace
from typing import Any

from ..adapters.control_channels import LocalBusControlChannel, TelegramControlChannel
from ..adapters.event_sinks import CompositeEventSink, DashboardEventSink, TelegramEventSink, TerminalEventSink
from ..codex_runner import CodexRunner
from ..core.engine import LoopConfig, LoopEngine
from ..core.state_store import LoopStateStore
from ..dashboard import DashboardServer, DashboardStore
from ..reviewer import Reviewer
from ..telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id
from .shell_utils import (
    control_help_text,
    format_control_status,
    looks_like_bot_token,
    parse_telegram_events,
    resolve_operator_messages_file,
)


def run_cli(args: Namespace) -> tuple[dict[str, Any], int]:
    objective = " ".join(args.objective).strip()
    dashboard_server: DashboardServer | None = None
    event_sink: CompositeEventSink | None = None
    control_channels: list[object] = []

    operator_messages_file = resolve_operator_messages_file(
        explicit_path=args.operator_messages_file,
        control_file=args.control_file,
        state_file=args.state_file,
    )
    state_store = LoopStateStore(
        objective=objective,
        state_file=args.state_file,
        operator_messages_file=operator_messages_file,
    )
    state_store.record_message(text=objective, source="operator", kind="initial-objective")

    sinks = [TerminalEventSink(live_terminal=args.live_terminal, verbose_events=args.verbose_events)]

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
        sinks.append(DashboardEventSink(dashboard_store))

    telegram_notifier: TelegramNotifier | None = None
    raw_chat_id = (args.telegram_chat_id or "").strip()
    telegram_requested = bool(args.telegram_bot_token) or raw_chat_id.lower() not in {"", "auto"}
    if telegram_requested:
        if not args.telegram_bot_token:
            raise ValueError("--telegram-bot-token is required when Telegram notifications are enabled.")
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
                raise ValueError(
                    "Unable to resolve Telegram chat_id. "
                    "Send /start to bot and try again, or pass --telegram-chat-id explicitly."
                )
            telegram_chat_id = resolved_chat_id
            print(f"Resolved Telegram chat_id={telegram_chat_id}", file=sys.stderr)

        telegram_notifier = TelegramNotifier(
            TelegramConfig(
                bot_token=args.telegram_bot_token,
                chat_id=telegram_chat_id,
                events=parse_telegram_events(args.telegram_events),
                timeout_seconds=args.telegram_timeout_seconds,
                typing_enabled=(not args.telegram_no_typing),
                typing_interval_seconds=args.telegram_typing_interval_seconds,
            ),
            on_error=lambda msg: print(f"[telegram] {msg}", file=sys.stderr),
        )
        print("Telegram notifications enabled.", file=sys.stderr)
        sinks.append(
            TelegramEventSink(
                notifier=telegram_notifier,
                live_updates=args.telegram_live_updates,
                live_interval_seconds=args.telegram_live_interval_seconds,
                on_error=lambda msg: print(f"[telegram] {msg}", file=sys.stderr),
            )
        )

        if args.telegram_control:
            control_channels.append(
                TelegramControlChannel(
                    bot_token=args.telegram_bot_token,
                    chat_id=telegram_chat_id,
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
            )
            print("Telegram control channel enabled.", file=sys.stderr)

    if args.control_file:
        control_channels.append(
            LocalBusControlChannel(
                path=args.control_file,
                source="terminal",
                on_error=lambda msg: print(f"[control] {msg}", file=sys.stderr),
                poll_interval_seconds=args.control_poll_interval_seconds,
            )
        )
        print(f"Local control channel enabled: {args.control_file}", file=sys.stderr)

    def reply_to_source(source: str, message: str) -> None:
        if source == "telegram" and telegram_notifier is not None:
            telegram_notifier.send_message(message)
            return
        print(message, file=sys.stderr)

    def on_control_command(command) -> None:
        if command.kind == "inject":
            state_store.request_inject(command.text, source=command.source)
            if command.source == "telegram" and telegram_notifier is not None:
                telegram_notifier.send_message(
                    "[autoloop] control ack\n"
                    "Action: inject\n"
                    "Main agent will be interrupted and resumed with your new instruction."
                )
            else:
                print("[control] local inject received.", file=sys.stderr)
            return
        if command.kind == "stop":
            state_store.request_stop(source=command.source)
            if command.source == "telegram" and telegram_notifier is not None:
                telegram_notifier.send_message(
                    "[autoloop] control ack\n"
                    "Action: stop\n"
                    "Current run will be interrupted and loop will stop."
                )
            else:
                print("[control] local stop received.", file=sys.stderr)
            return
        if command.kind == "status":
            reply_to_source(command.source, format_control_status(state_store.runtime_snapshot()))
            return
        if command.kind == "help":
            reply_to_source(command.source, control_help_text())
            return
        if command.kind == "run":
            reply_to_source(
                command.source,
                "[autoloop] /run is available in daemon mode.\n"
                "Current loop is already active; use /inject, /status, or /stop.",
            )

    for channel in control_channels:
        channel.start(on_control_command)

    event_sink = CompositeEventSink(sinks)
    runner = CodexRunner(codex_bin=args.codex_bin, event_callback=event_sink.handle_stream_line)
    reviewer = Reviewer(runner=runner)
    engine = LoopEngine(
        runner=runner,
        reviewer=reviewer,
        state_store=state_store,
        event_sink=event_sink,
        config=LoopConfig(
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
            stall_soft_idle_seconds=args.stall_soft_idle_seconds,
            stall_hard_idle_seconds=args.stall_hard_idle_seconds,
            initial_session_id=args.session_id,
        ),
    )

    try:
        result = engine.run()
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
        return payload, 0 if result.success else 2
    finally:
        for channel in reversed(control_channels):
            channel.stop()
        if event_sink is not None:
            event_sink.close()
        if dashboard_server is not None:
            dashboard_server.stop()

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .daemon_bus import BusCommand, JsonlCommandBus, read_status, write_status
from .model_catalog import MODEL_PRESETS, get_preset
from .planner_modes import (
    PLANNER_MODE_AUTO,
    PLANNER_MODE_CHOICES,
    planner_mode_allows_follow_up,
    resolve_planner_mode,
)
from .feishu_adapter import FeishuCommand, FeishuConfig, FeishuCommandPoller, FeishuNotifier
from .live_updates import ChildLogStreamFollower, GenericStreamReporter, TelegramStreamReporterConfig
from .telegram_control import TelegramCommand, TelegramCommandPoller
from .telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id
from .token_lock import TokenLock, acquire_token_lock

PLAN_MODE_EXECUTE_ONLY = "execute-only"
PLAN_MODE_FULLY_PLAN = "fully-plan"
PLAN_MODE_RECORD_ONLY = "record-only"
PLAN_MODES = {PLAN_MODE_EXECUTE_ONLY, PLAN_MODE_FULLY_PLAN, PLAN_MODE_RECORD_ONLY}
FORCE_FRESH_SESSION_KEY = "force_fresh_session"
FORCE_FRESH_REASON_KEY = "force_fresh_reason"
INVALID_ENCRYPTED_CONTENT_MARKER = "invalid encrypted content"


@dataclass
class PlanFollowUp:
    plan_id: str
    objective: str
    report_markdown: str
    created_at: dt.datetime
    auto_execute_at: dt.datetime | None
    awaiting_user_edit: bool = False
    auto_execute_enabled: bool = True


@dataclass
class GitCheckpointResult:
    ok_to_continue: bool
    message: str
    commit_hash: str | None = None


DEFAULT_CODEX_AUTOLOOP_CMD = f"{sys.executable} -m codex_autoloop.cli"
LOCAL_REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_autoloop_command(command: str) -> list[str]:
    parts = shlex.split(command) if command else []
    if not parts:
        raise ValueError("codex-autoloop command cannot be empty")
    return parts


def resolve_child_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [item for item in existing.split(os.pathsep) if item]
    repo_root = str(LOCAL_REPO_ROOT)
    if repo_root not in parts:
        parts.insert(0, repo_root)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.follow_up_auto_execute_seconds < 0:
        parser.error("--follow-up-auto-execute-seconds must be >= 0")
    run_planner_mode = resolve_planner_mode(planner_enabled_flag=args.run_planner, planner_mode=args.run_planner_mode)

    telegram_enabled = bool((args.telegram_bot_token or "").strip())
    chat_id = (args.telegram_chat_id or "").strip()
    if telegram_enabled and chat_id.lower() in {"", "auto", "none", "null"}:
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
    run_archive_log = logs_dir / "codexloop-run-archive.jsonl"
    operator_messages_path = logs_dir / "operator_messages.md"

    token_lock: TokenLock | None = None
    if telegram_enabled:
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

    notifier: TelegramNotifier | None = None
    feishu_notifier: FeishuNotifier | None = None
    if telegram_enabled:
        notifier = TelegramNotifier(
            TelegramConfig(
                bot_token=args.telegram_bot_token,
                chat_id=chat_id,
                events=set(),
                typing_enabled=False,
            ),
            on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        )
    feishu_enabled = bool(
        (args.feishu_app_id or "").strip()
        and (args.feishu_app_secret or "").strip()
        and (args.feishu_chat_id or "").strip()
    )
    if feishu_enabled:
        feishu_notifier = FeishuNotifier(
            FeishuConfig(
                app_id=args.feishu_app_id,
                app_secret=args.feishu_app_secret,
                chat_id=args.feishu_chat_id,
                receive_id_type=args.feishu_receive_id_type,
                events=set(),
                timeout_seconds=args.feishu_timeout_seconds,
            ),
            on_error=lambda msg: print(f"[feishu] {msg}", file=sys.stderr),
        )

    def notify(
        message: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        include_feishu: bool = True,
    ) -> None:
        if notifier is not None:
            notifier.send_message(message, reply_markup=reply_markup)
        if include_feishu and feishu_notifier is not None:
            feishu_notifier.send_message(format_external_message(message))
        if notifier is None and feishu_notifier is None:
            print(message, file=sys.stdout)

    child: subprocess.Popen[str] | None = None
    child_objective: str | None = None
    child_log_path: Path | None = None
    child_plan_report_path: Path | None = None
    child_plan_todo_path: Path | None = None
    child_started_at: dt.datetime | None = None
    child_control_bus: JsonlCommandBus | None = None
    child_run_id: str | None = None
    child_control_path: Path | None = None
    child_resume_session_id: str | None = None
    child_log_follower: ChildLogStreamFollower | None = None
    live_reporters: list[GenericStreamReporter] = []
    plan_mode = normalize_plan_mode(args.run_plan_mode)
    plan_request_delay_seconds = max(0, int(args.run_plan_request_delay_seconds))
    plan_auto_execute_delay_seconds = max(0, int(args.run_plan_auto_execute_delay_seconds))
    pending_plan_request: str | None = None
    pending_plan_auto_execute_at: dt.datetime | None = None
    pending_plan_generated_at: dt.datetime | None = None
    scheduled_plan_context: dict[str, Any] | None = None
    scheduled_plan_request_at: dt.datetime | None = None
    pending_follow_up: PlanFollowUp | None = None

    def log_event(event_type: str, **kwargs) -> None:
        payload = {
            "ts": dt.datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            **kwargs,
        }
        with events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def append_run_archive_record(*, event: str, **kwargs: Any) -> None:
        now = dt.datetime.utcnow()
        payload = {
            "ts": now.isoformat() + "Z",
            "date": now.date().isoformat(),
            "event": event,
            "workspace": str(run_cwd),
            **kwargs,
        }
        with run_archive_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def clear_planner_state(*, reason: str | None = None) -> None:
        nonlocal pending_plan_request, pending_plan_auto_execute_at, pending_plan_generated_at
        nonlocal scheduled_plan_context, scheduled_plan_request_at
        had_state = (
            pending_plan_request is not None
            or pending_plan_auto_execute_at is not None
            or scheduled_plan_request_at is not None
            or scheduled_plan_context is not None
        )
        pending_plan_request = None
        pending_plan_auto_execute_at = None
        pending_plan_generated_at = None
        scheduled_plan_context = None
        scheduled_plan_request_at = None
        if had_state and reason:
            log_event("plan.cleared", reason=reason)

    def update_status() -> None:
        running = child is not None and child.poll() is None
        last_session_id = resolve_resume_session_id(args.run_state_file, run_archive_log)
        force_fresh_session = is_force_fresh_session_requested(args.run_state_file)
        write_status(
            status_path,
            {
                "updated_at": dt.datetime.utcnow().isoformat() + "Z",
                "daemon_running": True,
                "running": running,
                "child_pid": child.pid if running else None,
                "child_objective": child_objective,
                "child_log_path": str(child_log_path) if child_log_path else None,
                "child_plan_report_path": str(child_plan_report_path) if child_plan_report_path else None,
                "child_plan_todo_path": str(child_plan_todo_path) if child_plan_todo_path else None,
                "child_started_at": child_started_at.isoformat() + "Z" if child_started_at else None,
                "last_session_id": last_session_id,
                "force_fresh_session": force_fresh_session,
                "run_cwd": str(run_cwd),
                "logs_dir": str(logs_dir),
                "bus_dir": str(bus_dir),
                "events_log": str(events_log),
                "run_archive_log": str(run_archive_log),
                "operator_messages_file": str(operator_messages_path),
                "plan_mode": plan_mode,
                "pending_plan_request": pending_plan_request,
                "pending_plan_generated_at": (
                    pending_plan_generated_at.isoformat() + "Z" if pending_plan_generated_at else None
                ),
                "pending_plan_auto_execute_at": (
                    pending_plan_auto_execute_at.isoformat() + "Z" if pending_plan_auto_execute_at else None
                ),
                "scheduled_plan_request_at": (
                    scheduled_plan_request_at.isoformat() + "Z" if scheduled_plan_request_at else None
                ),
            },
        )

    def start_child(objective: str, *, resume_last_session: bool = True) -> None:
        nonlocal child, child_objective, child_log_path, child_started_at, child_control_bus
        nonlocal child_run_id, child_control_path, child_resume_session_id
        nonlocal child_plan_report_path, child_plan_todo_path, pending_follow_up, child_log_follower
        clear_planner_state(reason="child_started")
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        log_path = logs_dir / f"run-{timestamp}.log"
        control_path = bus_dir / f"child-control-{timestamp}.jsonl"
        plan_report_path = logs_dir / f"run-{timestamp}-plan-report.md"
        plan_todo_path = logs_dir / f"run-{timestamp}-todo.md"
        messages_path = operator_messages_path
        force_fresh = is_force_fresh_session_requested(args.run_state_file)
        resume_session_id = (
            (None if force_fresh else resolve_resume_session_id(args.run_state_file, run_archive_log))
            if args.run_resume_last_session and resume_last_session
            else None
        )
        child_control_bus = JsonlCommandBus(control_path)
        pending_follow_up = None
        cmd = build_child_command(
            args=args,
            objective=objective,
            chat_id=chat_id,
            control_file=str(control_path),
            operator_messages_file=str(messages_path),
            plan_report_file=str(plan_report_path),
            plan_todo_file=str(plan_todo_path),
            resume_session_id=resume_session_id,
        )
        log_file = log_path.open("w", encoding="utf-8")
        child = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            text=True,
            cwd=run_cwd,
            env=resolve_child_env(),
        )
        child_objective = objective
        child_log_path = log_path
        child_plan_report_path = plan_report_path
        child_plan_todo_path = plan_todo_path
        child_started_at = dt.datetime.utcnow()
        child_run_id = timestamp
        child_control_path = control_path
        child_resume_session_id = resume_session_id
        if child_log_follower is not None:
            child_log_follower.stop()
            child_log_follower = None
        if live_reporters:
            child_log_follower = ChildLogStreamFollower(
                path=log_path,
                reporters=live_reporters,
                poll_interval_seconds=2,
            )
            child_log_follower.start()
        notify(
            "[daemon] launched run\n"
            f"pid={child.pid}\n"
            f"objective={objective[:700]}\n"
            f"log={log_path}",
            include_feishu=False,
        )
        log_event(
            "child.launched",
            pid=child.pid,
            objective=objective[:700],
            log_path=str(log_path),
            control_path=str(control_path),
            operator_messages_file=str(messages_path),
            plan_report_file=str(plan_report_path),
            plan_todo_file=str(plan_todo_path),
            resume_session_id=resume_session_id,
            run_id=timestamp,
        )
        append_run_archive_record(
            event="run.started",
            run_id=timestamp,
            pid=child.pid,
            objective=objective[:700],
            log_path=str(log_path),
            control_path=str(control_path),
            operator_messages_file=str(messages_path),
            resume_session_id=resume_session_id,
            force_fresh_session=force_fresh,
            plan_mode=plan_mode,
            started_at=child_started_at.isoformat() + "Z",
        )
        if force_fresh:
            log_event("session.fresh.applied", run_id=timestamp)
        update_status()

    def send_follow_up_prompt() -> None:
        if pending_follow_up is None:
            return
        countdown_text = "disabled"
        if pending_follow_up.auto_execute_at is not None:
            remaining = max(0, int((pending_follow_up.auto_execute_at - dt.datetime.utcnow()).total_seconds()))
            countdown_text = format_countdown(remaining)
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Execute Next Step", "callback_data": f"plan_run:{pending_follow_up.plan_id}"},
                    {"text": "Reject Plan", "callback_data": f"plan_reject:{pending_follow_up.plan_id}"},
                ],
                [
                    {"text": "Modify Then Execute", "callback_data": f"plan_modify:{pending_follow_up.plan_id}"},
                ]
            ]
        }
        message = (
            "[daemon] suggested next session\n"
            "The current run is finished. The planner recommends the follow-up objective below.\n"
            "Options:\n"
            "1. Direct execute\n"
            "2. Reject and wait for your instruction\n"
            "3. Modify and inherit this plan before execution\n"
            f"If you do nothing, daemon will auto-execute in {countdown_text}.\n"
            "Before execution, daemon will create a git checkpoint commit when the repo is dirty.\n"
            "This follow-up launches as a fresh session instead of resuming the old one.\n\n"
            f"{pending_follow_up.report_markdown[:3200]}"
        )
        notify(message, reply_markup=keyboard)

    def send_modify_prompt() -> None:
        if pending_follow_up is None:
            return
        notify(
            "[daemon] modify planned next session\n"
            "Send the revised objective or constraints now.\n"
            "Daemon will inherit the existing planner objective and append your changes before execution.\n\n"
            f"Current planned objective:\n{pending_follow_up.objective[:1500]}"
        )

    def launch_follow_up(
        *,
        follow_up: PlanFollowUp,
        source: str,
        override_text: str | None = None,
        auto_triggered: bool = False,
    ) -> bool:
        checkpoint = create_git_checkpoint(
            run_cwd=run_cwd,
            plan_id=follow_up.plan_id,
            auto_triggered=auto_triggered,
        )
        if checkpoint.message:
            send_reply(source, checkpoint.message)
        if not checkpoint.ok_to_continue:
            if auto_triggered:
                follow_up.auto_execute_enabled = False
                follow_up.auto_execute_at = None
            return False
        objective = follow_up.objective
        if override_text:
            objective = build_modified_follow_up_objective(
                base_objective=follow_up.objective,
                user_text=override_text,
            )
        start_child(objective, resume_last_session=False)
        return True

    def send_reply(source: str, message: str) -> None:
        if source == "telegram":
            notify(message)
        elif source == "feishu" and feishu_notifier is not None:
            feishu_notifier.send_message(format_external_message(message))
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

    def handle_command(command: TelegramCommand, source: str) -> None:
        nonlocal child, child_control_bus, pending_follow_up
        log_event("command.received", source=source, kind=command.kind, text=command.text[:700])
        if command.kind == "help":
            send_reply(source, help_text())
            return
        if command.kind == "status":
            last_session_id = resolve_resume_session_id(args.run_state_file, run_archive_log)
            send_reply(
                source,
                format_status(
                    child=child,
                    child_objective=child_objective,
                    child_log_path=child_log_path,
                    child_started_at=child_started_at,
                    last_session_id=last_session_id,
                    force_fresh_session=is_force_fresh_session_requested(args.run_state_file),
                    plan_mode=plan_mode,
                    pending_plan_request=pending_plan_request,
                    pending_plan_auto_execute_at=pending_plan_auto_execute_at,
                    scheduled_plan_request_at=scheduled_plan_request_at,
                ),
            )
            return
        if command.kind == "fresh-session":
            set_force_fresh_session_marker(
                args.run_state_file,
                enabled=True,
                reason=f"operator_requested_from_{source}",
            )
            running = child is not None and child.poll() is None
            append_run_archive_record(
                event="session.fresh.requested",
                source=source,
                running=running,
                active_run_id=child_run_id,
                active_objective=str(child_objective or "")[:700],
            )
            if running:
                send_reply(
                    source,
                    "[daemon] fresh session is armed for the next run. "
                    "Current run keeps its existing session.",
                )
            else:
                send_reply(source, "[daemon] fresh session armed. Next /run will not resume previous session_id.")
            update_status()
            return
        if command.kind in {"run", "inject"}:
            objective = command.text.strip()
            if not objective:
                send_reply(source, "[daemon] missing objective. Use /run <objective>.")
                return
            if (
                child is None or child.poll() is not None
            ) and pending_follow_up is not None and pending_follow_up.awaiting_user_edit:
                launched = launch_follow_up(
                    follow_up=pending_follow_up,
                    source=source,
                    override_text=objective,
                    auto_triggered=False,
                )
                if launched:
                    pending_follow_up = None
                else:
                    update_status()
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
            if pending_plan_request or scheduled_plan_request_at is not None:
                clear_planner_state(reason="manual_override")
                send_reply(source, "[daemon] pending plan request cleared by manual command.")
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
        handle_command(command, "telegram")

    def on_feishu_command(command: FeishuCommand) -> None:
        handle_command(TelegramCommand(kind=command.kind, text=command.text), "feishu")

    def schedule_plan_after_child_finish(
        *,
        objective: str,
        exit_code: int,
        log_path: Path | None,
        plan_report_path: Path | None,
    ) -> None:
        nonlocal pending_plan_request, pending_plan_auto_execute_at, pending_plan_generated_at
        nonlocal scheduled_plan_context, scheduled_plan_request_at
        if plan_mode == PLAN_MODE_EXECUTE_ONLY:
            clear_planner_state(reason="execute_only")
            return

        state_payload = read_status(args.run_state_file) if args.run_state_file else None
        finished_at = dt.datetime.utcnow()
        if plan_mode == PLAN_MODE_RECORD_ONLY:
            record_file = (
                Path(args.run_plan_record_file).expanduser().resolve()
                if args.run_plan_record_file
                else (logs_dir / "plan-agent-records.md").resolve()
            )
            append_plan_record_row(
                path=record_file,
                finished_at=finished_at,
                objective=objective,
                exit_code=exit_code,
                state_payload=state_payload,
                log_path=log_path,
            )
            log_event(
                "plan.recorded",
                mode=plan_mode,
                record_file=str(record_file),
                objective=objective[:700],
                exit_code=exit_code,
            )
            notify(
                "[daemon] plan mode=record-only\n"
                f"Recorded run summary to table: {record_file}",
                include_feishu=False,
            )
            clear_planner_state(reason="record_only")
            return

        should_schedule, skip_reason = should_schedule_plan_follow_up(
            exit_code=exit_code,
            state_payload=state_payload,
        )
        if not should_schedule:
            clear_planner_state(reason=skip_reason or "skip")
            log_event(
                "plan.skipped",
                mode=plan_mode,
                reason=skip_reason or "unknown",
                objective=objective[:700],
                exit_code=exit_code,
            )
            notify(
                "[daemon] plan mode=fully-plan\n"
                f"Skip auto-plan ({skip_reason or 'unknown'}). "
                "Please fix blockers and run again via /run or terminal.",
                include_feishu=False,
            )
            return

        scheduled_plan_context = {
            "objective": objective,
            "exit_code": exit_code,
            "log_path": str(log_path) if log_path else None,
            "state_payload": state_payload,
            "plan_report_path": str(plan_report_path) if plan_report_path else None,
        }
        scheduled_plan_request_at = finished_at + dt.timedelta(seconds=plan_request_delay_seconds)
        pending_plan_request = None
        pending_plan_auto_execute_at = None
        pending_plan_generated_at = None
        log_event(
            "plan.scheduled",
            mode=plan_mode,
            scheduled_request_at=scheduled_plan_request_at.isoformat() + "Z",
            objective=objective[:700],
            exit_code=exit_code,
        )
        notify(
            "[daemon] plan mode=fully-plan\n"
            f"Will generate next request in {plan_request_delay_seconds}s.",
            include_feishu=False,
        )

    def process_planner_timers() -> None:
        nonlocal pending_plan_request, pending_plan_auto_execute_at, pending_plan_generated_at
        nonlocal scheduled_plan_context, scheduled_plan_request_at
        if plan_mode != PLAN_MODE_FULLY_PLAN:
            return
        if child is not None and child.poll() is None:
            return
        now = dt.datetime.utcnow()

        if (
            pending_plan_request is not None
            and pending_plan_auto_execute_at is not None
            and now >= pending_plan_auto_execute_at
        ):
            request = pending_plan_request
            auto_at = pending_plan_auto_execute_at
            clear_planner_state(reason="auto_execute")
            log_event(
                "plan.auto_execute",
                request=request[:700],
                auto_execute_at=auto_at.isoformat() + "Z",
            )
            notify(
                "[daemon] auto executing planned request (no override received in time).\n"
                f"request={request[:700]}",
                include_feishu=False,
            )
            start_child(request)
            return

        if (
            scheduled_plan_context is not None
            and scheduled_plan_request_at is not None
            and now >= scheduled_plan_request_at
        ):
            request = build_plan_request(
                objective=str(scheduled_plan_context.get("objective") or "").strip(),
                exit_code=int(scheduled_plan_context.get("exit_code") or 0),
                state_payload=(
                    scheduled_plan_context.get("state_payload")
                    if isinstance(scheduled_plan_context.get("state_payload"), dict)
                    else None
                ),
                planner_report_path=(
                    Path(str(scheduled_plan_context.get("plan_report_path")))
                    if scheduled_plan_context.get("plan_report_path")
                    else None
                ),
            )
            pending_plan_request = request
            pending_plan_generated_at = now
            pending_plan_auto_execute_at = now + dt.timedelta(seconds=plan_auto_execute_delay_seconds)
            scheduled_plan_context = None
            scheduled_plan_request_at = None
            log_event(
                "plan.proposed",
                request=request[:700],
                auto_execute_at=pending_plan_auto_execute_at.isoformat() + "Z",
            )
            notify(
                "[daemon] planner request generated\n"
                f"request={request[:700]}\n"
                f"Auto execute in {plan_auto_execute_delay_seconds}s unless you override via /run or /inject.",
                include_feishu=False,
            )

    poller: TelegramCommandPoller | None = None
    feishu_poller: FeishuCommandPoller | None = None
    if telegram_enabled:
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
        notify(
            "[daemon] online\n"
            "Send /run <objective> to start a new run.\n"
            "Commands: /status /stop /fresh /help",
            include_feishu=False,
        )
        live_reporters.append(
            GenericStreamReporter(
                notifier=notifier,
                config=TelegramStreamReporterConfig(interval_seconds=30),
                on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
                error_label="telegram",
            )
        )
    else:
        print("[daemon] online (local control only)", file=sys.stdout)
    if feishu_enabled:
        feishu_poller = FeishuCommandPoller(
            app_id=args.feishu_app_id,
            app_secret=args.feishu_app_secret,
            chat_id=args.feishu_chat_id,
            on_command=on_feishu_command,
            on_error=lambda msg: print(f"[feishu] {msg}", file=sys.stderr),
            poll_interval_seconds=args.feishu_control_poll_interval_seconds,
            plain_text_kind="run",
        )
        feishu_poller.start()
        notify("[daemon] Feishu control enabled.", include_feishu=False)
        if feishu_notifier is not None:
            live_reporters.append(
                GenericStreamReporter(
                    notifier=feishu_notifier,
                    config=TelegramStreamReporterConfig(
                        interval_seconds=10,
                        max_chars=None,
                        max_item_chars=None,
                        compact_items=False,
                        header_template=None,
                    ),
                    on_error=lambda msg: print(f"[feishu] {msg}", file=sys.stderr),
                    error_label="feishu",
                    allowed_actors={"main"},
                )
            )
    for reporter in live_reporters:
        reporter.start()
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
                handle_command(
                    TelegramCommand(kind=item.kind, text=item.text),
                    "terminal",
                )
            if child is None:
                process_planner_timers()
                update_status()
                continue
            rc = child.poll()
            if rc is None:
                update_status()
                continue
            if child_log_follower is not None:
                child_log_follower.stop()
                child_log_follower = None
            notify(
                "[daemon] run finished\n"
                f"exit_code={rc}\n"
                f"objective={str(child_objective or '')[:700]}\n"
                f"log={child_log_path}",
                include_feishu=False,
            )
            state_payload = read_status(args.run_state_file) if args.run_state_file else None
            _, review_reason, _ = extract_latest_review(state_payload)
            external_result = format_external_run_result(
                exit_code=rc,
                objective=str(child_objective or ""),
                log_path=child_log_path,
                review_reason=review_reason,
            )
            if feishu_notifier is not None:
                time.sleep(2)
            if feishu_notifier is not None:
                feishu_notifier.send_message(external_result)
            log_event(
                "child.finished",
                exit_code=rc,
                objective=str(child_objective or "")[:700],
                log_path=str(child_log_path) if child_log_path else None,
                run_id=child_run_id,
            )
            if rc != 0 and log_contains_invalid_encrypted_content(child_log_path):
                set_force_fresh_session_marker(
                    args.run_state_file,
                    enabled=True,
                    reason="detected_invalid_encrypted_content",
                )
                warning = (
                    "[daemon][warning] detected 'invalid encrypted content' in child log. "
                    "Next run will start with a fresh session (no resume)."
                )
                notify(warning)
                print(warning, file=sys.stdout)
                log_event(
                    "session.fresh.flagged",
                    run_id=child_run_id,
                    reason="invalid_encrypted_content",
                    log_path=str(child_log_path) if child_log_path else None,
                )
                append_run_archive_record(
                    event="session.fresh.flagged",
                    run_id=child_run_id,
                    reason="invalid_encrypted_content",
                    log_path=str(child_log_path) if child_log_path else None,
                )
            if is_force_fresh_session_requested(args.run_state_file):
                fresh_session_id = resolve_saved_session_id_raw(args.run_state_file)
                if fresh_session_id:
                    set_force_fresh_session_marker(args.run_state_file, enabled=False)
                    log_event("session.fresh.cleared", run_id=child_run_id, session_id=fresh_session_id)
                    append_run_archive_record(
                        event="session.fresh.cleared",
                        run_id=child_run_id,
                        session_id=fresh_session_id,
                    )
            finished_session_id = resolve_resume_session_id(args.run_state_file, run_archive_log)
            append_run_archive_record(
                event="run.finished",
                run_id=child_run_id,
                objective=str(child_objective or "")[:700],
                plan_mode=plan_mode,
                exit_code=rc,
                log_path=str(child_log_path) if child_log_path else None,
                control_path=str(child_control_path) if child_control_path else None,
                operator_messages_file=str(operator_messages_path),
                resume_session_id=child_resume_session_id,
                session_id=finished_session_id,
                started_at=child_started_at.isoformat() + "Z" if child_started_at else None,
                finished_at=dt.datetime.utcnow().isoformat() + "Z",
            )
            schedule_plan_after_child_finish(
                objective=str(child_objective or ""),
                exit_code=rc,
                log_path=child_log_path,
                plan_report_path=child_plan_report_path,
            )
            pending_follow_up = resolve_plan_follow_up(
                state_file=args.run_state_file,
                report_path=child_plan_report_path,
                auto_execute_after_seconds=args.follow_up_auto_execute_seconds,
            ) if planner_mode_allows_follow_up(run_planner_mode) else None
            if pending_follow_up is not None:
                log_event(
                    "child.follow_up.ready",
                    plan_id=pending_follow_up.plan_id,
                    objective=pending_follow_up.objective[:700],
                )
                send_follow_up_prompt()
            child = None
            child_control_bus = None
            child_run_id = None
            child_control_path = None
            child_resume_session_id = None
            update_status()
    except KeyboardInterrupt:
        print("Daemon interrupted.", file=sys.stderr)
        log_event("daemon.interrupted")
    finally:
        if poller is not None:
            poller.stop()
        if feishu_poller is not None:
            feishu_poller.stop()
        if child is not None and child.poll() is None:
            child.terminate()
        if child_log_follower is not None:
            child_log_follower.stop()
        clear_planner_state(reason="daemon_stopped")
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
        for reporter in live_reporters:
            reporter.stop()
        if notifier is not None:
            notifier.close()
        if feishu_notifier is not None:
            feishu_notifier.close()


def build_child_command(
    *,
    args: argparse.Namespace,
    objective: str,
    chat_id: str,
    control_file: str,
    operator_messages_file: str,
    plan_report_file: str,
    plan_todo_file: str,
    resume_session_id: str | None,
) -> list[str]:
    planner_mode = resolve_planner_mode(planner_enabled_flag=args.run_planner, planner_mode=args.run_planner_mode)
    telegram_enabled = bool((args.telegram_bot_token or "").strip())
    preset = get_preset(args.run_model_preset) if args.run_model_preset else None
    main_model = preset.main_model if preset is not None else args.run_main_model
    main_reasoning_effort = preset.main_reasoning_effort if preset is not None else args.run_main_reasoning_effort
    reviewer_model = preset.reviewer_model if preset is not None else args.run_reviewer_model
    reviewer_reasoning_effort = (
        preset.reviewer_reasoning_effort if preset is not None else args.run_reviewer_reasoning_effort
    )
    planner_model = args.run_planner_model
    planner_reasoning_effort = args.run_planner_reasoning_effort
    cmd = resolve_autoloop_command(args.codex_autoloop_bin) + [
        "--max-rounds",
        str(args.run_max_rounds),
        "--control-file",
        control_file,
        "--operator-messages-file",
        operator_messages_file,
        "--plan-report-file",
        plan_report_file,
        "--plan-todo-file",
        plan_todo_file,
    ]
    if telegram_enabled:
        cmd.extend(
            [
                "--telegram-bot-token",
                args.telegram_bot_token,
                "--telegram-chat-id",
                chat_id,
                "--no-telegram-control",
                "--telegram-control-whisper-model",
                args.telegram_control_whisper_model,
                "--telegram-control-whisper-base-url",
                args.telegram_control_whisper_base_url,
                "--telegram-control-whisper-timeout-seconds",
                str(args.telegram_control_whisper_timeout_seconds),
            ]
        )
    if main_model:
        cmd.extend(["--main-model", main_model])
    if main_reasoning_effort:
        cmd.extend(["--main-reasoning-effort", main_reasoning_effort])
    if reviewer_model:
        cmd.extend(["--reviewer-model", reviewer_model])
    if reviewer_reasoning_effort:
        cmd.extend(["--reviewer-reasoning-effort", reviewer_reasoning_effort])
    if planner_model:
        cmd.extend(["--planner-model", planner_model])
    if planner_reasoning_effort:
        cmd.extend(["--planner-reasoning-effort", planner_reasoning_effort])
    cmd.extend(["--planner-mode", planner_mode])
    if planner_mode != "off":
        cmd.append("--planner")
    else:
        cmd.append("--no-planner")
    if telegram_enabled and args.telegram_control_whisper:
        cmd.append("--telegram-control-whisper")
    elif telegram_enabled:
        cmd.append("--no-telegram-control-whisper")
    if telegram_enabled and args.telegram_control_whisper_api_key:
        cmd.extend(["--telegram-control-whisper-api-key", args.telegram_control_whisper_api_key])
    if resume_session_id:
        cmd.extend(["--session-id", resume_session_id])
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
    cmd.extend(["--plan-update-interval-seconds", str(args.run_plan_update_interval_seconds)])
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
    last_session_id: str | None = None,
    force_fresh_session: bool = False,
    plan_mode: str = PLAN_MODE_FULLY_PLAN,
    pending_plan_request: str | None = None,
    pending_plan_auto_execute_at: dt.datetime | None = None,
    scheduled_plan_request_at: dt.datetime | None = None,
) -> str:
    if child is None or child.poll() is not None:
        base = f"[daemon] status=idle\nplan_mode={plan_mode}"
        if last_session_id:
            base += f"\nlast_session_id={last_session_id}"
        if force_fresh_session:
            base += "\nforce_fresh_session=true"
        if scheduled_plan_request_at is not None:
            base += f"\nplan_request_at={scheduled_plan_request_at.isoformat()}Z"
        if pending_plan_request:
            base += f"\npending_plan_request={pending_plan_request[:700]}"
        if pending_plan_auto_execute_at is not None:
            base += f"\nplan_auto_execute_at={pending_plan_auto_execute_at.isoformat()}Z"
        return base
    elapsed = "unknown"
    if child_started_at is not None:
        elapsed_seconds = int((dt.datetime.utcnow() - child_started_at).total_seconds())
        elapsed = f"{elapsed_seconds}s"
    return (
        "[daemon] status=running\n"
        f"plan_mode={plan_mode}\n"
        f"pid={child.pid}\n"
        f"elapsed={elapsed}\n"
        f"last_session_id={last_session_id}\n"
        f"force_fresh_session={str(force_fresh_session).lower()}\n"
        f"objective={str(child_objective or '')[:700]}\n"
        f"log={child_log_path}"
    )


def resolve_saved_session_id_raw(state_file: str | None) -> str | None:
    if not state_file:
        return None
    payload = read_status(state_file)
    if payload is None:
        return None
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def resolve_saved_session_id(state_file: str | None) -> str | None:
    if is_force_fresh_session_requested(state_file):
        return None
    return resolve_saved_session_id_raw(state_file)


def is_force_fresh_session_requested(state_file: str | None) -> bool:
    if not state_file:
        return False
    payload = read_status(state_file)
    if not isinstance(payload, dict):
        return False
    return payload.get(FORCE_FRESH_SESSION_KEY) is True


def set_force_fresh_session_marker(state_file: str | None, *, enabled: bool, reason: str | None = None) -> bool:
    if not state_file:
        return False
    state_path = Path(state_file).expanduser().resolve()
    payload = read_status(str(state_path))
    if not isinstance(payload, dict):
        payload = {}
    payload[FORCE_FRESH_SESSION_KEY] = bool(enabled)
    if enabled:
        payload["session_id"] = None
        payload["force_fresh_updated_at"] = dt.datetime.utcnow().isoformat() + "Z"
        if reason:
            payload[FORCE_FRESH_REASON_KEY] = reason
    else:
        payload.pop(FORCE_FRESH_REASON_KEY, None)
        payload.pop("force_fresh_updated_at", None)
    write_status(state_path, payload)
    return True


def resolve_last_session_id_from_archive(archive_file: str | Path | None) -> str | None:
    if archive_file is None:
        return None
    archive_path = Path(archive_file)
    if not archive_path.exists():
        return None
    try:
        lines = archive_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in reversed(lines):
        raw = line.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        session_id = payload.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            return session_id.strip()
        resume_session_id = payload.get("resume_session_id")
        if isinstance(resume_session_id, str) and resume_session_id.strip():
            return resume_session_id.strip()
    return None


def resolve_resume_session_id(state_file: str | None, archive_file: str | Path | None) -> str | None:
    if is_force_fresh_session_requested(state_file):
        return None
    from_state = resolve_saved_session_id(state_file)
    if from_state:
        return from_state
    return resolve_last_session_id_from_archive(archive_file)


def log_contains_invalid_encrypted_content(log_path: Path | None, *, tail_bytes: int = 256_000) -> bool:
    if log_path is None or not log_path.exists():
        return False
    try:
        with log_path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            start = max(0, size - max(1, int(tail_bytes)))
            f.seek(start)
            raw = f.read()
    except Exception:
        return False
    text = raw.decode("utf-8", errors="ignore").lower()
    return INVALID_ENCRYPTED_CONTENT_MARKER in text


def format_countdown(seconds: int) -> str:
    remaining = max(0, int(seconds))
    minutes, secs = divmod(remaining, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def resolve_plan_follow_up(
    *,
    state_file: str | None,
    report_path: Path | None,
    auto_execute_after_seconds: int,
) -> PlanFollowUp | None:
    # Keep daemon stable even when planner follow-up artifacts are unavailable.
    _ = state_file
    _ = report_path
    _ = auto_execute_after_seconds
    return None


def create_git_checkpoint(
    *,
    run_cwd: Path,
    plan_id: str,
    auto_triggered: bool,
) -> GitCheckpointResult:
    _ = run_cwd
    _ = plan_id
    _ = auto_triggered
    return GitCheckpointResult(ok_to_continue=True, message="", commit_hash=None)


def build_modified_follow_up_objective(*, base_objective: str, user_text: str) -> str:
    base = (base_objective or "").strip()
    extra = (user_text or "").strip()
    if not base:
        return extra
    if not extra:
        return base
    return (
        f"{base}\n\n"
        "User modifications:\n"
        f"{extra}"
    )


def normalize_plan_mode(raw: str | None) -> str:
    value = (raw or PLAN_MODE_FULLY_PLAN).strip().lower()
    return value if value in PLAN_MODES else PLAN_MODE_FULLY_PLAN


def should_schedule_plan_follow_up(*, exit_code: int, state_payload: dict[str, Any] | None) -> tuple[bool, str | None]:
    if exit_code != 0:
        return False, "last_run_failed"
    review_status = extract_latest_review_status(state_payload)
    if review_status == "blocked":
        return False, "review_blocked"
    return True, None


def extract_latest_review_status(state_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(state_payload, dict):
        return None
    raw = state_payload.get("latest_review_status")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    status, _, _ = extract_latest_review(state_payload)
    if not status:
        return None
    return status.strip().lower()


def build_plan_request(
    *,
    objective: str,
    exit_code: int,
    state_payload: dict[str, Any] | None,
    planner_report_path: Path | None = None,
) -> str:
    objective_text = sanitize_follow_up_objective(objective)
    if not objective_text:
        objective_text = "Continue improving the current repository objective."

    review_status, review_reason, review_next_action = extract_latest_review(state_payload)
    planner_next_objective = extract_suggested_next_objective_from_plan_report(planner_report_path)

    # Priority: reviewer next_action > planner report objective > objective fallback.
    if review_next_action:
        return f"{review_next_action.strip()}（目标上下文：{objective_text}）".strip()
    if planner_next_objective:
        return planner_next_objective

    parts = [f"继续推进目标：{objective_text}"]
    if exit_code != 0:
        parts.append("先定位并修复上一轮失败原因。")
    if review_reason:
        parts.append(f"优先关注：{review_reason}")
    if review_status:
        parts.append(f"当前审核状态：{review_status}")
    if not review_reason:
        parts.append("补齐剩余实现并运行关键验证命令后再继续。")
    return " ".join(parts).strip()


def sanitize_follow_up_objective(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    while True:
        lowered = value.lower()
        if lowered.startswith("/run "):
            value = value[5:].strip()
            continue
        if lowered.startswith("run /run "):
            value = value[9:].strip()
            continue
        if lowered.startswith("run "):
            value = value[4:].strip()
            continue
        break
    return value


def extract_suggested_next_objective_from_plan_report(report_path: Path | None) -> str | None:
    if report_path is None:
        return None
    try:
        text = report_path.read_text(encoding="utf-8")
    except Exception:
        return None
    return extract_suggested_next_objective_from_markdown(text)


def extract_suggested_next_objective_from_markdown(markdown_text: str) -> str | None:
    marker = "## Suggested Next Objective"
    if marker not in markdown_text:
        return None
    section = markdown_text.split(marker, 1)[1]
    lines: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            break
        lines.append(line)
    if not lines:
        return None
    candidate = " ".join(lines).strip()
    if not candidate:
        return None
    if candidate.lower() == "no follow-up objective proposed yet.":
        return None
    return candidate[:2000]


def extract_latest_review(state_payload: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    if not isinstance(state_payload, dict):
        return None, None, None
    rounds = state_payload.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        return None, None, None
    last_item = rounds[-1]
    if not isinstance(last_item, dict):
        return None, None, None
    review = last_item.get("review")
    if isinstance(review, dict):
        status = review.get("status")
        reason = review.get("reason")
        next_action = review.get("next_action")
    else:
        status = last_item.get("review_status")
        reason = last_item.get("review_reason")
        next_action = last_item.get("review_next_action")
    return (
        str(status).strip() if status else None,
        str(reason).strip() if reason else None,
        str(next_action).strip() if next_action else None,
    )


def append_plan_record_row(
    *,
    path: Path,
    finished_at: dt.datetime,
    objective: str,
    exit_code: int,
    state_payload: dict[str, Any] | None,
    log_path: Path | None,
) -> None:
    status, reason, next_action = extract_latest_review(state_payload)
    session_id = None
    if isinstance(state_payload, dict):
        session_id_raw = state_payload.get("session_id")
        if isinstance(session_id_raw, str) and session_id_raw.strip():
            session_id = session_id_raw.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        header = (
            "| finished_at | objective | exit_code | review_status | review_next_action | session_id | log |\n"
            "|---|---|---:|---|---|---|---|\n"
        )
        path.write_text(header, encoding="utf-8")
    row = (
        f"| {_table_cell(finished_at.isoformat() + 'Z')} "
        f"| {_table_cell(objective[:700])} "
        f"| {exit_code} "
        f"| {_table_cell(status or '')} "
        f"| {_table_cell((next_action or reason or '')[:700])} "
        f"| {_table_cell(session_id or '')} "
        f"| {_table_cell(str(log_path) if log_path else '')} |\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(row)


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def help_text() -> str:
    return (
        "[daemon] commands\n"
        "/run <objective> - start a new codex-autoloop run\n"
        "/inject <instruction> - inject instruction to active run (or run if idle)\n"
        "/status - daemon + child status\n"
        "/stop - stop active run\n"
        "/fresh - force next run to use a fresh session (ignore saved session_id)\n"
        "/daemon-stop - stop daemon process\n"
        "/help - show this help\n"
        "Terminal plain text is treated as /run when idle.\n"
        "When Telegram is enabled, plain text messages are also treated as /run when idle.\n"
        "Voice/audio message will be transcribed by Whisper when Telegram is enabled.\n"
        "In fully-plan mode, daemon may auto-propose and auto-run next request unless overridden."
    )


def format_external_message(message: str) -> str:
    text = (message or "").strip()
    if text.startswith("[daemon] "):
        return text[len("[daemon] ") :].strip()
    if text.startswith("[daemon]\n"):
        return text[len("[daemon]\n") :].strip()
    return text


def format_external_run_result(
    *,
    exit_code: int,
    objective: str,
    log_path: Path | None,
    review_reason: str | None = None,
) -> str:
    if exit_code == 0:
        return "successful"
    lines = ["fail"]
    if review_reason and review_reason.strip():
        lines.append(f"reason={review_reason.strip()[:500]}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    preset_names = ", ".join(p.name for p in MODEL_PRESETS)
    parser = argparse.ArgumentParser(
        prog="codex-autoloop-telegram-daemon",
        description="Keep a local control daemon online and launch codex-autoloop runs on demand.",
    )
    parser.add_argument("--telegram-bot-token", default=None, help="Optional Telegram bot token.")
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
    parser.add_argument("--feishu-app-id", default=None, help="Optional Feishu app id.")
    parser.add_argument("--feishu-app-secret", default=None, help="Optional Feishu app secret.")
    parser.add_argument("--feishu-chat-id", default=None, help="Feishu chat id.")
    parser.add_argument(
        "--feishu-receive-id-type",
        default="chat_id",
        help="Feishu receive_id_type used for outgoing messages.",
    )
    parser.add_argument(
        "--feishu-timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout for Feishu API calls.",
    )
    parser.add_argument(
        "--feishu-control-poll-interval-seconds",
        type=int,
        default=2,
        help="Polling interval for Feishu control command loop.",
    )
    parser.add_argument(
        "--codex-autoloop-bin",
        default=DEFAULT_CODEX_AUTOLOOP_CMD,
        help=(
            "Executable or command used to launch child runs. "
            "Supports full commands like 'python -m codex_autoloop.cli'."
        ),
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
        "--follow-up-auto-execute-seconds",
        type=int,
        default=600,
        help="Seconds to wait before automatically executing the planner's proposed next session.",
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
    parser.add_argument("--run-max-rounds", type=int, default=500, help="Child codex-autoloop max rounds.")
    parser.add_argument(
        "--run-model-preset",
        default=None,
        help=(
            "Optional model preset name for child runs. "
            f"If unset, child inherits Codex default model settings (available presets: {preset_names})."
        ),
    )
    parser.add_argument(
        "--run-main-model",
        default=None,
        help="Explicit main agent model override for child runs.",
    )
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
    parser.add_argument(
        "--run-planner-mode",
        default=PLANNER_MODE_AUTO,
        choices=PLANNER_MODE_CHOICES,
        help="Planner mode for child runs: off, auto, or record.",
    )
    parser.add_argument(
        "--run-planner-model",
        default=None,
        help="Explicit planner agent model override for child runs.",
    )
    parser.add_argument(
        "--run-planner-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Explicit planner agent reasoning effort override for child runs.",
    )
    parser.add_argument(
        "--run-planner",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable planner manager sub-agent for child runs.",
    )
    parser.add_argument(
        "--run-plan-update-interval-seconds",
        type=int,
        default=1800,
        help="Child planner sweep interval in seconds.",
    )
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
        default=3600,
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
        "--run-resume-last-session",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from last saved session_id when daemon starts a new idle run.",
    )
    parser.add_argument(
        "--run-plan-mode",
        default=PLAN_MODE_FULLY_PLAN,
        choices=sorted(PLAN_MODES),
        help="Plan mode: execute-only, fully-plan (default), or record-only.",
    )
    parser.add_argument(
        "--run-plan-request-delay-seconds",
        type=int,
        default=600,
        help="In fully-plan mode, delay before generating next planner request after child completion.",
    )
    parser.add_argument(
        "--run-plan-auto-execute-delay-seconds",
        type=int,
        default=600,
        help="In fully-plan mode, auto-execute planner request after this delay unless user overrides it.",
    )
    parser.add_argument(
        "--run-plan-record-file",
        default=None,
        help="Optional markdown table file path used by record-only mode. Defaults to logs_dir/plan-agent-records.md.",
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

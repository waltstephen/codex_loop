from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ..adapters.control_channels import LocalBusControlChannel, TelegramControlChannel
from ..daemon_bus import BusCommand, JsonlCommandBus, read_status, write_status
from ..model_catalog import get_preset
from ..telegram_notifier import TelegramConfig, TelegramNotifier, resolve_chat_id
from ..token_lock import TokenLock, acquire_token_lock


class TelegramDaemonApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.chat_id = ""
        self.run_cwd = Path(args.run_cd).resolve()
        self.logs_dir = Path(args.logs_dir).resolve()
        self.bus_dir = Path(args.bus_dir).resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.bus_dir.mkdir(parents=True, exist_ok=True)
        self.events_log = self.logs_dir / "daemon-events.jsonl"
        self.status_path = self.bus_dir / "daemon_status.json"

        self.token_lock: TokenLock | None = None
        self.notifier: TelegramNotifier | None = None
        self.control_channels: list[object] = []
        self.child: subprocess.Popen[str] | None = None
        self.child_objective: str | None = None
        self.child_log_path: Path | None = None
        self.child_plan_overview_path: Path | None = None
        self.child_review_summaries_dir: Path | None = None
        self.child_started_at: dt.datetime | None = None
        self.child_control_bus: JsonlCommandBus | None = None
        self._stopping = False

    def run(self) -> None:
        self.chat_id = self._resolve_chat_id()
        self.token_lock = self._acquire_token_lock()
        self.notifier = TelegramNotifier(
            TelegramConfig(
                bot_token=self.args.telegram_bot_token,
                chat_id=self.chat_id,
                events=set(),
                typing_enabled=False,
            ),
            on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        )
        self.control_channels = self._build_control_channels()
        for channel in self.control_channels:
            channel.start(self._on_command)

        self.notifier.send_message(
            "[daemon] online\n"
            "Send /run <objective> to start a new run.\n"
            "Commands: /status /mode /plan /review /show-plan /show-review /stop /help"
        )
        self._log_event(
            "daemon.started",
            run_cwd=str(self.run_cwd),
            logs_dir=str(self.logs_dir),
            bus_dir=str(self.bus_dir),
            token_hash=(self.token_lock.token_hash if self.token_lock else None),
        )
        self._write_status()

        try:
            while not self._stopping:
                time.sleep(1)
                self._check_child()
                self._write_status()
        except KeyboardInterrupt:
            print("Daemon interrupted.", file=sys.stderr)
            self._log_event("daemon.interrupted")
        finally:
            self._shutdown()

    def _resolve_chat_id(self) -> str:
        chat_id = (self.args.telegram_chat_id or "").strip()
        if chat_id.lower() not in {"", "auto", "none", "null"}:
            return chat_id
        print("Resolving chat_id from updates. Send /start or a message to your bot now...", file=sys.stderr)
        resolved = resolve_chat_id(
            bot_token=self.args.telegram_bot_token,
            timeout_seconds=self.args.telegram_chat_id_resolve_timeout_seconds,
            poll_interval_seconds=2,
            on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
        )
        if not resolved:
            raise ValueError("Unable to resolve chat_id automatically.")
        print(f"Resolved chat_id={resolved}", file=sys.stderr)
        return resolved

    def _acquire_token_lock(self) -> TokenLock:
        return acquire_token_lock(
            token=self.args.telegram_bot_token,
            owner_info={
                "pid": os.getpid(),
                "chat_id": self.chat_id,
                "run_cwd": str(self.run_cwd),
                "bus_dir": str(self.bus_dir),
                "started_at": dt.datetime.utcnow().isoformat() + "Z",
            },
            lock_dir=self.args.token_lock_dir,
        )

    def _build_control_channels(self) -> list[object]:
        return [
            LocalBusControlChannel(
                path=str(self.bus_dir / "daemon_commands.jsonl"),
                source="terminal",
                on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
            ),
            TelegramControlChannel(
                bot_token=self.args.telegram_bot_token,
                chat_id=self.chat_id,
                on_error=lambda msg: print(f"[daemon] {msg}", file=sys.stderr),
                poll_interval_seconds=self.args.poll_interval_seconds,
                long_poll_timeout_seconds=self.args.long_poll_timeout_seconds,
                plain_text_as_inject=True,
                whisper_enabled=self.args.telegram_control_whisper,
                whisper_api_key=self.args.telegram_control_whisper_api_key,
                whisper_model=self.args.telegram_control_whisper_model,
                whisper_base_url=self.args.telegram_control_whisper_base_url,
                whisper_timeout_seconds=self.args.telegram_control_whisper_timeout_seconds,
            ),
        ]

    def _on_command(self, command) -> None:
        self._log_event("command.received", source=command.source, kind=command.kind, text=command.text[:700])
        if command.kind == "help":
            self._send_reply(command.source, help_text())
            return
        if command.kind == "mode":
            updated_mode = _normalize_plan_mode(command.text)
            if updated_mode is None:
                self._send_reply(command.source, "[daemon] invalid mode. Use: off, auto, or record.")
                return
            self.args.run_plan_mode = updated_mode
            self._log_event("daemon.mode.updated", source=command.source, plan_mode=updated_mode)
            if self._child_running():
                if self._forward_to_child("mode", updated_mode, command.source):
                    self._send_reply(
                        command.source,
                        f"[daemon] plan mode updated to {updated_mode} for future runs and forwarded to active run.",
                    )
                else:
                    self._send_reply(
                        command.source,
                        f"[daemon] plan mode updated to {updated_mode} for future runs, but active child bus is unavailable.",
                    )
            else:
                self._send_reply(command.source, f"[daemon] default plan mode updated to {updated_mode}.")
            self._write_status()
            return
        if command.kind == "status":
            self._send_reply(
                command.source,
                format_status(
                    child=self.child,
                    child_objective=self.child_objective,
                    child_log_path=self.child_log_path,
                    child_plan_overview_path=self.child_plan_overview_path,
                    child_review_summaries_dir=self.child_review_summaries_dir,
                    child_started_at=self.child_started_at,
                    default_plan_mode=getattr(self.args, "run_plan_mode", "auto"),
                    last_session_id=resolve_saved_session_id(self.args.run_state_file),
                ),
            )
            return
        if command.kind == "show-plan":
            doc = _read_text_file(self.child_plan_overview_path)
            self._send_reply(command.source, doc or "[daemon] no plan overview markdown available.")
            return
        if command.kind == "show-review":
            target = self.child_review_summaries_dir / "index.md" if self.child_review_summaries_dir else None
            if command.text.strip():
                if self.child_review_summaries_dir is None:
                    self._send_reply(command.source, "[daemon] no reviewer summary markdown available.")
                    return
                try:
                    round_index = int(command.text.strip())
                except ValueError:
                    self._send_reply(command.source, "[daemon] invalid round number for show-review.")
                    return
                target = self.child_review_summaries_dir / f"round-{round_index:03d}.md"
            doc = _read_text_file(target)
            self._send_reply(command.source, doc or "[daemon] no reviewer summary markdown available.")
            return
        if command.kind in {"run", "inject"}:
            objective = command.text.strip()
            if not objective:
                self._send_reply(command.source, "[daemon] missing objective. Use /run <objective>.")
                return
            if self._child_running():
                if self._forward_to_child("inject", objective, command.source):
                    self._send_reply(
                        command.source,
                        "[daemon] inject forwarded to active run. "
                        "Child loop will interrupt and apply your new instruction.",
                    )
                else:
                    self._send_reply(command.source, "[daemon] active run exists but child control bus unavailable.")
                return
            self._start_child(objective)
            return
        if command.kind in {"plan", "review"}:
            if not self._child_running():
                self._send_reply(command.source, "[daemon] no active run for targeted plan/review command.")
                return
            if self._forward_to_child(command.kind, command.text.strip(), command.source):
                self._send_reply(command.source, f"[daemon] {command.kind} forwarded to active run.")
            else:
                self._send_reply(command.source, "[daemon] active run exists but child control bus unavailable.")
            return
        if command.kind == "stop":
            if not self._child_running():
                self._send_reply(command.source, "[daemon] no active run.")
                return
            if self._forward_to_child("stop", "", command.source):
                self._send_reply(command.source, "[daemon] stop forwarded to active run.")
            else:
                assert self.child is not None
                self.child.terminate()
                self._send_reply(command.source, "[daemon] stop signal sent to active run.")
            return
        if command.kind == "daemon-stop":
            self._send_reply(command.source, "[daemon] stopping daemon.")
            self._stopping = True

    def _start_child(self, objective: str) -> None:
        assert self.notifier is not None
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        log_path = self.logs_dir / f"run-{timestamp}.log"
        control_path = self.bus_dir / f"child-control-{timestamp}.jsonl"
        messages_path = self.logs_dir / f"run-{timestamp}-operator_messages.md"
        plan_overview_path = self.logs_dir / f"run-{timestamp}-plan_overview.md"
        review_summaries_dir = self.logs_dir / f"run-{timestamp}-review"
        resume_session_id = resolve_saved_session_id(self.args.run_state_file) if self.args.run_resume_last_session else None
        self.child_control_bus = JsonlCommandBus(control_path)
        cmd = build_child_command(
            args=self.args,
            objective=objective,
            chat_id=self.chat_id,
            control_file=str(control_path),
            operator_messages_file=str(messages_path),
            plan_overview_file=str(plan_overview_path),
            review_summaries_dir=str(review_summaries_dir),
            resume_session_id=resume_session_id,
        )
        log_file = log_path.open("w", encoding="utf-8")
        self.child = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, text=True, cwd=self.run_cwd)
        self.child_objective = objective
        self.child_log_path = log_path
        self.child_plan_overview_path = plan_overview_path
        self.child_review_summaries_dir = review_summaries_dir
        self.child_started_at = dt.datetime.utcnow()
        self.notifier.send_message(
            "[daemon] launched run\n"
            f"pid={self.child.pid}\n"
            f"objective={objective[:700]}\n"
            f"log={log_path}"
        )
        self._log_event(
            "child.launched",
            pid=self.child.pid,
            objective=objective[:700],
            log_path=str(log_path),
            control_path=str(control_path),
            operator_messages_file=str(messages_path),
            plan_overview_file=str(plan_overview_path),
            review_summaries_dir=str(review_summaries_dir),
            resume_session_id=resume_session_id,
        )
        self._write_status()

    def _send_reply(self, source: str, message: str) -> None:
        if source == "telegram":
            assert self.notifier is not None
            self.notifier.send_message(message)
        else:
            print(message, file=sys.stdout)
        self._log_event("reply.sent", source=source, message=message[:700])

    def _forward_to_child(self, kind: str, text: str, source: str) -> bool:
        if not self._child_running() or self.child_control_bus is None:
            return False
        self.child_control_bus.publish(BusCommand(kind=kind, text=text, source=source, ts=time.time()))
        self._log_event("child.command.forwarded", source=source, kind=kind, text=text[:700])
        return True

    def _child_running(self) -> bool:
        return self.child is not None and self.child.poll() is None

    def _check_child(self) -> None:
        if self.child is None:
            return
        rc = self.child.poll()
        if rc is None:
            return
        assert self.notifier is not None
        self.notifier.send_message(
            "[daemon] run finished\n"
            f"exit_code={rc}\n"
            f"objective={str(self.child_objective or '')[:700]}\n"
            f"log={self.child_log_path}"
        )
        self._log_event(
            "child.finished",
            exit_code=rc,
            objective=str(self.child_objective or "")[:700],
            log_path=str(self.child_log_path) if self.child_log_path else None,
        )
        self.child = None
        self.child_control_bus = None

    def _write_status(self) -> None:
        running = self._child_running()
        write_status(
            self.status_path,
            {
                "updated_at": dt.datetime.utcnow().isoformat() + "Z",
                "daemon_running": not self._stopping,
                "running": running,
                "default_plan_mode": getattr(self.args, "run_plan_mode", "auto"),
                "child_pid": self.child.pid if running and self.child else None,
                "child_objective": self.child_objective,
                "child_log_path": str(self.child_log_path) if self.child_log_path else None,
                "child_plan_overview_path": str(self.child_plan_overview_path) if self.child_plan_overview_path else None,
                "child_review_summaries_dir": (
                    str(self.child_review_summaries_dir) if self.child_review_summaries_dir else None
                ),
                "child_started_at": self.child_started_at.isoformat() + "Z" if self.child_started_at else None,
                "last_session_id": resolve_saved_session_id(self.args.run_state_file),
                "run_cwd": str(self.run_cwd),
                "logs_dir": str(self.logs_dir),
                "bus_dir": str(self.bus_dir),
                "events_log": str(self.events_log),
            },
        )

    def _log_event(self, event_type: str, **kwargs) -> None:
        payload = {
            "ts": dt.datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            **kwargs,
        }
        with self.events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _shutdown(self) -> None:
        for channel in reversed(self.control_channels):
            channel.stop()
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
        write_status(
            self.status_path,
            {
                "updated_at": dt.datetime.utcnow().isoformat() + "Z",
                "daemon_running": False,
                "running": False,
            },
        )
        self._log_event("daemon.stopped")
        if self.token_lock is not None:
            self.token_lock.release()
        if self.notifier is not None:
            self.notifier.close()


def run_telegram_daemon(args: argparse.Namespace) -> None:
    TelegramDaemonApp(args).run()


def build_child_command(
    *,
    args: argparse.Namespace,
    objective: str,
    chat_id: str,
    control_file: str,
    operator_messages_file: str,
    plan_overview_file: str,
    review_summaries_dir: str,
    resume_session_id: str | None,
) -> list[str]:
    preset = get_preset(args.run_model_preset) if args.run_model_preset else None
    main_model = preset.main_model if preset is not None else args.run_main_model
    main_reasoning_effort = preset.main_reasoning_effort if preset is not None else args.run_main_reasoning_effort
    reviewer_model = preset.reviewer_model if preset is not None else args.run_reviewer_model
    reviewer_reasoning_effort = (
        preset.reviewer_reasoning_effort if preset is not None else args.run_reviewer_reasoning_effort
    )
    plan_model = preset.plan_model if preset is not None else getattr(args, "run_plan_model", None)
    plan_reasoning_effort = (
        preset.plan_reasoning_effort
        if preset is not None
        else getattr(args, "run_plan_reasoning_effort", None)
    )
    plan_mode = getattr(args, "run_plan_mode", "auto")
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
        "--plan-overview-file",
        plan_overview_file,
        "--review-summaries-dir",
        review_summaries_dir,
        "--plan-mode",
        plan_mode,
        "--telegram-control-whisper-model",
        args.telegram_control_whisper_model,
        "--telegram-control-whisper-base-url",
        args.telegram_control_whisper_base_url,
        "--telegram-control-whisper-timeout-seconds",
        str(args.telegram_control_whisper_timeout_seconds),
    ]
    if main_model:
        cmd.extend(["--main-model", main_model])
    if main_reasoning_effort:
        cmd.extend(["--main-reasoning-effort", main_reasoning_effort])
    if reviewer_model:
        cmd.extend(["--reviewer-model", reviewer_model])
    if reviewer_reasoning_effort:
        cmd.extend(["--reviewer-reasoning-effort", reviewer_reasoning_effort])
    if plan_model:
        cmd.extend(["--plan-model", plan_model])
    if plan_reasoning_effort:
        cmd.extend(["--plan-reasoning-effort", plan_reasoning_effort])
    if args.telegram_control_whisper:
        cmd.append("--telegram-control-whisper")
    else:
        cmd.append("--no-telegram-control-whisper")
    if args.telegram_control_whisper_api_key:
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
    child_plan_overview_path: Path | None,
    child_review_summaries_dir: Path | None,
    child_started_at: dt.datetime | None,
    default_plan_mode: str,
    last_session_id: str | None = None,
) -> str:
    if child is None or child.poll() is not None:
        base = "[daemon] status=idle"
        if last_session_id:
            base += f"\nlast_session_id={last_session_id}"
        base += f"\ndefault_plan_mode={default_plan_mode}"
        if child_plan_overview_path:
            base += f"\nplan_overview={child_plan_overview_path}"
        if child_review_summaries_dir:
            base += f"\nreview_summaries_dir={child_review_summaries_dir}"
        return base
    elapsed = "unknown"
    if child_started_at is not None:
        elapsed_seconds = int((dt.datetime.utcnow() - child_started_at).total_seconds())
        elapsed = f"{elapsed_seconds}s"
    return (
        "[daemon] status=running\n"
        f"pid={child.pid}\n"
        f"elapsed={elapsed}\n"
        f"default_plan_mode={default_plan_mode}\n"
        f"last_session_id={last_session_id}\n"
        f"objective={str(child_objective or '')[:700]}\n"
        f"log={child_log_path}\n"
        f"plan_overview={child_plan_overview_path}\n"
        f"review_summaries_dir={child_review_summaries_dir}"
    )


def resolve_saved_session_id(state_file: str | None) -> str | None:
    if not state_file:
        return None
    payload = read_status(state_file)
    if payload is None:
        return None
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def help_text() -> str:
    return (
        "[daemon] commands\n"
        "/run <objective> - start a new codex-autoloop run\n"
        "/inject <instruction> - inject instruction to active run (or run if idle)\n"
        "/mode <off|auto|record> - hot-switch daemon default mode and active child mode\n"
        "/plan <direction> - send direction to the active plan agent only\n"
        "/review <criteria> - send audit criteria to the active reviewer only\n"
        "/show-plan - print the latest plan overview markdown\n"
        "/show-review [round] - print reviewer summary markdown\n"
        "/status - daemon + child status\n"
        "/stop - stop active run\n"
        "/daemon-stop - stop daemon process\n"
        "/help - show this help\n"
        "Plain text message is treated as /run when idle.\n"
        "Voice/audio message will be transcribed by Whisper when enabled."
    )


def _normalize_plan_mode(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"off", "auto", "record"}:
        return normalized
    return None


def _read_text_file(path: str | Path | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None

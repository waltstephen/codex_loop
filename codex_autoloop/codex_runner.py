from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, Literal

from .models import CodexRunResult


EventCallback = Callable[[str, str], None]
InactivityDecision = Literal["continue", "restart"]


@dataclass
class InactivitySnapshot:
    idle_seconds: float
    command: list[str]
    thread_id: str | None
    last_agent_message: str
    stdout_tail: list[str]
    stderr_tail: list[str]
    run_label: str | None = None


InactivityCallback = Callable[[InactivitySnapshot], InactivityDecision]
ExternalInterruptProvider = Callable[[], str | None]


@dataclass
class RunnerOptions:
    model: str | None = None
    dangerous_yolo: bool = False
    full_auto: bool = False
    skip_git_repo_check: bool = False
    extra_args: list[str] | None = None
    output_schema_path: str | None = None
    watchdog_soft_idle_seconds: int | None = None
    watchdog_hard_idle_seconds: int | None = None
    inactivity_callback: InactivityCallback | None = None
    external_interrupt_reason_provider: ExternalInterruptProvider | None = None


class CodexRunner:
    def __init__(self, codex_bin: str = "codex", event_callback: EventCallback | None = None) -> None:
        self.codex_bin = codex_bin
        self.event_callback = event_callback

    def run_exec(
        self,
        *,
        prompt: str,
        resume_thread_id: str | None,
        options: RunnerOptions,
        run_label: str | None = None,
    ) -> CodexRunResult:
        command = self._build_command(prompt=prompt, resume_thread_id=resume_thread_id, options=options)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        events: list[dict] = []
        agent_messages: list[str] = []
        thread_id: str | None = resume_thread_id
        turn_completed = False
        turn_failed = False
        fatal_error: str | None = None

        line_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        soft_idle = options.watchdog_soft_idle_seconds or 0
        hard_idle = options.watchdog_hard_idle_seconds or 0
        last_activity_at = time.monotonic()
        last_soft_check_at = last_activity_at
        stdout_closed = False
        stderr_closed = False
        watchdog_terminated = False
        watchdog_reason: str | None = None

        def consume_pipe(stream_name: str, pipe) -> None:
            assert pipe is not None
            for line in pipe:
                line_queue.put((stream_name, line.rstrip("\n")))
            line_queue.put((stream_name, None))

        stdout_thread = threading.Thread(
            target=consume_pipe,
            args=("stdout", process.stdout),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=consume_pipe,
            args=("stderr", process.stderr),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        while True:
            if process.poll() is not None and stdout_closed and stderr_closed:
                break
            try:
                stream_name, text = line_queue.get(timeout=1.0)
            except queue.Empty:
                now = time.monotonic()
                idle_seconds = now - last_activity_at

                if process.poll() is None and options.external_interrupt_reason_provider is not None:
                    interrupt_reason = options.external_interrupt_reason_provider()
                    if interrupt_reason:
                        watchdog_reason = f"External interrupt: {interrupt_reason}"
                        self._emit(
                            self._stream_name("stderr", run_label),
                            f"[watchdog] {watchdog_reason}",
                        )
                        self._terminate_process(process)
                        watchdog_terminated = True

                if (
                    soft_idle > 0
                    and options.inactivity_callback is not None
                    and process.poll() is None
                    and idle_seconds >= soft_idle
                    and (now - last_soft_check_at) >= soft_idle
                ):
                    last_soft_check_at = now
                    snapshot = InactivitySnapshot(
                        idle_seconds=idle_seconds,
                        command=command,
                        thread_id=thread_id,
                        last_agent_message=agent_messages[-1] if agent_messages else "",
                        stdout_tail=stdout_lines[-50:],
                        stderr_tail=stderr_lines[-50:],
                        run_label=run_label,
                    )
                    decision = options.inactivity_callback(snapshot)
                    if decision == "restart":
                        watchdog_reason = (
                            f"Restart requested by stall sub-agent after {int(idle_seconds)}s idle."
                        )
                        self._emit(
                            self._stream_name("stderr", run_label),
                            f"[watchdog] {watchdog_reason}",
                        )
                        self._terminate_process(process)
                        watchdog_terminated = True

                if (
                    hard_idle > 0
                    and process.poll() is None
                    and idle_seconds >= hard_idle
                ):
                    watchdog_reason = (
                        f"Forced restart after hard idle timeout ({int(idle_seconds)}s)."
                    )
                    self._emit(
                        self._stream_name("stderr", run_label),
                        f"[watchdog] {watchdog_reason}",
                    )
                    self._terminate_process(process)
                    watchdog_terminated = True
                continue

            if text is None:
                if stream_name == "stdout":
                    stdout_closed = True
                else:
                    stderr_closed = True
                continue

            last_activity_at = time.monotonic()
            output_stream = self._stream_name(stream_name, run_label)
            self._emit(output_stream, text)

            if stream_name == "stdout":
                stdout_lines.append(text)
                event = self._parse_json_line(text)
                if event is None:
                    continue
                events.append(event)
                event_type = event.get("type")
                if event_type == "thread.started":
                    thread_id = event.get("thread_id", thread_id)
                elif event_type == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        message = item.get("text", "")
                        if isinstance(message, str):
                            agent_messages.append(message)
                elif event_type == "turn.completed":
                    turn_completed = True
                elif event_type == "turn.failed":
                    turn_failed = True
                    err = event.get("error", {})
                    if isinstance(err, dict):
                        maybe_msg = err.get("message")
                        if isinstance(maybe_msg, str):
                            fatal_error = maybe_msg
                elif event_type == "error" and fatal_error is None:
                    maybe_msg = event.get("message")
                    if isinstance(maybe_msg, str):
                        fatal_error = maybe_msg
            else:
                stderr_lines.append(text)

        if process.poll() is None:
            process.wait(timeout=10.0)

        stdout_thread.join(timeout=2.0)
        stderr_thread.join(timeout=2.0)

        if watchdog_terminated:
            turn_failed = True
            if watchdog_reason and fatal_error is None:
                fatal_error = watchdog_reason
        elif turn_completed and not turn_failed:
            fatal_error = None

        return CodexRunResult(
            command=command,
            exit_code=process.returncode,
            thread_id=thread_id,
            agent_messages=agent_messages,
            json_events=events,
            stdout_lines=stdout_lines,
            stderr_lines=stderr_lines,
            turn_completed=turn_completed,
            turn_failed=turn_failed,
            fatal_error=fatal_error,
        )

    def _build_command(self, *, prompt: str, resume_thread_id: str | None, options: RunnerOptions) -> list[str]:
        command = [self.codex_bin, "exec"]
        if resume_thread_id:
            command.append("resume")
        command.append("--json")
        if options.model:
            command.extend(["-m", options.model])
        if options.dangerous_yolo:
            command.append("--dangerously-bypass-approvals-and-sandbox")
        elif options.full_auto:
            command.append("--full-auto")
        if options.skip_git_repo_check:
            command.append("--skip-git-repo-check")
        if options.output_schema_path and not resume_thread_id:
            command.extend(["--output-schema", options.output_schema_path])
        if options.extra_args:
            command.extend(options.extra_args)
        if resume_thread_id:
            command.append(resume_thread_id)
        command.append(prompt)
        return command

    @staticmethod
    def _parse_json_line(line: str) -> dict | None:
        stripped = line.strip()
        if not stripped.startswith("{"):
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _emit(self, stream: str, line: str) -> None:
        if self.event_callback is None:
            return
        self.event_callback(stream, line)

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5.0)

    @staticmethod
    def _stream_name(stream: str, run_label: str | None) -> str:
        if not run_label:
            return stream
        return f"{run_label}.{stream}"

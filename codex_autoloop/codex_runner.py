from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable

from .models import CodexRunResult


EventCallback = Callable[[str, str], None]


@dataclass
class RunnerOptions:
    model: str | None = None
    dangerous_yolo: bool = False
    full_auto: bool = False
    skip_git_repo_check: bool = False
    extra_args: list[str] | None = None
    output_schema_path: str | None = None


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

        def consume_stderr() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                text = line.rstrip("\n")
                stderr_lines.append(text)
                self._emit(self._stream_name("stderr", run_label), text)

        stderr_thread = threading.Thread(target=consume_stderr, daemon=True)
        stderr_thread.start()

        assert process.stdout is not None
        for line in process.stdout:
            text = line.rstrip("\n")
            stdout_lines.append(text)
            self._emit(self._stream_name("stdout", run_label), text)
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

        process.wait()
        stderr_thread.join(timeout=2.0)

        if turn_completed and not turn_failed:
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
    def _stream_name(stream: str, run_label: str | None) -> str:
        if not run_label:
            return stream
        return f"{run_label}.{stream}"

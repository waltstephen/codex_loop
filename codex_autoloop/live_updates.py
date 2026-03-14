from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from .telegram_notifier import TelegramNotifier


class MessageNotifier(Protocol):
    def send_message(self, message: str) -> None:
        ...


def extract_agent_message(stream: str, line: str) -> tuple[str, str] | None:
    if not stream.endswith(".stdout"):
        return None
    actor = stream.split(".", 1)[0]
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "item.completed":
        return None
    item = payload.get("item", {})
    if not isinstance(item, dict):
        return None
    if item.get("type") != "agent_message":
        return None
    text = item.get("text", "")
    if not isinstance(text, str):
        return None
    message = text.strip()
    if not message:
        return None
    return actor, message


@dataclass
class TelegramStreamReporterConfig:
    interval_seconds: int = 30
    max_items_per_push: int = 6
    max_chars: int | None = 3500
    max_item_chars: int | None = 420
    compact_items: bool = True
    header_template: str | None = "[autoloop] live update {ts}"


class TelegramStreamReporter:
    def __init__(
        self,
        *,
        notifier: TelegramNotifier,
        config: TelegramStreamReporterConfig,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.notifier = notifier
        self.config = config
        self.on_error = on_error
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending: list[tuple[str, str]] = []
        self._last_seen_by_actor: dict[str, str] = {}

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        while self.flush():
            pass

    def add_message(self, actor: str, message: str) -> None:
        normalized = message.strip()
        if not normalized:
            return
        with self._lock:
            if self._last_seen_by_actor.get(actor) == normalized:
                return
            self._last_seen_by_actor[actor] = normalized
            self._pending.append((actor, normalized))

    def flush(self) -> bool:
        with self._lock:
            if not self._pending:
                return False
            batch = self._pending[: self.config.max_items_per_push]
            self._pending = self._pending[self.config.max_items_per_push :]
        message = self._format_batch(batch)
        self.notifier.send_message(message)
        return True

    def _run(self) -> None:
        interval = max(5, int(self.config.interval_seconds))
        while not self._stop_event.wait(interval):
            try:
                self.flush()
            except Exception as exc:
                if self.on_error:
                    self.on_error(f"telegram live flush error: {exc}")

    def _format_batch(self, batch: list[tuple[str, str]]) -> str:
        return _format_batch(batch, self.config)


class GenericStreamReporter:
    def __init__(
        self,
        *,
        notifier: MessageNotifier,
        config: TelegramStreamReporterConfig,
        on_error: Callable[[str], None] | None = None,
        error_label: str = "live",
        allowed_actors: set[str] | None = None,
    ) -> None:
        self.notifier = notifier
        self.config = config
        self.on_error = on_error
        self.error_label = error_label
        self.allowed_actors = {item.strip() for item in (allowed_actors or set()) if item.strip()} or None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending: list[tuple[str, str]] = []
        self._last_seen_by_actor: dict[str, str] = {}

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        while self.flush():
            pass

    def add_message(self, actor: str, message: str) -> None:
        normalized = message.strip()
        if not normalized:
            return
        if self.allowed_actors is not None and actor not in self.allowed_actors:
            return
        with self._lock:
            if self._last_seen_by_actor.get(actor) == normalized:
                return
            self._last_seen_by_actor[actor] = normalized
            self._pending.append((actor, normalized))

    def flush(self) -> bool:
        with self._lock:
            if not self._pending:
                return False
            batch = self._pending[: self.config.max_items_per_push]
            self._pending = self._pending[self.config.max_items_per_push :]
        self.notifier.send_message(_format_batch(batch, self.config))
        return True

    def _run(self) -> None:
        interval = max(5, int(self.config.interval_seconds))
        while not self._stop_event.wait(interval):
            try:
                self.flush()
            except Exception as exc:
                if self.on_error:
                    self.on_error(f"{self.error_label} live flush error: {exc}")


class ChildLogStreamFollower:
    def __init__(
        self,
        *,
        path: Path,
        reporters: list[GenericStreamReporter],
        poll_interval_seconds: int = 2,
    ) -> None:
        self.path = path
        self.reporters = reporters
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0
        self._current_actor: str | None = None
        self._current_lines: list[str] = []

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._flush_block()

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_interval_seconds):
            if not self.path.exists():
                continue
            size = self.path.stat().st_size
            if size < self._offset:
                self._offset = 0
            if size == self._offset:
                continue
            try:
                with self.path.open("r", encoding="utf-8") as stream:
                    stream.seek(self._offset)
                    chunk = stream.read()
                    self._offset = stream.tell()
            except Exception:
                continue
            for line in chunk.splitlines():
                self._consume_line(line)

    def _consume_line(self, line: str) -> None:
        actor = parse_child_actor_line(line)
        if actor is not None:
            self._flush_block()
            self._current_actor = actor
            self._current_lines = []
            return
        if not line.strip():
            if self._current_actor is None:
                return
            # Preserve paragraph breaks inside a single agent message block.
            self._current_lines.append("")
            return
        if self._current_actor is None:
            return
        self._current_lines.append(line.strip())

    def _flush_block(self) -> None:
        if self._current_actor is None or not self._current_lines:
            self._current_actor = None if not self._current_lines else self._current_actor
            self._current_lines = []
            return
        message = "\n".join(self._current_lines).strip()
        for reporter in self.reporters:
            reporter.add_message(self._current_actor, message)
        self._current_actor = None
        self._current_lines = []


_CHILD_ACTOR_RE = re.compile(r"^\[(?P<actor>[^\]]+)\s+agent\]$")


def parse_child_actor_line(line: str) -> str | None:
    match = _CHILD_ACTOR_RE.match(line.strip())
    if not match:
        return None
    return match.group("actor").strip()


def _format_batch(batch: list[tuple[str, str]], config: TelegramStreamReporterConfig) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines: list[str] = []
    if config.header_template is not None:
        lines.append(config.header_template.format(ts=now))
    for actor, text in batch:
        rendered_text = " ".join(text.split()) if config.compact_items else text.strip()
        if config.max_item_chars is not None:
            rendered_text = rendered_text[: config.max_item_chars]
        if config.compact_items:
            lines.append(f"- {actor}: {rendered_text}")
        else:
            if lines:
                lines.append("")
            lines.append(f"[{actor} agent]")
            lines.append(rendered_text)
    rendered = "\n".join(lines)
    if config.max_chars is None or len(rendered) <= config.max_chars:
        return rendered
    return rendered[: config.max_chars]

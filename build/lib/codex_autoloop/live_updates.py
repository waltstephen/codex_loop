from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .telegram_notifier import TelegramNotifier


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
    max_chars: int = 3500


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
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        lines = [f"[autoloop] live update {now}"]
        for actor, text in batch:
            compact = " ".join(text.split())
            lines.append(f"- {actor}: {compact[:420]}")
        rendered = "\n".join(lines)
        if len(rendered) <= self.config.max_chars:
            return rendered
        return rendered[: self.config.max_chars]

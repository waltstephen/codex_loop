from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re


@dataclass
class OperatorMessage:
    ts: str
    source: str
    kind: str
    text: str


class LoopControlState:
    def __init__(self, operator_messages_file: str | None = None) -> None:
        self._lock = threading.Lock()
        self._interrupt_reason: str | None = None
        self._pending_instruction: str | None = None
        self._stop_requested = False
        self._operator_messages_file = operator_messages_file
        self._messages: list[OperatorMessage] = self._load_messages_from_file(operator_messages_file)

    def request_inject(self, instruction: str, source: str = "operator") -> None:
        text = instruction.strip()
        if not text:
            return
        with self._lock:
            self._pending_instruction = text
            self._interrupt_reason = f"{source} requested instruction update"
            self._messages.append(
                OperatorMessage(
                    ts=self._now(),
                    source=source,
                    kind="inject",
                    text=text,
                )
            )
            self._write_messages_doc_locked()

    def request_stop(self, source: str = "operator") -> None:
        with self._lock:
            self._stop_requested = True
            self._interrupt_reason = f"{source} requested stop"
            self._messages.append(
                OperatorMessage(
                    ts=self._now(),
                    source=source,
                    kind="stop",
                    text="stop requested",
                )
            )
            self._write_messages_doc_locked()

    def record_message(self, *, text: str, source: str = "operator", kind: str = "message") -> None:
        normalized = text.strip()
        if not normalized:
            return
        with self._lock:
            self._messages.append(
                OperatorMessage(
                    ts=self._now(),
                    source=source,
                    kind=kind,
                    text=normalized,
                )
            )
            self._write_messages_doc_locked()

    def consume_interrupt_reason(self) -> str | None:
        with self._lock:
            reason = self._interrupt_reason
            self._interrupt_reason = None
            return reason

    def consume_pending_instruction(self) -> str | None:
        with self._lock:
            instruction = self._pending_instruction
            self._pending_instruction = None
            return instruction

    def is_stop_requested(self) -> bool:
        with self._lock:
            return self._stop_requested

    def list_messages(self) -> list[str]:
        with self._lock:
            return [f"[{m.ts}] [{m.source}] [{m.kind}] {m.text}" for m in self._messages]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_messages_doc_locked(self) -> None:
        if not self._operator_messages_file:
            return
        path = Path(self._operator_messages_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Operator Messages",
            "",
            "Messages entered by user/operator channels (Telegram/terminal/initial objective).",
            "",
        ]
        for item in self._messages:
            lines.append(f"- `{item.ts}` `{item.source}` `{item.kind}`: {item.text}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _load_messages_from_file(path: str | None) -> list[OperatorMessage]:
        if not path:
            return []
        p = Path(path)
        if not p.exists():
            return []
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            return []
        out: list[OperatorMessage] = []
        pattern = re.compile(r"^- `([^`]+)` `([^`]+)` `([^`]+)`: (.*)$")
        for line in content.splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            ts, source, kind, text = match.groups()
            out.append(
                OperatorMessage(
                    ts=ts.strip(),
                    source=source.strip(),
                    kind=kind.strip(),
                    text=text.strip(),
                )
            )
        return out

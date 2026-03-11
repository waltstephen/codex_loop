from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..models import ReviewDecision, RoundSummary


@dataclass
class OperatorMessage:
    ts: str
    source: str
    kind: str
    text: str


class LoopStateStore:
    def __init__(
        self,
        *,
        objective: str = "",
        state_file: str | None = None,
        operator_messages_file: str | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._objective = objective
        self._state_file = state_file
        self._operator_messages_file = operator_messages_file
        self._interrupt_reason: str | None = None
        self._pending_instruction: str | None = None
        self._stop_requested = False
        self._messages: list[OperatorMessage] = []
        self._rounds: list[RoundSummary] = []
        self._session_id: str | None = None
        self._latest_review: ReviewDecision | None = None
        self._runtime: dict[str, object | None] = {
            "status": "idle",
            "round": 0,
            "session_id": None,
            "updated_at": None,
            "success": None,
            "stop_reason": None,
        }

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

    def runtime_snapshot(self) -> dict[str, object | None]:
        with self._lock:
            return dict(self._runtime)

    def handle_event(self, event: dict[str, object]) -> None:
        event_type = str(event.get("type", ""))
        with self._lock:
            self._runtime["updated_at"] = event.get("ts") or self._now()
            if event_type == "loop.started":
                self._runtime["status"] = "running"
                self._runtime["session_id"] = event.get("session_id")
                self._runtime["round"] = 0
                self._runtime["success"] = None
                self._runtime["stop_reason"] = None
            elif event_type == "round.started":
                self._runtime["round"] = event.get("round_index", self._runtime["round"])
                self._runtime["session_id"] = event.get("session_id", self._runtime["session_id"])
            elif event_type == "round.main.completed":
                self._runtime["session_id"] = event.get("session_id", self._runtime["session_id"])
            elif event_type == "loop.completed":
                self._runtime["status"] = "completed"
                self._runtime["success"] = event.get("success")
                self._runtime["stop_reason"] = event.get("stop_reason")

    def record_round(
        self,
        round_summary: RoundSummary,
        *,
        session_id: str | None,
        current_review: ReviewDecision,
    ) -> None:
        with self._lock:
            self._rounds.append(round_summary)
            self._session_id = session_id
            self._latest_review = current_review
            self._write_state_locked()

    def record_completion(self, *, success: bool, stop_reason: str, session_id: str | None) -> None:
        with self._lock:
            self._session_id = session_id
            self._runtime["status"] = "completed"
            self._runtime["success"] = success
            self._runtime["stop_reason"] = stop_reason
            self._runtime["updated_at"] = self._now()
            self._write_state_locked()

    @staticmethod
    def _serialize_round(round_summary: RoundSummary) -> dict[str, object]:
        data = asdict(round_summary)
        data["checks"] = [asdict(item) for item in round_summary.checks]
        data["review"] = asdict(round_summary.review)
        return data

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_state_locked(self) -> None:
        if not self._state_file:
            return
        payload = {
            "updated_at": self._now(),
            "objective": self._objective,
            "session_id": self._session_id,
            "round_count": len(self._rounds),
            "latest_review_status": self._latest_review.status if self._latest_review else None,
            "status": self._runtime["status"],
            "success": self._runtime["success"],
            "stop_reason": self._runtime["stop_reason"],
            "rounds": [self._serialize_round(item) for item in self._rounds],
        }
        path = Path(self._state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

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

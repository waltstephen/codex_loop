from __future__ import annotations

import threading


class LoopControlState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._interrupt_reason: str | None = None
        self._pending_instruction: str | None = None
        self._stop_requested = False

    def request_inject(self, instruction: str, source: str = "operator") -> None:
        text = instruction.strip()
        if not text:
            return
        with self._lock:
            self._pending_instruction = text
            self._interrupt_reason = f"{source} requested instruction update"

    def request_stop(self, source: str = "operator") -> None:
        with self._lock:
            self._stop_requested = True
            self._interrupt_reason = f"{source} requested stop"

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

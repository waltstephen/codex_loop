from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class BusCommand:
    kind: str
    text: str
    source: str
    ts: float


class JsonlCommandBus:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._offset = 0
        if self.path.exists():
            self._offset = self.path.stat().st_size

    def publish(self, command: BusCommand) -> None:
        line = json.dumps(asdict(command), ensure_ascii=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_new(self) -> list[BusCommand]:
        if not self.path.exists():
            return []
        out: list[BusCommand] = []
        with self._lock:
            with self.path.open("r", encoding="utf-8") as f:
                f.seek(self._offset)
                lines = f.readlines()
                self._offset = f.tell()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            kind = payload.get("kind")
            text = payload.get("text", "")
            source = payload.get("source", "unknown")
            ts = payload.get("ts", time.time())
            if not isinstance(kind, str):
                continue
            if not isinstance(text, str):
                text = str(text)
            if not isinstance(source, str):
                source = str(source)
            if not isinstance(ts, (int, float)):
                ts = time.time()
            out.append(BusCommand(kind=kind, text=text, source=source, ts=float(ts)))
        return out


def write_status(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def read_status(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data

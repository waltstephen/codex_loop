from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TokenLock:
    token_hash: str
    lock_path: Path
    meta_path: Path
    fd: int

    def release(self) -> None:
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
        try:
            self.meta_path.unlink(missing_ok=True)
        except Exception:
            pass


def acquire_token_lock(*, token: str, owner_info: dict[str, Any], lock_dir: str | Path | None = None) -> TokenLock:
    directory = Path(lock_dir or "/tmp/codex-autoloop-token-locks").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    lock_path = directory / f"{digest}.lock"
    meta_path = directory / f"{digest}.json"

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        detail = _read_meta(meta_path)
        owner_desc = json.dumps(detail, ensure_ascii=True) if detail else "unknown owner"
        raise RuntimeError(
            "Telegram token is already in use by another daemon. "
            f"owner={owner_desc}"
        ) from exc

    payload = dict(owner_info)
    payload["token_hash"] = digest
    payload["lock_path"] = str(lock_path)
    meta_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return TokenLock(token_hash=digest, lock_path=lock_path, meta_path=meta_path, fd=fd)


def _read_meta(meta_path: Path) -> dict[str, Any] | None:
    if not meta_path.exists():
        return None
    try:
        raw = meta_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload

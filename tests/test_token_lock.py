import os
from pathlib import Path

from codex_autoloop.token_lock import acquire_token_lock


def test_token_lock_conflict(tmp_path: Path) -> None:
    lock1 = acquire_token_lock(
        token="123:secret",
        owner_info={"pid": os.getpid()},
        lock_dir=tmp_path,
    )
    try:
        error = None
        try:
            acquire_token_lock(
                token="123:secret",
                owner_info={"pid": "other"},
                lock_dir=tmp_path,
            )
        except RuntimeError as exc:
            error = exc
        assert error is not None
        assert "already in use" in str(error)
    finally:
        lock1.release()


def test_token_lock_release_allows_reacquire(tmp_path: Path) -> None:
    lock1 = acquire_token_lock(
        token="123:secret",
        owner_info={"pid": "a"},
        lock_dir=tmp_path,
    )
    lock1.release()
    lock2 = acquire_token_lock(
        token="123:secret",
        owner_info={"pid": "b"},
        lock_dir=tmp_path,
    )
    lock2.release()

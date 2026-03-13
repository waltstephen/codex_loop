import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from codex_autoloop import daemon_bus
from codex_autoloop.daemon_bus import (
    BusCommand,
    JsonlCommandBus,
    inspect_daemon_status_payload,
    read_status,
    write_status,
)


def test_jsonl_bus_publish_and_read(tmp_path: Path) -> None:
    path = tmp_path / "commands.jsonl"
    bus = JsonlCommandBus(path)
    bus.publish(BusCommand(kind="run", text="hello", source="terminal", ts=time.time()))
    items = bus.read_new()
    assert len(items) == 1
    assert items[0].kind == "run"
    assert items[0].text == "hello"
    assert bus.read_new() == []


def test_status_read_write(tmp_path: Path) -> None:
    status_path = tmp_path / "status.json"
    write_status(status_path, {"running": True, "pid": 123})
    status = read_status(status_path)
    assert status is not None
    assert status["running"] is True
    assert status["pid"] == 123


def test_inspect_daemon_status_payload_detects_stale_running_status(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr("codex_autoloop.daemon_bus.is_pid_running", lambda pid: True)
    inspection = inspect_daemon_status_payload(
        {
            "daemon_running": True,
            "daemon_pid": 123,
            "updated_at": (now - timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
        },
        stale_after_seconds=15,
        now=now,
    )
    assert inspection.is_live is False
    assert inspection.reason is not None
    assert "stale" in inspection.reason


def test_inspect_daemon_status_payload_detects_dead_pid(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr("codex_autoloop.daemon_bus.is_pid_running", lambda pid: False)
    inspection = inspect_daemon_status_payload(
        {
            "daemon_running": True,
            "daemon_pid": 123,
            "updated_at": now.isoformat().replace("+00:00", "Z"),
        },
        stale_after_seconds=15,
        now=now,
    )
    assert inspection.is_live is False
    assert inspection.reason == "Daemon status points to dead pid 123."


def test_is_pid_running_uses_tasklist_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(daemon_bus, "os", SimpleNamespace(name="nt"))

    def fake_run(args, capture_output, text, timeout):
        assert args == ["tasklist", "/FI", "PID eq 456"]
        assert capture_output is True
        assert text is True
        assert timeout == 10
        return SimpleNamespace(returncode=0, stdout="python.exe                 456 Console", stderr="")

    monkeypatch.setattr(daemon_bus.subprocess, "run", fake_run)
    assert daemon_bus.is_pid_running(456) is True


def test_is_pid_running_uses_os_kill_on_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(daemon_bus.os, "name", "posix", raising=False)
    seen: list[tuple[int, int]] = []

    def fake_kill(pid: int, sig: int) -> None:
        seen.append((pid, sig))

    monkeypatch.setattr(daemon_bus.os, "kill", fake_kill)
    assert daemon_bus.is_pid_running(789) is True
    assert seen == [(789, 0)]

import time
from pathlib import Path

from codex_autoloop.daemon_bus import BusCommand, JsonlCommandBus, read_status, write_status


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

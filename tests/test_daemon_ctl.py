from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from codex_autoloop import daemon_ctl
from codex_autoloop.daemon_bus import DaemonStatusInspection


def test_load_status_for_cli_marks_dead_running_daemon_stale(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "daemon_status.json"
    payload = {"daemon_running": True, "running": True, "daemon_pid": 321}
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload=payload,
            is_live=False,
            reason="Daemon status points to dead pid 321.",
            daemon_pid=321,
            updated_at=None,
        ),
    )
    status = daemon_ctl.load_status_for_cli(status_path, require_live=False)
    assert status["daemon_status_state"] == "stale"
    assert status["daemon_status_live"] is False
    assert status["daemon_running"] is False
    assert status["running"] is False
    assert "dead pid 321" in status["daemon_status_warning"]


def test_load_status_for_cli_keeps_clean_offline_status(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "daemon_status.json"
    payload = {"daemon_running": False, "running": False, "daemon_pid": 321}
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload=payload,
            is_live=False,
            reason="Daemon is not running.",
            daemon_pid=321,
            updated_at=None,
        ),
    )
    status = daemon_ctl.load_status_for_cli(status_path, require_live=False)
    assert status["daemon_status_state"] == "offline"
    assert status["daemon_running"] is False
    assert status["running"] is False


def test_show_plan_rejects_stale_daemon_status(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={"daemon_running": True, "daemon_pid": 999, "updated_at": "2026-03-13T00:00:00Z"},
            is_live=False,
            reason="Daemon status is stale (30s old).",
            daemon_pid=999,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-plan"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "stale" in captured.out


def test_show_main_prompt_rejects_missing_child_path(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={"daemon_running": True, "running": False, "daemon_pid": 123, "updated_at": "2026-03-13T00:00:00Z"},
            is_live=True,
            reason=None,
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-main-prompt"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "No main prompt path found" in captured.out


def test_status_command_prints_offline_state_without_online_misreport(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={"daemon_running": False, "running": False, "daemon_pid": 123, "updated_at": "2026-03-13T00:00:00Z"},
            is_live=False,
            reason="Daemon is not running.",
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "status"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["daemon_status_state"] == "offline"
    assert payload["daemon_running"] is False

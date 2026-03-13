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


def test_show_plan_prints_live_plan_markdown(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    plan_path = tmp_path / "plan_overview.md"
    plan_path.write_text("# Plan\n\n- inspect daemon status\n", encoding="utf-8")
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={
                "daemon_running": True,
                "running": True,
                "daemon_pid": 123,
                "updated_at": "2026-03-13T00:00:00Z",
                "child_plan_overview_path": str(plan_path),
            },
            is_live=True,
            reason=None,
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-plan"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out == "# Plan\n\n- inspect daemon status\n\n"


def test_show_main_prompt_prints_live_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    prompt_path = tmp_path / "main_prompt.md"
    prompt_path.write_text("# Main Prompt\n\nfix btw delivery\n", encoding="utf-8")
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={
                "daemon_running": True,
                "running": True,
                "daemon_pid": 123,
                "updated_at": "2026-03-13T00:00:00Z",
                "child_main_prompt_path": str(prompt_path),
            },
            is_live=True,
            reason=None,
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-main-prompt"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out == "# Main Prompt\n\nfix btw delivery\n\n"


def test_show_review_prints_live_review_markdown(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    review_dir = tmp_path / "reviews"
    review_dir.mkdir()
    index_path = review_dir / "index.md"
    index_path.write_text("# Reviews\n\n- round 1 ok\n", encoding="utf-8")
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={
                "daemon_running": True,
                "running": True,
                "daemon_pid": 123,
                "updated_at": "2026-03-13T00:00:00Z",
                "child_review_summaries_dir": str(review_dir),
            },
            is_live=True,
            reason=None,
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-review"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out == "# Reviews\n\n- round 1 ok\n\n"


def test_show_review_context_uses_run_state_file_from_status(monkeypatch, tmp_path: Path, capsys) -> None:
    bus_dir = tmp_path / "bus"
    bus_dir.mkdir()
    review_dir = tmp_path / "reviews"
    review_dir.mkdir()
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        daemon_ctl,
        "inspect_daemon_status",
        lambda *args, **kwargs: DaemonStatusInspection(
            payload={
                "daemon_running": True,
                "running": True,
                "daemon_pid": 123,
                "updated_at": "2026-03-13T00:00:00Z",
                "child_review_summaries_dir": str(review_dir),
                "child_operator_messages_path": str(tmp_path / "operator_messages.md"),
                "run_state_file": str(tmp_path / "custom-home" / "last_state.json"),
                "run_check": ["pytest -q"],
            },
            is_live=True,
            reason=None,
            daemon_pid=123,
            updated_at=datetime.now(timezone.utc),
        ),
    )

    def fake_render_review_context(**kwargs) -> str:
        captured.update(kwargs)
        return "# Review Context\n"

    monkeypatch.setattr(daemon_ctl, "render_review_context", fake_render_review_context)
    monkeypatch.setattr(sys, "argv", ["codex-autoloop-daemon-ctl", "--bus-dir", str(bus_dir), "show-review-context"])
    with pytest.raises(SystemExit) as exc:
        daemon_ctl.main()
    assert exc.value.code == 0
    assert capsys.readouterr().out == "# Review Context\n\n"
    assert captured["state_file"] == str(tmp_path / "custom-home" / "last_state.json")
    assert captured["review_summaries_dir"] == str(review_dir)

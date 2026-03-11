import sys
from pathlib import Path

from codex_autoloop import setup_wizard


def test_resolve_daemon_launch_prefix_fallback(monkeypatch) -> None:
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: None)
    prefix = setup_wizard.resolve_daemon_launch_prefix()
    assert prefix[:2] == [sys.executable, "-m"]
    assert prefix[2] == "codex_autoloop.telegram_daemon"


def test_resolve_daemon_ctl_hint_fallback(monkeypatch) -> None:
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: None)
    hint = setup_wizard.resolve_daemon_ctl_hint()
    assert "codex_autoloop.daemon_ctl" in hint


def test_stop_existing_daemon_no_pid_file(tmp_path: Path) -> None:
    setup_wizard.stop_existing_daemon(home_dir=tmp_path, bus_dir=tmp_path / "bus")

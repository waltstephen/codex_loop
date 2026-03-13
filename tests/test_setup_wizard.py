import sys
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
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


def test_is_pid_running_timeout_is_treated_as_running(monkeypatch) -> None:
    monkeypatch.setattr(setup_wizard, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(setup_wizard, "_run_quiet", lambda args, timeout: None)
    assert setup_wizard._is_pid_running("123") is True


def test_stop_existing_daemon_tolerates_probe_timeout(monkeypatch, tmp_path: Path) -> None:
    pid_path = tmp_path / "daemon.pid"
    pid_path.write_text("33580", encoding="utf-8")
    monkeypatch.setattr(setup_wizard, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: None)
    monkeypatch.setattr(setup_wizard.time, "sleep", lambda seconds: None)

    calls: list[tuple[str, bool]] = []
    probe_results = iter([True, True, True])

    monkeypatch.setattr(setup_wizard, "_is_pid_running", lambda pid: next(probe_results))
    monkeypatch.setattr(
        setup_wizard,
        "_terminate_pid",
        lambda pid, force: calls.append((pid, force)),
    )
    monkeypatch.setattr(
        setup_wizard,
        "_run_quiet",
        lambda args, timeout: calls.append((" ".join(args), False)),
    )
    setup_wizard.stop_existing_daemon(home_dir=tmp_path, bus_dir=tmp_path / "bus")
    assert not pid_path.exists()
    assert any(isinstance(item[0], str) and "codex_autoloop.daemon_ctl" in item[0] for item in calls)
    assert ("33580", False) in calls
    assert ("33580", True) in calls


def test_prompt_model_choice_default(monkeypatch) -> None:
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: "")
    assert setup_wizard.prompt_model_choice() == "quality"


def test_build_parser_accepts_plan_args() -> None:
    parser = setup_wizard.build_parser()
    args = parser.parse_args(
        [
            "--run-plan-mode",
            "record",
            "--run-plan-model",
            "gpt-5.4",
            "--run-plan-reasoning-effort",
            "high",
        ]
    )
    assert args.run_plan_mode == "record"
    assert args.run_plan_model == "gpt-5.4"
    assert args.run_plan_reasoning_effort == "high"


def test_resolve_effective_chat_id_returns_explicit() -> None:
    assert setup_wizard.resolve_effective_chat_id(
        bot_token="123:abc",
        requested_chat_id="8533505134",
        timeout_seconds=5,
    ) == "8533505134"


def test_resolve_effective_chat_id_resolves_auto(monkeypatch) -> None:
    monkeypatch.setattr(setup_wizard, "resolve_chat_id", lambda **kwargs: "8533505134")
    assert setup_wizard.resolve_effective_chat_id(
        bot_token="123:abc",
        requested_chat_id="auto",
        timeout_seconds=5,
    ) == "8533505134"


def test_resolve_effective_chat_id_preserves_explicit_numeric_string() -> None:
    assert setup_wizard.resolve_effective_chat_id(
        bot_token="123:abc",
        requested_chat_id="1",
        timeout_seconds=5,
    ) == "1"


def test_normalize_reasoning_effort_accepts_blank_and_lowercases() -> None:
    assert setup_wizard.normalize_reasoning_effort("", field_name="main") is None
    assert setup_wizard.normalize_reasoning_effort(" HIGH ", field_name="main") == "high"


def test_normalize_reasoning_effort_rejects_invalid_value() -> None:
    try:
        setup_wizard.normalize_reasoning_effort("maximum", field_name="main")
    except ValueError as exc:
        assert "must be one of" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid reasoning effort")


def test_wait_for_daemon_ready_reads_running_status(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "daemon_status.json"
    launched_after = datetime.now(timezone.utc) - timedelta(seconds=1)
    updated_at = (launched_after + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    status_path.write_text(
        f'{{"daemon_running": true, "daemon_pid": 123, "updated_at": "{updated_at}"}}',
        encoding="utf-8",
    )

    class _FakeProcess:
        pid = 123

        def poll(self):
            return None

    monkeypatch.setattr(setup_wizard.time, "sleep", lambda seconds: None)
    status = setup_wizard.wait_for_daemon_ready(
        status_path=status_path,
        process=_FakeProcess(),
        timeout_seconds=1,
        launched_after=launched_after,
    )
    assert status == {
        "daemon_running": True,
        "daemon_pid": 123,
        "updated_at": updated_at,
    }


def test_wait_for_daemon_ready_rejects_stale_status_file(monkeypatch, tmp_path: Path) -> None:
    status_path = tmp_path / "daemon_status.json"
    launched_after = datetime(2026, 3, 13, 0, 0, 1, tzinfo=timezone.utc)
    status_path.write_text(
        '{"daemon_running": true, "daemon_pid": 999, "updated_at": "2026-03-13T00:00:00Z"}',
        encoding="utf-8",
    )

    class _FakeProcess:
        pid = 123

        def poll(self):
            return None

    tick = {"value": 0.0}

    def fake_monotonic() -> float:
        tick["value"] += 0.3
        return tick["value"]

    monkeypatch.setattr(setup_wizard.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(setup_wizard.time, "sleep", lambda seconds: None)
    assert (
        setup_wizard.wait_for_daemon_ready(
            status_path=status_path,
            process=_FakeProcess(),
            timeout_seconds=1,
            launched_after=launched_after,
        )
        is None
    )


def test_wait_for_daemon_ready_returns_none_when_process_exits(tmp_path: Path) -> None:
    class _FakeProcess:
        pid = 123

        def poll(self):
            return 2

    assert (
        setup_wizard.wait_for_daemon_ready(
            status_path=tmp_path / "daemon_status.json",
            process=_FakeProcess(),
            timeout_seconds=1,
            launched_after=datetime.now(timezone.utc),
        )
        is None
    )


def test_resolve_codex_autoloop_bin_creates_shim_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: None)
    path = setup_wizard.resolve_codex_autoloop_bin(tmp_path)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "codex_autoloop.cli" in content

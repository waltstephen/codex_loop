import sys
from pathlib import Path
from types import SimpleNamespace

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
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: default)
    assert setup_wizard.prompt_model_choice() is None


def test_prompt_model_choice_retries(monkeypatch) -> None:
    answers = iter(["abc", "99", "2"])
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: next(answers))
    assert setup_wizard.prompt_model_choice() == setup_wizard.MODEL_PRESETS[1].name


def test_prompt_reasoning_effort_retries(monkeypatch) -> None:
    answers = iter(["wrong", "high"])
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: next(answers))
    assert setup_wizard.prompt_reasoning_effort("x") == "high"


def test_prompt_chat_id_retries(monkeypatch) -> None:
    answers = iter(["abc", "-100123"])
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: next(answers))
    assert setup_wizard.prompt_chat_id() == "-100123"


def test_prompt_token_retries(monkeypatch) -> None:
    answers = iter(["invalid", "123:secret"])
    monkeypatch.setattr(setup_wizard, "prompt_secret", lambda prompt: next(answers))
    assert setup_wizard.prompt_token() == "123:secret"


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

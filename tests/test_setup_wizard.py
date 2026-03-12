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

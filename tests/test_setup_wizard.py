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
    assert setup_wizard.resolve_effective_chat_id(
        bot_token="123:abc",
        requested_chat_id="1",
        timeout_seconds=5,
    ) == "8533505134"


def test_resolve_codex_autoloop_bin_creates_shim_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: None)
    path = setup_wizard.resolve_codex_autoloop_bin(tmp_path)
    assert Path(path).exists()
    content = Path(path).read_text(encoding="utf-8")
    assert "codex_autoloop.cli" in content

import sys
from pathlib import Path

from codex_autoloop import codexloop


def test_parse_terminal_command_plain_text_routes_to_run_when_idle() -> None:
    cmd = codexloop.parse_terminal_command("implement feature", running=False)
    assert cmd is not None
    assert cmd.kind == "run"
    assert cmd.text == "implement feature"


def test_parse_terminal_command_plain_text_routes_to_inject_when_running() -> None:
    cmd = codexloop.parse_terminal_command("fix failing tests first", running=True)
    assert cmd is not None
    assert cmd.kind == "inject"
    assert cmd.text == "fix failing tests first"


def test_parse_terminal_command_explicit_commands() -> None:
    run = codexloop.parse_terminal_command("/run build dashboard", running=True)
    inject = codexloop.parse_terminal_command("/inject tweak prompt", running=False)
    stop = codexloop.parse_terminal_command("/stop", running=False)
    disable = codexloop.parse_terminal_command("/disable", running=False)
    status = codexloop.parse_terminal_command("/status", running=False)
    assert run is not None and run.kind == "run" and run.text == "build dashboard"
    assert inject is not None and inject.kind == "inject" and inject.text == "tweak prompt"
    assert stop is not None and stop.kind == "stop"
    assert disable is not None and disable.kind == "daemon-stop"
    assert status is not None and status.kind == "status"


def test_parse_terminal_command_rejects_empty_payload() -> None:
    assert codexloop.parse_terminal_command("/run   ", running=False) is None
    assert codexloop.parse_terminal_command("/inject   ", running=True) is None


def test_build_parser_supports_disable_subcommand() -> None:
    parser = codexloop.build_parser()
    args = parser.parse_args(["disable"])
    assert args.subcommand == "disable"


def test_build_parser_supports_help_subcommand() -> None:
    parser = codexloop.build_parser()
    args = parser.parse_args(["help"])
    assert args.subcommand == "help"


def test_build_parser_supports_init_subcommand() -> None:
    parser = codexloop.build_parser()
    args = parser.parse_args(["init"])
    assert args.subcommand == "init"


def test_supported_features_text_contains_core_commands() -> None:
    text = codexloop.supported_features_text()
    assert "codexloop help" in text
    assert "codexloop disable" in text
    assert "codexloop init" in text
    assert "/disable" in text


def test_main_help_does_not_require_codex_binary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["codexloop", "help"])
    monkeypatch.setattr(codexloop.shutil, "which", lambda name: None)
    codexloop.main()
    captured = capsys.readouterr()
    assert "codexloop supported features" in captured.out


def test_is_config_usable_requires_token_and_run_cd() -> None:
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": "."}) is True
    assert codexloop.is_config_usable({"telegram_bot_token": "bad-token", "run_cd": "."}) is False
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": ""}) is False


def test_run_interactive_config_uses_passed_run_cd(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "prompt_token", lambda: "123:abc")
    monkeypatch.setattr(codexloop, "prompt_chat_id", lambda: "auto")
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: "")
    monkeypatch.setattr(codexloop, "prompt_model_choice", lambda: None)
    monkeypatch.setattr(codexloop, "prompt_play_mode", lambda: codexloop.PLAY_MODES[1])
    config = codexloop.run_interactive_config(home_dir=tmp_path / ".codex_daemon", run_cd=tmp_path)
    assert config["run_cd"] == str(tmp_path.resolve())
    assert config["run_model_preset"] is None
    assert config["run_plan_mode"] == "fully-plan"
    assert config["run_plan_request_delay_seconds"] == 600
    assert config["run_plan_auto_execute_delay_seconds"] == 600
    assert config["run_yolo"] is True
    assert config["run_full_auto"] is False


def test_prompt_play_mode_selection(monkeypatch) -> None:
    answers = iter(["3"])
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: next(answers))
    mode = codexloop.prompt_play_mode()
    assert mode.name == "record-only"
    assert mode.run_plan_mode == "record-only"


def test_prompt_model_choice_selection(monkeypatch) -> None:
    answers = iter(["1"])
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: next(answers))
    model = codexloop.prompt_model_choice()
    assert model == codexloop.MODEL_PRESETS[0].name


def test_prompt_model_choice_default_inherits_codex(monkeypatch) -> None:
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: default)
    assert codexloop.prompt_model_choice() is None


def test_main_init_starts_background_without_attach(monkeypatch, tmp_path: Path, capsys) -> None:
    home_dir = tmp_path / ".codex_daemon"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": True,
        "run_plan_mode": "fully-plan",
        "run_plan_request_delay_seconds": 600,
        "run_plan_auto_execute_delay_seconds": 600,
        "run_resume_last_session": True,
        "run_main_reasoning_effort": None,
        "run_reviewer_reasoning_effort": None,
        "run_main_model": None,
        "run_reviewer_model": None,
        "run_model_preset": "codex-xhigh",
        "bus_dir": str(home_dir / "bus"),
        "logs_dir": str(home_dir / "logs"),
    }

    monkeypatch.setattr(sys, "argv", ["codexloop", "--home-dir", str(home_dir), "init"])
    monkeypatch.setattr(codexloop.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(codexloop, "load_config", lambda path: None)
    monkeypatch.setattr(codexloop, "run_interactive_config", lambda **kwargs: config)
    monkeypatch.setattr(codexloop, "stop_all_codexloop_loops", lambda **kwargs: None)
    monkeypatch.setattr(codexloop, "ensure_daemon_running", lambda **kwargs: 4321)
    monkeypatch.setattr(codexloop, "run_monitor_console", lambda **kwargs: (_ for _ in ()).throw(AssertionError("attach should not run")))
    monkeypatch.setattr(codexloop, "save_config", lambda path, payload: None)

    codexloop.main()
    captured = capsys.readouterr()
    assert "Daemon running in background. pid=4321" in captured.out
    assert "Use `codexloop` to attach monitor" in captured.out


def test_parse_pid_supports_int_and_digit_string() -> None:
    assert codexloop.parse_pid(123) == 123
    assert codexloop.parse_pid("456") == 456
    assert codexloop.parse_pid("setup-probe") is None
    assert codexloop.parse_pid(-1) is None


def test_build_daemon_command_uses_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "resolve_daemon_launch_prefix", lambda: ["daemon-bin"])
    home_dir = tmp_path / ".codex_daemon"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": "pytest -q",
        "run_max_rounds": 500,
        "run_skip_git_repo_check": True,
        "run_full_auto": False,
        "run_yolo": True,
        "run_plan_mode": "fully-plan",
        "run_plan_request_delay_seconds": 600,
        "run_plan_auto_execute_delay_seconds": 600,
        "run_resume_last_session": True,
        "run_model_preset": "quality",
        "bus_dir": str(home_dir / "bus"),
        "logs_dir": str(home_dir / "logs"),
    }
    cmd = codexloop.build_daemon_command(
        config=config,
        home_dir=home_dir,
        token_lock_dir="/tmp/token-locks",
    )
    assert cmd[0] == "daemon-bin"
    assert "--telegram-bot-token" in cmd
    assert "--run-max-rounds" in cmd
    assert "--run-plan-mode" in cmd
    assert "--run-plan-request-delay-seconds" in cmd
    assert "--run-plan-auto-execute-delay-seconds" in cmd
    assert "--run-check" in cmd
    assert "--run-model-preset" in cmd
    assert "--run-skip-git-repo-check" in cmd
    assert "--run-yolo" in cmd
    assert "--run-resume-last-session" in cmd


def test_build_daemon_command_forces_yolo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "resolve_daemon_launch_prefix", lambda: ["daemon-bin"])
    home_dir = tmp_path / ".codex_daemon"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": False,
        "run_plan_mode": "execute-only",
        "run_resume_last_session": True,
        "run_model_preset": "quality",
        "bus_dir": str(home_dir / "bus"),
        "logs_dir": str(home_dir / "logs"),
    }
    cmd = codexloop.build_daemon_command(config=config, home_dir=home_dir, token_lock_dir="/tmp/token-locks")
    assert "--run-yolo" in cmd
    assert "--no-run-yolo" not in cmd

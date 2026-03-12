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


def test_is_config_usable_requires_token_and_run_cd() -> None:
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": "."}) is True
    assert codexloop.is_config_usable({"telegram_bot_token": "bad-token", "run_cd": "."}) is False
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": ""}) is False


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
    assert "--run-check" in cmd
    assert "--run-model-preset" in cmd
    assert "--run-skip-git-repo-check" in cmd
    assert "--run-yolo" in cmd
    assert "--run-resume-last-session" in cmd

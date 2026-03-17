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
    new = codexloop.parse_terminal_command("/new", running=False)
    mode = codexloop.parse_terminal_command("/mode auto", running=False)
    status = codexloop.parse_terminal_command("/status", running=False)
    assert run is not None and run.kind == "run" and run.text == "build dashboard"
    assert inject is not None and inject.kind == "inject" and inject.text == "tweak prompt"
    assert stop is not None and stop.kind == "stop"
    assert new is not None and new.kind == "fresh-session"
    assert mode is not None and mode.kind == "mode" and mode.text == "auto"
    assert status is not None and status.kind == "status"


def test_parse_terminal_command_rejects_empty_payload() -> None:
    assert codexloop.parse_terminal_command("/run   ", running=False) is None
    assert codexloop.parse_terminal_command("/inject   ", running=True) is None


def test_build_parser_supports_daemon_stop_subcommand() -> None:
    parser = codexloop.build_parser()
    args = parser.parse_args(["daemon-stop"])
    assert args.subcommand == "daemon-stop"


def test_build_parser_supports_new_subcommand() -> None:
    parser = codexloop.build_parser()
    args = parser.parse_args(["new"])
    assert args.subcommand == "new"


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
    assert "argusbot help" in text
    assert "argusbot new" in text
    assert "argusbot mode <off|auto|record>" in text
    assert "argusbot init" in text
    assert "/daemon-stop" in text
    assert "/new" in text


def test_main_help_does_not_require_codex_binary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["argusbot", "help"])
    monkeypatch.setattr(codexloop.shutil, "which", lambda name: None)
    codexloop.main()
    captured = capsys.readouterr()
    assert "ArgusBot supported features" in captured.out


def test_is_config_usable_requires_token_and_run_cd() -> None:
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": "."}) is True
    assert codexloop.is_config_usable({"telegram_bot_token": "bad-token", "run_cd": "."}) is False
    assert (
        codexloop.is_config_usable(
            {
                "feishu_app_id": "cli_xxx",
                "feishu_app_secret": "secret",
                "feishu_chat_id": "oc_123",
                "run_cd": ".",
            }
        )
        is True
    )
    assert codexloop.is_config_usable({"telegram_bot_token": "123:abc", "run_cd": ""}) is False


def test_run_interactive_config_uses_passed_run_cd(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "prompt_control_channel", lambda default="telegram": "telegram")
    monkeypatch.setattr(codexloop, "prompt_token", lambda: "123:abc")
    monkeypatch.setattr(codexloop, "prompt_chat_id", lambda: "auto")
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: "")
    monkeypatch.setattr(codexloop, "prompt_model_choice", lambda: None)
    monkeypatch.setattr(codexloop, "prompt_copilot_proxy_choice", lambda preferred=False: (False, None, 18080))
    monkeypatch.setattr(codexloop, "prompt_play_mode", lambda: codexloop.PLAY_MODES[1])
    config = codexloop.run_interactive_config(home_dir=tmp_path / ".argusbot", run_cd=tmp_path)
    assert config["run_cd"] == str(tmp_path.resolve())
    assert config["feishu_app_id"] is None
    assert config["feishu_app_secret"] is None
    assert config["feishu_chat_id"] is None
    assert config["run_model_preset"] is None
    assert config["run_planner_mode"] == "auto"
    assert config["run_plan_mode"] == "fully-plan"
    assert config["run_plan_request_delay_seconds"] == 600
    assert config["run_plan_auto_execute_delay_seconds"] == 600
    assert config["run_yolo"] is True
    assert config["run_full_auto"] is False
    assert config["run_copilot_proxy"] is False
    assert config["run_runner_backend"] == "codex"
    assert config["run_codex_bin"]


def test_run_interactive_config_supports_feishu_channel(monkeypatch, tmp_path: Path) -> None:
    answers = iter(["1", "cli_xxx", "oc_123", ""])
    monkeypatch.setattr(codexloop, "prompt_control_channel", lambda default="telegram": "feishu")
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: next(answers))
    monkeypatch.setattr(codexloop, "prompt_secret", lambda prompt: "secret")
    monkeypatch.setattr(codexloop, "prompt_model_choice", lambda: None)
    monkeypatch.setattr(codexloop, "prompt_copilot_proxy_choice", lambda preferred=False: (False, None, 18080))
    monkeypatch.setattr(codexloop, "prompt_play_mode", lambda: codexloop.PLAY_MODES[1])
    config = codexloop.run_interactive_config(home_dir=tmp_path / ".argusbot", run_cd=tmp_path)
    assert config["telegram_bot_token"] is None
    assert config["telegram_chat_id"] is None
    assert config["feishu_app_id"] == "cli_xxx"
    assert config["feishu_app_secret"] == "secret"
    assert config["feishu_chat_id"] == "oc_123"
    assert config["run_runner_backend"] == "codex"


def test_run_interactive_config_marks_copilot_preset_as_preferred(monkeypatch, tmp_path: Path) -> None:
    observed: dict[str, bool] = {}

    def fake_prompt_copilot_proxy_choice(preferred=False):
        observed["preferred"] = preferred
        return False, None, 18080

    monkeypatch.setattr(codexloop, "prompt_control_channel", lambda default="telegram": "telegram")
    monkeypatch.setattr(codexloop, "prompt_token", lambda: "123:abc")
    monkeypatch.setattr(codexloop, "prompt_chat_id", lambda: "auto")
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: "")
    monkeypatch.setattr(codexloop, "prompt_model_choice", lambda: "copilot")
    monkeypatch.setattr(codexloop, "prompt_copilot_proxy_choice", fake_prompt_copilot_proxy_choice)
    monkeypatch.setattr(codexloop, "prompt_play_mode", lambda: codexloop.PLAY_MODES[1])

    codexloop.run_interactive_config(home_dir=tmp_path / ".argusbot", run_cd=tmp_path)

    assert observed == {"preferred": True}


def test_prompt_control_channel_default_is_telegram(monkeypatch) -> None:
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: default)
    assert codexloop.prompt_control_channel() == "telegram"


def test_prompt_control_channel_select_feishu(monkeypatch) -> None:
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: "2")
    assert codexloop.prompt_control_channel() == "feishu"


def test_prompt_play_mode_selection(monkeypatch) -> None:
    answers = iter(["3"])
    monkeypatch.setattr(codexloop, "prompt_input", lambda prompt, default: next(answers))
    mode = codexloop.prompt_play_mode()
    assert mode.name == "record"
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
    home_dir = tmp_path / ".argusbot"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": True,
        "run_planner_mode": "auto",
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

    monkeypatch.setattr(sys, "argv", ["argusbot", "--home-dir", str(home_dir), "init"])
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
    assert "Use `argusbot` to attach monitor" in captured.out


def test_main_init_calls_banner_once(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / ".argusbot"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": True,
        "run_planner_mode": "auto",
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
    observed: list[str | None] = []

    monkeypatch.setattr(sys, "argv", ["argusbot", "--home-dir", str(home_dir), "init"])
    monkeypatch.setattr(codexloop.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.setattr(codexloop, "load_config", lambda path: None)
    monkeypatch.setattr(codexloop, "run_interactive_config", lambda **kwargs: config)
    monkeypatch.setattr(codexloop, "stop_all_codexloop_loops", lambda **kwargs: None)
    monkeypatch.setattr(codexloop, "ensure_daemon_running", lambda **kwargs: 4321)
    monkeypatch.setattr(codexloop, "save_config", lambda path, payload: None)
    monkeypatch.setattr(
        codexloop,
        "maybe_print_banner",
        lambda *, subcommand, stream=None: observed.append(subcommand),
    )

    codexloop.main()
    assert observed == ["init"]


def test_parse_pid_supports_int_and_digit_string() -> None:
    assert codexloop.parse_pid(123) == 123
    assert codexloop.parse_pid("456") == 456
    assert codexloop.parse_pid("setup-probe") is None
    assert codexloop.parse_pid(-1) is None


def test_build_daemon_command_uses_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "resolve_daemon_launch_prefix", lambda: ["daemon-bin"])
    home_dir = tmp_path / ".argusbot"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": "pytest -q",
        "run_max_rounds": 500,
        "run_skip_git_repo_check": True,
        "run_full_auto": False,
        "run_yolo": True,
        "run_planner_mode": "auto",
        "run_plan_mode": "fully-plan",
        "run_plan_request_delay_seconds": 600,
        "run_plan_auto_execute_delay_seconds": 600,
        "follow_up_auto_execute_seconds": 900,
        "run_resume_last_session": True,
        "run_model_preset": "quality",
        "run_runner_backend": "claude",
        "run_codex_bin": "/opt/homebrew/bin/claude",
        "run_copilot_proxy": True,
        "run_copilot_proxy_dir": "/home/v-boxiuli/copilot-proxy",
        "run_copilot_proxy_port": 18080,
        "codex_autoloop_bin": r"C:\Users\wen25\codex_loop\.venv\Scripts\python.exe -m codex_autoloop.cli",
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
    assert "--follow-up-auto-execute-seconds" in cmd
    assert "--run-check" in cmd
    assert "--run-model-preset" in cmd
    assert "--run-runner-backend" in cmd
    assert "--run-runner-bin" in cmd
    assert "--run-copilot-proxy" in cmd
    assert "--run-copilot-proxy-dir" in cmd
    assert "--run-copilot-proxy-port" in cmd
    assert "--argusbot-bin" in cmd
    assert "--run-skip-git-repo-check" in cmd
    assert "--run-yolo" in cmd
    assert "--run-resume-last-session" in cmd
    follow_up_index = cmd.index("--follow-up-auto-execute-seconds")
    assert cmd[follow_up_index + 1] == "900"
    child_command_index = cmd.index("--argusbot-bin")
    assert cmd[child_command_index + 1] == r"C:\Users\wen25\codex_loop\.venv\Scripts\python.exe -m codex_autoloop.cli"
    backend_index = cmd.index("--run-runner-backend")
    assert cmd[backend_index + 1] == "claude"
    runner_bin_index = cmd.index("--run-runner-bin")
    assert cmd[runner_bin_index + 1] == "/opt/homebrew/bin/claude"


def test_build_daemon_command_forces_yolo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "resolve_daemon_launch_prefix", lambda: ["daemon-bin"])
    home_dir = tmp_path / ".argusbot"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": False,
        "run_planner_mode": "off",
        "run_plan_mode": "execute-only",
        "run_resume_last_session": True,
        "run_model_preset": "quality",
        "bus_dir": str(home_dir / "bus"),
        "logs_dir": str(home_dir / "logs"),
    }
    cmd = codexloop.build_daemon_command(config=config, home_dir=home_dir, token_lock_dir="/tmp/token-locks")
    assert "--run-yolo" in cmd
    assert "--no-run-yolo" not in cmd


def test_build_daemon_command_includes_feishu(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(codexloop, "resolve_daemon_launch_prefix", lambda: ["daemon-bin"])
    home_dir = tmp_path / ".argusbot"
    config = {
        "telegram_bot_token": "123:abc",
        "telegram_chat_id": "auto",
        "feishu_app_id": "cli_xxx",
        "feishu_app_secret": "secret",
        "feishu_chat_id": "oc_123",
        "feishu_receive_id_type": "chat_id",
        "run_cd": str(tmp_path),
        "run_check": None,
        "run_max_rounds": 500,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": True,
        "run_planner_mode": "auto",
        "run_plan_mode": "fully-plan",
        "run_resume_last_session": True,
        "run_model_preset": "quality",
        "bus_dir": str(home_dir / "bus"),
        "logs_dir": str(home_dir / "logs"),
    }
    cmd = codexloop.build_daemon_command(config=config, home_dir=home_dir, token_lock_dir="/tmp/token-locks")
    assert "--feishu-app-id" in cmd
    assert "--feishu-app-secret" in cmd
    assert "--feishu-chat-id" in cmd
    assert "--feishu-receive-id-type" in cmd


def test_stop_all_codexloop_loops_workspace_only_stops_current_home(monkeypatch, tmp_path: Path, capsys) -> None:
    home_dir = tmp_path / ".argusbot"
    calls: list[str] = []

    def fake_stop_current_home_daemon(*, home_dir: Path, config: dict | None) -> bool:
        _ = home_dir
        _ = config
        calls.append("home")
        return True

    def fail_stop_global_daemons_from_token_locks(*, token_lock_dir: str) -> list[int]:
        _ = token_lock_dir
        raise AssertionError("global stop should not be called for workspace-isolated init")

    monkeypatch.setattr(codexloop, "stop_current_home_daemon", fake_stop_current_home_daemon)
    monkeypatch.setattr(codexloop, "stop_global_daemons_from_token_locks", fail_stop_global_daemons_from_token_locks)

    codexloop.stop_all_codexloop_loops(home_dir=home_dir, config=None, token_lock_dir="/tmp/token-locks")
    captured = capsys.readouterr()
    assert calls == ["home"]
    assert "Stopped 1 ArgusBot daemon process." in captured.out

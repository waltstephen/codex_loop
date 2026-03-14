import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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


def test_prompt_channel_choice_retries(monkeypatch) -> None:
    answers = iter(["9", "2"])
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: next(answers))
    assert setup_wizard.prompt_channel_choice() == setup_wizard.CHANNEL_FEISHU


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


def test_resolve_effective_chat_id_reuses_home_config_after_conflict(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    (home_dir / "daemon_config.json").write_text(
        json.dumps({"telegram_chat_id": "8533505134"}),
        encoding="utf-8",
    )

    def fake_resolve_chat_id(**kwargs):
        kwargs["on_error"](
            'getUpdates HTTP 409: {"ok":false,"error_code":409,"description":"Conflict: terminated by other getUpdates request"}'
        )
        return None

    monkeypatch.setattr(setup_wizard, "resolve_chat_id", fake_resolve_chat_id)
    assert setup_wizard.resolve_effective_chat_id(
        bot_token="123:abc",
        requested_chat_id="auto",
        timeout_seconds=5,
        home_dir=home_dir,
        token_lock_dir=str(tmp_path / "locks"),
    ) == "8533505134"


def test_resolve_effective_chat_id_reuses_matching_token_lock_meta(monkeypatch, tmp_path: Path) -> None:
    lock_dir = tmp_path / "locks"
    lock_dir.mkdir()
    token = "123:abc"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]
    (lock_dir / f"{digest}.json").write_text(
        json.dumps({"chat_id": "8533505134"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(setup_wizard, "resolve_chat_id", lambda **kwargs: None)
    assert setup_wizard.resolve_effective_chat_id(
        bot_token=token,
        requested_chat_id="auto",
        timeout_seconds=5,
        home_dir=tmp_path / "missing-home",
        token_lock_dir=str(lock_dir),
    ) == "8533505134"


def test_resolve_effective_chat_id_raises_when_auto_resolution_has_no_fallback(monkeypatch, tmp_path: Path) -> None:
    def fake_resolve_chat_id(**kwargs):
        kwargs["on_error"](
            'getUpdates HTTP 409: {"ok":false,"error_code":409,"description":"Conflict: terminated by other getUpdates request"}'
        )
        return None

    monkeypatch.setattr(setup_wizard, "resolve_chat_id", fake_resolve_chat_id)
    with pytest.raises(SystemExit) as excinfo:
        setup_wizard.resolve_effective_chat_id(
            bot_token="123:abc",
            requested_chat_id="auto",
            timeout_seconds=5,
            home_dir=tmp_path / "missing-home",
            token_lock_dir=str(tmp_path / "locks"),
        )
    assert excinfo.value.code == 2


def test_main_stops_existing_daemon_before_resolving_auto_chat_id(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "custom-home"
    run_cd = tmp_path / "repo"
    run_cd.mkdir()
    args = SimpleNamespace(
        run_cd=str(run_cd),
        home_dir=str(home_dir),
        run_max_rounds=50,
        run_skip_git_repo_check=False,
        run_full_auto=False,
        run_yolo=True,
        run_resume_last_session=True,
        run_planner_mode="auto",
        run_model_preset="cheap",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        token_lock_dir=str(tmp_path / "locks"),
        restart_existing=True,
        follow_up_auto_execute_seconds=600,
    )

    class _FakeParser:
        def parse_args(self):
            return args

    class _FakeLock:
        def release(self) -> None:
            return None

    class _FakeProcess:
        pid = 4321

        def poll(self):
            return None

    order: list[str] = []

    monkeypatch.setattr(setup_wizard, "build_parser", lambda: _FakeParser())
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: "codex" if name == "codex" else None)
    monkeypatch.setattr(setup_wizard, "check_codex_binary", lambda codex_bin: True)
    monkeypatch.setattr(setup_wizard, "check_codex_auth", lambda **kwargs: True)
    monkeypatch.setattr(setup_wizard, "prompt_secret", lambda prompt: "123456:ABCDEFGHIJK")
    monkeypatch.setattr(
        setup_wizard,
        "prompt_input",
        lambda prompt, default: "auto" if "chat id" in prompt else default,
    )
    monkeypatch.setattr(
        setup_wizard,
        "stop_existing_daemon",
        lambda **kwargs: order.append("stop_existing_daemon"),
    )
    monkeypatch.setattr(
        setup_wizard,
        "resolve_effective_chat_id",
        lambda **kwargs: order.append("resolve_effective_chat_id") or "42",
    )
    monkeypatch.setattr(setup_wizard, "acquire_token_lock", lambda **kwargs: _FakeLock())
    monkeypatch.setattr(setup_wizard, "resolve_daemon_launch_prefix", lambda: ["argusbot-daemon"])
    monkeypatch.setattr(setup_wizard.subprocess, "Popen", lambda *args, **kwargs: _FakeProcess())

    setup_wizard.main()

    assert order[:2] == ["stop_existing_daemon", "resolve_effective_chat_id"]


def test_main_feishu_only_skips_telegram_setup(monkeypatch, tmp_path: Path) -> None:
    home_dir = tmp_path / "custom-home"
    run_cd = tmp_path / "repo"
    run_cd.mkdir()
    args = SimpleNamespace(
        channel="feishu",
        telegram_bot_token=None,
        telegram_chat_id=None,
        feishu_app_id="cli_xxx",
        feishu_app_secret="secret",
        feishu_chat_id="oc_123",
        feishu_receive_id_type="chat_id",
        run_cd=str(run_cd),
        home_dir=str(home_dir),
        run_max_rounds=50,
        run_skip_git_repo_check=False,
        run_full_auto=False,
        run_yolo=True,
        run_resume_last_session=True,
        run_planner_mode="auto",
        run_model_preset="cheap",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        token_lock_dir=str(tmp_path / "locks"),
        restart_existing=False,
        follow_up_auto_execute_seconds=600,
    )

    class _FakeParser:
        def parse_args(self):
            return args

    class _FakeProcess:
        pid = 4321

        def poll(self):
            return None

    launched: list[list[str]] = []

    monkeypatch.setattr(setup_wizard, "build_parser", lambda: _FakeParser())
    monkeypatch.setattr(setup_wizard.shutil, "which", lambda name: "codex" if name == "codex" else None)
    monkeypatch.setattr(setup_wizard, "check_codex_binary", lambda codex_bin: True)
    monkeypatch.setattr(setup_wizard, "check_codex_auth", lambda **kwargs: True)
    monkeypatch.setattr(setup_wizard, "resolve_effective_chat_id", lambda **kwargs: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(setup_wizard, "acquire_token_lock", lambda **kwargs: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(setup_wizard, "prompt_secret", lambda prompt: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(setup_wizard, "prompt_input", lambda prompt, default: default)
    monkeypatch.setattr(setup_wizard, "resolve_daemon_launch_prefix", lambda: ["argusbot-daemon"])
    monkeypatch.setattr(
        setup_wizard.subprocess,
        "Popen",
        lambda cmd, **kwargs: launched.append(cmd) or _FakeProcess(),
    )

    setup_wizard.main()

    assert launched
    daemon_cmd = launched[0]
    assert "--telegram-bot-token" not in daemon_cmd
    assert "--telegram-chat-id" not in daemon_cmd
    assert "--feishu-app-id" in daemon_cmd
    payload = json.loads((home_dir / "daemon_config.json").read_text(encoding="utf-8"))
    assert payload["control_channel"] == "feishu"
    assert payload["telegram_bot_token"] is None
    assert payload["feishu_app_id"] == "cli_xxx"


def test_build_parser_accepts_feishu_options() -> None:
    args = setup_wizard.build_parser().parse_args(
        [
            "--channel",
            "feishu",
            "--feishu-app-id",
            "cli_xxx",
            "--feishu-app-secret",
            "secret",
            "--feishu-chat-id",
            "oc_123",
        ]
    )
    assert args.channel == "feishu"
    assert args.feishu_app_id == "cli_xxx"
    assert args.feishu_chat_id == "oc_123"

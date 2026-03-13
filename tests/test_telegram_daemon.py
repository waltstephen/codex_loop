import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from codex_autoloop.apps.daemon_app import (
    TelegramDaemonApp,
    consume_force_new_session_next_run,
    read_force_new_session_next_run,
    write_force_new_session_next_run,
)
from codex_autoloop.telegram_daemon import build_child_command, resolve_saved_session_id


def test_build_child_command_includes_core_args() -> None:
    args = Namespace(
        codex_autoloop_bin="codex-autoloop",
        run_max_rounds=8,
        run_model_preset="quality",
        run_plan_mode="auto",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        run_plan_model=None,
        run_plan_reasoning_effort=None,
        telegram_bot_token="123:abc",
        telegram_control_whisper=True,
        telegram_control_whisper_api_key=None,
        telegram_control_whisper_model="whisper-1",
        telegram_control_whisper_base_url="https://api.openai.com/v1",
        telegram_control_whisper_timeout_seconds=90,
        run_skip_git_repo_check=True,
        run_full_auto=False,
        run_yolo=True,
        run_check=["pytest -q", "python -m compileall ."],
        run_stall_soft_idle_seconds=1200,
        run_stall_hard_idle_seconds=10800,
        run_state_file=".codex_daemon/last_state.json",
        run_telegram_events="loop.started,round.main.completed,round.review.completed,plan.completed,loop.completed",
        run_telegram_live_updates=True,
        run_telegram_live_interval_seconds=5,
        run_resume_last_session=True,
        run_no_dashboard=True,
    )
    cmd = build_child_command(
        args=args,
        objective="do work",
        chat_id="42",
        control_file="/tmp/control.jsonl",
        operator_messages_file="/tmp/operator_messages.md",
        main_prompt_file="/tmp/main_prompt.md",
        plan_overview_file="/tmp/plan_overview.md",
        review_summaries_dir="/tmp/reviews",
        resume_session_id="thread123",
    )
    assert cmd[0] == "codex-autoloop"
    assert "--telegram-bot-token" in cmd
    assert "--telegram-chat-id" in cmd
    assert "--control-file" in cmd
    assert "--operator-messages-file" in cmd
    assert "--main-prompt-file" in cmd
    assert "--plan-overview-file" in cmd
    assert "--review-summaries-dir" in cmd
    assert "--plan-mode" in cmd
    assert "--main-model" in cmd
    assert "--main-reasoning-effort" in cmd
    assert "--reviewer-model" in cmd
    assert "--reviewer-reasoning-effort" in cmd
    assert "--plan-model" in cmd
    assert "--plan-reasoning-effort" in cmd
    assert "--session-id" in cmd
    assert "--check" in cmd
    assert "--yolo" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--no-dashboard" in cmd
    assert "--telegram-control-whisper" in cmd
    assert "--no-telegram-control" in cmd
    assert "--telegram-live-updates" in cmd
    assert "--telegram-live-interval-seconds" in cmd
    assert "--telegram-events" in cmd
    assert "--telegram-control-whisper-model" in cmd
    assert cmd[-1] == "do work"


def test_resolve_saved_session_id(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    state_file.write_text(json.dumps({"session_id": "thread-abc"}), encoding="utf-8")
    assert resolve_saved_session_id(str(state_file)) == "thread-abc"


def test_force_new_session_flag_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "next_run_new_session.flag"
    assert read_force_new_session_next_run(path) is False
    write_force_new_session_next_run(path, True)
    assert read_force_new_session_next_run(path) is True
    assert consume_force_new_session_next_run(path) is True
    assert read_force_new_session_next_run(path) is False


def test_send_reply_logs_failure_when_telegram_send_fails() -> None:
    app = TelegramDaemonApp.__new__(TelegramDaemonApp)
    app.notifier = SimpleNamespace(send_message=lambda message: False)
    events: list[tuple[str, dict]] = []
    app._log_event = lambda event_type, **kwargs: events.append((event_type, kwargs))
    app._send_reply("telegram", "[btw] answer")
    assert events == [("reply.failed", {"source": "telegram", "message": "[btw] answer"})]

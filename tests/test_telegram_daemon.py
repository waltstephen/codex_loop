import json
from argparse import Namespace
from pathlib import Path

from codex_autoloop.telegram_daemon import build_child_command, resolve_plan_follow_up, resolve_saved_session_id


def test_build_child_command_includes_core_args() -> None:
    args = Namespace(
        codex_autoloop_bin="codex-autoloop",
        run_max_rounds=8,
        run_model_preset="quality",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        run_planner_model="gpt-5.4",
        run_planner_reasoning_effort="high",
        run_planner=True,
        run_plan_update_interval_seconds=1800,
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
        run_resume_last_session=True,
        run_no_dashboard=True,
    )
    cmd = build_child_command(
        args=args,
        objective="do work",
        chat_id="42",
        control_file="/tmp/control.jsonl",
        operator_messages_file="/tmp/operator_messages.md",
        plan_report_file="/tmp/plan.md",
        resume_session_id="thread123",
    )
    assert cmd[0] == "codex-autoloop"
    assert "--telegram-bot-token" in cmd
    assert "--telegram-chat-id" in cmd
    assert "--control-file" in cmd
    assert "--operator-messages-file" in cmd
    assert "--main-model" in cmd
    assert "--main-reasoning-effort" in cmd
    assert "--reviewer-model" in cmd
    assert "--reviewer-reasoning-effort" in cmd
    assert "--planner-model" in cmd
    assert "--planner-reasoning-effort" in cmd
    assert "--planner" in cmd
    assert "--plan-report-file" in cmd
    assert "--plan-update-interval-seconds" in cmd
    assert "--session-id" in cmd
    assert "--check" in cmd
    assert "--yolo" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--no-dashboard" in cmd
    assert "--telegram-control-whisper" in cmd
    assert "--telegram-control-whisper-model" in cmd
    assert cmd[-1] == "do work"


def test_resolve_saved_session_id(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    state_file.write_text(json.dumps({"session_id": "thread-abc"}), encoding="utf-8")
    assert resolve_saved_session_id(str(state_file)) == "thread-abc"


def test_resolve_plan_follow_up(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    report_file = tmp_path / "plan.md"
    report_file.write_text("# Planning Snapshot\nnext", encoding="utf-8")
    state_file.write_text(
        json.dumps(
            {
                "plan": {
                    "plan_id": "plan-123",
                    "suggested_next_objective": "benchmark pipeline",
                    "should_propose_follow_up": True,
                    "report_markdown": "# fallback",
                }
            }
        ),
        encoding="utf-8",
    )
    follow_up = resolve_plan_follow_up(str(state_file), report_file)
    assert follow_up is not None
    assert follow_up.plan_id == "plan-123"
    assert follow_up.objective == "benchmark pipeline"
    assert "Planning Snapshot" in follow_up.report_markdown

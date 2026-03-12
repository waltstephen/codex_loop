import json
import datetime as dt
from argparse import Namespace
from pathlib import Path

from codex_autoloop.telegram_daemon import (
    PLAN_MODE_FULLY_PLAN,
    append_plan_record_row,
    build_child_command,
    build_plan_request,
    format_status,
    normalize_plan_mode,
    resolve_last_session_id_from_archive,
    resolve_resume_session_id,
    resolve_saved_session_id,
)


def test_build_child_command_includes_core_args() -> None:
    args = Namespace(
        codex_autoloop_bin="codex-autoloop",
        run_max_rounds=8,
        run_model_preset="quality",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
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


def test_resolve_last_session_id_from_archive_prefers_latest_finished_row(tmp_path: Path) -> None:
    archive_file = tmp_path / "codexloop-run-archive.jsonl"
    rows = [
        {"event": "run.started", "resume_session_id": "thread-old"},
        {"event": "run.finished", "session_id": "thread-new"},
    ]
    with archive_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    assert resolve_last_session_id_from_archive(archive_file) == "thread-new"


def test_resolve_resume_session_id_falls_back_to_archive(tmp_path: Path) -> None:
    archive_file = tmp_path / "codexloop-run-archive.jsonl"
    archive_file.write_text(json.dumps({"session_id": "thread-archive"}) + "\n", encoding="utf-8")
    assert resolve_resume_session_id(str(tmp_path / "missing-state.json"), archive_file) == "thread-archive"


def test_resolve_resume_session_id_prefers_state_over_archive(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    archive_file = tmp_path / "codexloop-run-archive.jsonl"
    state_file.write_text(json.dumps({"session_id": "thread-state"}), encoding="utf-8")
    archive_file.write_text(json.dumps({"session_id": "thread-archive"}) + "\n", encoding="utf-8")
    assert resolve_resume_session_id(str(state_file), archive_file) == "thread-state"


def test_normalize_plan_mode_defaults_to_fully_plan() -> None:
    assert normalize_plan_mode(None) == PLAN_MODE_FULLY_PLAN
    assert normalize_plan_mode("unknown") == PLAN_MODE_FULLY_PLAN
    assert normalize_plan_mode("execute-only") == "execute-only"


def test_build_plan_request_uses_review_guidance() -> None:
    state_payload = {
        "rounds": [
            {
                "review": {
                    "status": "continue",
                    "reason": "tests still failing",
                    "next_action": "fix failing tests and rerun pytest",
                }
            }
        ]
    }
    request = build_plan_request(objective="完成接口重构", exit_code=2, state_payload=state_payload)
    assert "完成接口重构" in request
    assert "fix failing tests" in request
    assert "失败原因" in request


def test_append_plan_record_row_writes_markdown_table(tmp_path: Path) -> None:
    record = tmp_path / "plan-records.md"
    state_payload = {"session_id": "thread-1", "rounds": [{"review": {"status": "continue", "reason": "x"}}]}
    append_plan_record_row(
        path=record,
        finished_at=dt.datetime(2026, 1, 1, 0, 0, 0),
        objective="do work",
        exit_code=0,
        state_payload=state_payload,
        log_path=tmp_path / "run.log",
    )
    text = record.read_text(encoding="utf-8")
    assert "| finished_at | objective | exit_code |" in text
    assert "do work" in text
    assert "thread-1" in text


def test_format_status_includes_plan_fields_when_idle() -> None:
    rendered = format_status(
        child=None,
        child_objective=None,
        child_log_path=None,
        child_started_at=None,
        last_session_id="thread-1",
        plan_mode="fully-plan",
        pending_plan_request="继续推进目标",
        pending_plan_auto_execute_at=dt.datetime(2026, 1, 1, 0, 10, 0),
        scheduled_plan_request_at=dt.datetime(2026, 1, 1, 0, 0, 0),
    )
    assert "plan_mode=fully-plan" in rendered
    assert "pending_plan_request=继续推进目标" in rendered
    assert "plan_auto_execute_at=" in rendered

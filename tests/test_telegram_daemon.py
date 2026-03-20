import json
import datetime as dt
from argparse import Namespace
from pathlib import Path

from codex_autoloop.telegram_daemon import (
    append_plan_record_row,
    build_plan_skip_message,
    build_session_plan_confirmation_required_message,
    build_parser,
    build_child_command,
    build_plan_request,
    extract_suggested_next_objective_from_markdown,
    extract_latest_review,
    extract_latest_review_status,
    format_external_message,
    format_status,
    find_matching_autoloop_child_pids,
    is_force_fresh_session_requested,
    looks_like_feishu_chat_id,
    log_contains_invalid_encrypted_content,
    normalize_plan_mode,
    parse_process_table,
    resolve_last_session_id_from_archive,
    resolve_autoloop_command,
    resolve_resume_session_id,
    resolve_saved_session_id,
    sanitize_follow_up_objective,
    session_plan_goal_is_confirmed,
    should_emit_feishu_heartbeat,
    should_block_for_unconfirmed_session_plan,
    set_force_fresh_session_marker,
    should_schedule_plan_follow_up,
    terminate_process_tree,
    wait_for_process_exit,
)


def test_build_child_command_includes_core_args() -> None:
    args = Namespace(
        codex_autoloop_bin="argusbot-run",
        run_max_rounds=8,
        run_runner_backend="claude",
        run_runner_bin="/opt/homebrew/bin/claude",
        run_model_preset="quality",
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        run_planner_mode="auto",
        run_planner_model="gpt-5.4",
        run_planner_reasoning_effort="high",
        run_planner=True,
        run_plan_update_interval_seconds=1800,
        follow_up_auto_execute_seconds=3600,
        telegram_bot_token="123:abc",
        feishu_app_id=None,
        feishu_app_secret=None,
        feishu_chat_id=None,
        feishu_receive_id_type="chat_id",
        feishu_timeout_seconds=10,
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
        run_state_file=".argusbot/last_state.json",
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
        plan_todo_file="/tmp/todo.md",
        resume_session_id="thread123",
    )
    assert cmd[0] == "argusbot-run"
    assert "--telegram-bot-token" in cmd
    assert "--telegram-chat-id" in cmd
    assert "--no-telegram-control" in cmd
    assert "--control-file" in cmd
    assert "--operator-messages-file" in cmd
    assert "--main-model" in cmd
    assert "--main-reasoning-effort" in cmd
    assert "--reviewer-model" in cmd
    assert "--reviewer-reasoning-effort" in cmd
    assert "--planner-model" in cmd
    assert "--planner-reasoning-effort" in cmd
    assert "--planner" in cmd
    assert "--planner-mode" in cmd
    assert "--plan-report-file" in cmd
    assert "--plan-todo-file" in cmd
    assert "--plan-update-interval-seconds" in cmd
    assert "--session-id" in cmd
    assert "--check" in cmd
    assert "--runner-backend" in cmd
    assert "--runner-bin" in cmd
    assert "--yolo" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--no-dashboard" in cmd
    assert "--telegram-control-whisper" in cmd
    assert "--telegram-control-whisper-model" in cmd
    backend_index = cmd.index("--runner-backend")
    assert cmd[backend_index + 1] == "claude"
    runner_bin_index = cmd.index("--runner-bin")
    assert cmd[runner_bin_index + 1] == "/opt/homebrew/bin/claude"
    assert cmd[-1] == "do work"


def test_resolve_autoloop_command_keeps_windows_python_path(monkeypatch) -> None:
    monkeypatch.setattr("codex_autoloop.telegram_daemon.os.name", "nt")
    parts = resolve_autoloop_command(r'C:\Users\wen25\codex_loop\.venv\Scripts\python.exe -m codex_autoloop.cli')
    assert parts == [
        r"C:\Users\wen25\codex_loop\.venv\Scripts\python.exe",
        "-m",
        "codex_autoloop.cli",
    ]


def test_build_child_command_keeps_windows_python_path(monkeypatch) -> None:
    monkeypatch.setattr("codex_autoloop.telegram_daemon.os.name", "nt")
    args = Namespace(
        codex_autoloop_bin=r"C:\Users\wen25\codex_loop\.venv\Scripts\python.exe -m codex_autoloop.cli",
        run_max_rounds=8,
        run_model_preset=None,
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        run_planner_mode="auto",
        run_planner_model=None,
        run_planner_reasoning_effort=None,
        run_planner=True,
        run_plan_update_interval_seconds=1800,
        follow_up_auto_execute_seconds=3600,
        telegram_bot_token="123:abc",
        feishu_app_id=None,
        feishu_app_secret=None,
        feishu_chat_id=None,
        feishu_receive_id_type="chat_id",
        feishu_timeout_seconds=10,
        telegram_control_whisper=True,
        telegram_control_whisper_api_key=None,
        telegram_control_whisper_model="whisper-1",
        telegram_control_whisper_base_url="https://api.openai.com/v1",
        telegram_control_whisper_timeout_seconds=90,
        run_skip_git_repo_check=False,
        run_full_auto=False,
        run_yolo=True,
        run_check=[],
        run_stall_soft_idle_seconds=1200,
        run_stall_hard_idle_seconds=10800,
        run_state_file=".argusbot/last_state.json",
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
        plan_todo_file="/tmp/todo.md",
        resume_session_id=None,
    )
    assert cmd[:3] == [
        r"C:\Users\wen25\codex_loop\.venv\Scripts\python.exe",
        "-m",
        "codex_autoloop.cli",
    ]


def test_parse_process_table_parses_pid_ppid_and_args() -> None:
    rows = parse_process_table(
        "3103351 1 python -m codex_autoloop.cli --state-file /tmp/a.json\n"
        "3349866 1 argusbot-daemon --run-state-file /tmp/a.json\n"
    )
    assert rows == [
        (3103351, 1, "python -m codex_autoloop.cli --state-file /tmp/a.json"),
        (3349866, 1, "argusbot-daemon --run-state-file /tmp/a.json"),
    ]


def test_find_matching_autoloop_child_pids_filters_to_same_state_file(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    other_state_file = tmp_path / "other_state.json"
    process_table = [
        (3103351, 1, f"python -m codex_autoloop.cli --state-file {state_file} objective"),
        (3349866, 1, f"argusbot-daemon --run-state-file {state_file}"),
        (445566, 1, f"python -m codex_autoloop.cli --state-file {other_state_file} objective"),
    ]
    matches = find_matching_autoloop_child_pids(
        process_table=process_table,
        state_file=str(state_file),
        current_pid=3349866,
    )
    assert matches == [3103351]


def test_build_child_command_includes_feishu_args_when_configured() -> None:
    args = Namespace(
        codex_autoloop_bin="argusbot-run",
        run_max_rounds=8,
        run_model_preset=None,
        run_main_model=None,
        run_main_reasoning_effort=None,
        run_reviewer_model=None,
        run_reviewer_reasoning_effort=None,
        run_planner_mode="auto",
        run_planner_model=None,
        run_planner_reasoning_effort=None,
        run_planner=True,
        run_plan_update_interval_seconds=1800,
        follow_up_auto_execute_seconds=3600,
        telegram_bot_token=None,
        feishu_app_id="cli_xxx",
        feishu_app_secret="secret",
        feishu_chat_id="oc_123",
        feishu_receive_id_type="chat_id",
        feishu_timeout_seconds=12,
        telegram_control_whisper=True,
        telegram_control_whisper_api_key=None,
        telegram_control_whisper_model="whisper-1",
        telegram_control_whisper_base_url="https://api.openai.com/v1",
        telegram_control_whisper_timeout_seconds=90,
        run_skip_git_repo_check=False,
        run_full_auto=False,
        run_yolo=True,
        run_check=[],
        run_stall_soft_idle_seconds=1200,
        run_stall_hard_idle_seconds=10800,
        run_state_file=".argusbot/last_state.json",
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
        plan_todo_file="/tmp/todo.md",
        resume_session_id=None,
    )
    assert "--feishu-app-id" in cmd
    assert "--feishu-app-secret" in cmd
    assert "--feishu-chat-id" in cmd
    assert "--feishu-receive-id-type" in cmd
    assert "--feishu-timeout-seconds" in cmd
    assert "--no-feishu-control" in cmd


def test_build_child_command_includes_copilot_proxy_args() -> None:
    args = Namespace(
        codex_autoloop_bin="argusbot-run",
        run_max_rounds=8,
        run_model_preset=None,
        run_main_model="gpt-5.4",
        run_main_reasoning_effort="high",
        run_reviewer_model="gpt-5.4",
        run_reviewer_reasoning_effort="high",
        run_planner_mode="auto",
        run_planner_model="gpt-5.4",
        run_planner_reasoning_effort="high",
        run_planner=True,
        run_copilot_proxy=True,
        run_copilot_proxy_dir="/home/v-boxiuli/copilot-proxy",
        run_copilot_proxy_port=18080,
        run_plan_update_interval_seconds=1800,
        follow_up_auto_execute_seconds=3600,
        telegram_bot_token="123:abc",
        feishu_app_id=None,
        feishu_app_secret=None,
        feishu_chat_id=None,
        feishu_receive_id_type="chat_id",
        feishu_timeout_seconds=10,
        telegram_control_whisper=True,
        telegram_control_whisper_api_key=None,
        telegram_control_whisper_model="whisper-1",
        telegram_control_whisper_base_url="https://api.openai.com/v1",
        telegram_control_whisper_timeout_seconds=90,
        run_skip_git_repo_check=False,
        run_full_auto=False,
        run_yolo=True,
        run_check=[],
        run_stall_soft_idle_seconds=1200,
        run_stall_hard_idle_seconds=10800,
        run_state_file=".argusbot/last_state.json",
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
        plan_todo_file="/tmp/todo.md",
        resume_session_id=None,
    )
    assert "--copilot-proxy" in cmd
    assert "--copilot-proxy-dir" in cmd
    assert "/home/v-boxiuli/copilot-proxy" in cmd
    assert "--copilot-proxy-port" in cmd


def test_resolve_saved_session_id(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    state_file.write_text(json.dumps({"session_id": "thread-abc"}), encoding="utf-8")
    assert resolve_saved_session_id(str(state_file)) == "thread-abc"


def test_resolve_last_session_id_from_archive_prefers_latest_finished_row(tmp_path: Path) -> None:
    archive_file = tmp_path / "argusbot-run-archive.jsonl"
    rows = [
        {"event": "run.started", "resume_session_id": "thread-old"},
        {"event": "run.finished", "session_id": "thread-new"},
    ]
    with archive_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    assert resolve_last_session_id_from_archive(archive_file) == "thread-new"


def test_resolve_resume_session_id_falls_back_to_archive(tmp_path: Path) -> None:
    archive_file = tmp_path / "argusbot-run-archive.jsonl"
    archive_file.write_text(json.dumps({"session_id": "thread-archive"}) + "\n", encoding="utf-8")
    assert resolve_resume_session_id(str(tmp_path / "missing-state.json"), archive_file) == "thread-archive"


def test_resolve_resume_session_id_prefers_state_over_archive(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    archive_file = tmp_path / "argusbot-run-archive.jsonl"
    state_file.write_text(json.dumps({"session_id": "thread-state"}), encoding="utf-8")
    archive_file.write_text(json.dumps({"session_id": "thread-archive"}) + "\n", encoding="utf-8")
    assert resolve_resume_session_id(str(state_file), archive_file) == "thread-state"


def test_set_force_fresh_session_marker_blocks_resume(tmp_path: Path) -> None:
    state_file = tmp_path / "last_state.json"
    archive_file = tmp_path / "archive.jsonl"
    state_file.write_text(json.dumps({"session_id": "thread-state"}), encoding="utf-8")
    archive_file.write_text(json.dumps({"session_id": "thread-archive"}) + "\n", encoding="utf-8")
    assert resolve_resume_session_id(str(state_file), archive_file) == "thread-state"
    changed = set_force_fresh_session_marker(str(state_file), enabled=True, reason="test")
    assert changed is True
    assert is_force_fresh_session_requested(str(state_file)) is True
    assert resolve_resume_session_id(str(state_file), archive_file) is None
    set_force_fresh_session_marker(str(state_file), enabled=False)
    assert is_force_fresh_session_requested(str(state_file)) is False
    assert resolve_resume_session_id(str(state_file), archive_file) == "thread-archive"


def test_log_contains_invalid_encrypted_content(tmp_path: Path) -> None:
    log_file = tmp_path / "run.log"
    log_file.write_text("some error: Invalid Encrypted Content happened\n", encoding="utf-8")
    assert log_contains_invalid_encrypted_content(log_file) is True
    other_log = tmp_path / "ok.log"
    other_log.write_text("normal output\n", encoding="utf-8")
    assert log_contains_invalid_encrypted_content(other_log) is False


def test_normalize_plan_mode_defaults_to_fully_plan() -> None:
    assert normalize_plan_mode(None) == "execute-only"
    assert normalize_plan_mode("unknown") == "execute-only"
    assert normalize_plan_mode("execute-only") == "execute-only"


def test_session_plan_goal_is_confirmed_accepts_pending_or_active_goal() -> None:
    assert (
        session_plan_goal_is_confirmed(
            pending_session_plan_goal=None,
            active_session_plan_goal=None,
        )
        is False
    )
    assert (
        session_plan_goal_is_confirmed(
            pending_session_plan_goal="ship the full session objective",
            active_session_plan_goal=None,
        )
        is True
    )
    assert (
        session_plan_goal_is_confirmed(
            pending_session_plan_goal=None,
            active_session_plan_goal="continue the same session objective",
        )
        is True
    )


def test_should_block_for_unconfirmed_session_plan_blocks_task_commands_only() -> None:
    assert (
        should_block_for_unconfirmed_session_plan(
            planner_mode="auto",
            command_kind="run",
            pending_session_plan_goal=None,
            active_session_plan_goal=None,
        )
        is True
    )
    assert (
        should_block_for_unconfirmed_session_plan(
            planner_mode="auto",
            command_kind="plan",
            pending_session_plan_goal=None,
            active_session_plan_goal=None,
        )
        is False
    )
    assert (
        should_block_for_unconfirmed_session_plan(
            planner_mode="record",
            command_kind="run",
            pending_session_plan_goal=None,
            active_session_plan_goal=None,
        )
        is False
    )


def test_build_session_plan_confirmation_required_message_mentions_plan_and_session_goal() -> None:
    message = build_session_plan_confirmation_required_message()
    assert "/plan" in message
    assert "session goal" in message.lower()
    assert "本 session 总目标" in message


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
    assert "目标上下文：完成接口重构" in request
    assert "fix failing tests" in request


def test_format_external_message_returns_trimmed_text_without_buttons() -> None:
    assert format_external_message("  [daemon] online  ") == "[daemon] online"


def test_format_external_message_appends_inline_button_labels() -> None:
    rendered = format_external_message(
        "[daemon] suggested next session",
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "Execute Next Step", "callback_data": "plan_run:123"},
                    {"text": "Reject Plan", "callback_data": "plan_reject:123"},
                ],
                [{"text": "Modify Then Execute", "callback_data": "plan_modify:123"}],
            ]
        },
    )
    assert "Telegram inline buttons are unavailable here" in rendered
    assert "- Execute Next Step" in rendered
    assert "- Reject Plan" in rendered
    assert "- Modify Then Execute" in rendered


def test_looks_like_feishu_chat_id_requires_oc_prefix_for_chat_id() -> None:
    assert looks_like_feishu_chat_id("oc_123") is True
    assert looks_like_feishu_chat_id("11") is False
    assert looks_like_feishu_chat_id("ou_xxx", receive_id_type="open_id") is True


def test_extract_latest_review_supports_legacy_flat_fields() -> None:
    state_payload = {
        "rounds": [
            {
                "review_status": "blocked",
                "review_reason": "missing data",
                "review_next_action": "restore /blob assets",
            }
        ]
    }
    status, reason, next_action = extract_latest_review(state_payload)
    assert status == "blocked"
    assert reason == "missing data"
    assert next_action == "restore /blob assets"


def test_extract_latest_review_status_prefers_top_level_field() -> None:
    state_payload = {
        "latest_review_status": "BLOCKED",
        "rounds": [{"review": {"status": "continue"}}],
    }
    assert extract_latest_review_status(state_payload) == "blocked"


def test_should_schedule_plan_follow_up_skips_on_failed_exit() -> None:
    should_schedule, reason = should_schedule_plan_follow_up(
        exit_code=2,
        state_payload=None,
        session_goal_confirmed=True,
    )
    assert should_schedule is False
    assert reason == "last_run_failed"


def test_should_schedule_plan_follow_up_skips_on_blocked_review() -> None:
    state_payload = {"latest_review_status": "blocked"}
    should_schedule, reason = should_schedule_plan_follow_up(
        exit_code=0,
        state_payload=state_payload,
        session_goal_confirmed=True,
    )
    assert should_schedule is False
    assert reason == "review_blocked"


def test_should_schedule_plan_follow_up_skips_when_session_goal_unconfirmed() -> None:
    state_payload = {"latest_review_status": "done"}
    should_schedule, reason = should_schedule_plan_follow_up(
        exit_code=0,
        state_payload=state_payload,
        session_goal_confirmed=False,
    )
    assert should_schedule is False
    assert reason == "session_goal_unconfirmed"


def test_should_schedule_plan_follow_up_skips_when_latest_plan_has_no_follow_up() -> None:
    state_payload = {
        "latest_review_status": "done",
        "latest_plan": {
            "follow_up_required": False,
            "main_instruction": "do not run",
        },
    }
    should_schedule, reason = should_schedule_plan_follow_up(
        exit_code=0,
        state_payload=state_payload,
        session_goal_confirmed=True,
    )
    assert should_schedule is False
    assert reason == "planner_no_follow_up"


def test_build_plan_skip_message_explains_unconfirmed_session_goal() -> None:
    message = build_plan_skip_message(skip_reason="session_goal_unconfirmed", state_payload=None)
    assert "/plan" in message
    assert "session-level goal" in message


def test_build_plan_skip_message_explains_planner_no_follow_up() -> None:
    message = build_plan_skip_message(
        skip_reason="planner_no_follow_up",
        state_payload={
            "latest_plan": {
                "follow_up_required": False,
                "main_instruction": "Wait for a new objective before starting further planning or execution.",
            }
        },
    )
    assert "Planner did not propose a follow-up objective." in message
    assert "Wait for a new objective before starting further planning or execution." in message
    assert "fix blockers" not in message.lower()


def test_build_plan_skip_message_explains_failed_run() -> None:
    message = build_plan_skip_message(skip_reason="last_run_failed", state_payload=None)
    assert "previous run exited non-zero" in message


def test_build_plan_request_prefers_planner_report_when_no_next_action(tmp_path: Path) -> None:
    report = tmp_path / "plan-report.md"
    report.write_text(
        "# Planning Snapshot\n\n"
        "## Suggested Next Objective\n"
        "实现 GUI 高层 planner 与 computer-use 执行层的联动验证。\n\n"
        "## Reviewer\n"
        "- Status: continue\n",
        encoding="utf-8",
    )
    state_payload = {
        "rounds": [
            {
                "review": {
                    "status": "continue",
                    "reason": "still pending",
                    "next_action": "",
                }
            }
        ]
    }
    request = build_plan_request(
        objective="旧目标",
        exit_code=0,
        state_payload=state_payload,
        planner_report_path=report,
    )
    assert request == "实现 GUI 高层 planner 与 computer-use 执行层的联动验证。"


def test_build_plan_request_prefers_latest_plan_main_instruction() -> None:
    state_payload = {
        "rounds": [
            {
                "review": {
                    "status": "done",
                    "reason": "done",
                    "next_action": "send the user a concise completion summary",
                }
            }
        ],
        "latest_plan": {
            "follow_up_required": True,
            "main_instruction": "在 MONET hard-4 上复现 step_0020 与 step_0030 的对照实验并输出误差分析。",
        },
    }
    request = build_plan_request(
        objective="旧目标",
        exit_code=0,
        state_payload=state_payload,
    )
    assert request == "在 MONET hard-4 上复现 step_0020 与 step_0030 的对照实验并输出误差分析。"


def test_extract_suggested_next_objective_from_markdown_none_when_placeholder() -> None:
    text = (
        "# Planning Snapshot\n"
        "## Suggested Next Objective\n"
        "No follow-up objective proposed yet.\n"
        "## Acceptance Checks\n"
    )
    assert extract_suggested_next_objective_from_markdown(text) is None


def test_sanitize_follow_up_objective_removes_run_prefixes() -> None:
    assert sanitize_follow_up_objective("run /run 继续修复") == "继续修复"
    assert sanitize_follow_up_objective("/run 继续修复") == "继续修复"


def test_sanitize_follow_up_objective_removes_objective_context_suffix() -> None:
    text = "Stop the autoloop and wait for the user's next instruction.（目标上下文：旧目标文本）"
    assert sanitize_follow_up_objective(text) == "Stop the autoloop and wait for the user's next instruction."


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
        plan_mode="auto",
        default_planner_mode="auto",
        pending_plan_request="继续推进目标",
        pending_plan_auto_execute_at=dt.datetime(2026, 1, 1, 0, 10, 0),
        scheduled_plan_request_at=dt.datetime(2026, 1, 1, 0, 0, 0),
    )
    assert "planner_mode=auto" in rendered
    assert "pending_plan_request=继续推进目标" in rendered
    assert "plan_auto_execute_at=" in rendered


def test_build_parser_default_run_model_preset_is_none() -> None:
    args = build_parser().parse_args(["--telegram-bot-token", "123:abc"])
    assert args.run_model_preset is None


def test_build_parser_accepts_feishu_only_args() -> None:
    args = build_parser().parse_args(
        [
            "--feishu-app-id",
            "cli_xxx",
            "--feishu-app-secret",
            "secret",
            "--feishu-chat-id",
            "oc_123",
        ]
    )
    assert args.telegram_bot_token is None
    assert args.feishu_app_id == "cli_xxx"


def test_build_parser_default_feishu_heartbeat_interval_seconds() -> None:
    args = build_parser().parse_args(["--telegram-bot-token", "123:abc"])
    assert args.feishu_heartbeat_interval_seconds == 600


def test_should_emit_feishu_heartbeat_respects_interval_and_state() -> None:
    assert (
        should_emit_feishu_heartbeat(
            feishu_enabled=True,
            running=True,
            interval_seconds=600,
            now_monotonic=1200,
            last_sent_monotonic=590,
        )
        is True
    )
    assert (
        should_emit_feishu_heartbeat(
            feishu_enabled=True,
            running=True,
            interval_seconds=600,
            now_monotonic=1189,
            last_sent_monotonic=590,
        )
        is False
    )
    assert (
        should_emit_feishu_heartbeat(
            feishu_enabled=False,
            running=True,
            interval_seconds=600,
            now_monotonic=1200,
            last_sent_monotonic=590,
        )
        is False
    )
    assert (
        should_emit_feishu_heartbeat(
            feishu_enabled=True,
            running=False,
            interval_seconds=600,
            now_monotonic=1200,
            last_sent_monotonic=590,
        )
        is False
    )
    assert (
        should_emit_feishu_heartbeat(
            feishu_enabled=True,
            running=True,
            interval_seconds=0,
            now_monotonic=1200,
            last_sent_monotonic=590,
        )
        is False
    )


def test_wait_for_process_exit_detects_exit() -> None:
    class _FakeProcess:
        def __init__(self) -> None:
            self.calls = 0

        def poll(self):
            self.calls += 1
            return None if self.calls == 1 else 0

    assert wait_for_process_exit(_FakeProcess(), timeout_seconds=0.5) is True


def test_terminate_process_tree_uses_taskkill_on_windows(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _FakeProcess:
        pid = 2468

        def __init__(self) -> None:
            self._poll = None

        def poll(self):
            return self._poll

        def wait(self, timeout=None):
            self._poll = 0
            return 0

        def kill(self):
            self._poll = 0

    monkeypatch.setattr("codex_autoloop.telegram_daemon.os.name", "nt")
    monkeypatch.setattr(
        "codex_autoloop.telegram_daemon.subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )

    process = _FakeProcess()
    terminate_process_tree(process)

    assert calls == [["taskkill", "/PID", "2468", "/T", "/F"]]

from codex_autoloop.dashboard import DashboardStore
from codex_autoloop.cli import (
    format_control_status,
    parse_telegram_events,
    resolve_final_report_file,
    resolve_operator_messages_file,
    resolve_plan_report_file,
    resolve_plan_todo_file,
    resolve_pptx_report_file,
)


def test_dashboard_store_state_and_events() -> None:
    store = DashboardStore(objective="test objective")
    store.apply_loop_event({"type": "loop.started", "session_id": "abc", "max_rounds": 3})
    store.apply_loop_event({"type": "round.started", "round_index": 1, "session_id": "abc"})
    store.apply_loop_event(
        {
            "type": "plan.updated",
            "summary": "planner summary",
            "suggested_next_objective": "run next task",
            "report_markdown": "# Planning Snapshot",
        }
    )
    store.add_stream_line("main.stdout", "line1")
    store.apply_loop_event({"type": "loop.completed", "success": True, "stop_reason": "ok"})

    state = store.state_snapshot()
    assert state["status"] == "completed"
    assert state["success"] is True
    assert state["session_id"] == "abc"
    assert state["current_round"] == 1
    assert state["plan_summary"] == "planner summary"
    assert state["plan_next_objective"] == "run next task"

    events = store.events_after(after_id=0, limit=20)
    assert len(events) >= 4
    assert any(item["type"] == "stream.line" for item in events)


def test_parse_telegram_events() -> None:
    parsed = parse_telegram_events("loop.started, round.review.completed , ,loop.completed")
    assert parsed == {"loop.started", "round.review.completed", "loop.completed"}


def test_resolve_operator_messages_file_prefers_explicit() -> None:
    out = resolve_operator_messages_file(
        explicit_path="/tmp/a.md",
        control_file="/tmp/control.jsonl",
        state_file="/tmp/state.json",
    )
    assert out == "/tmp/a.md"


def test_resolve_plan_report_file_prefers_explicit() -> None:
    out = resolve_plan_report_file(
        explicit_path="/tmp/plan.md",
        state_file="/tmp/state.json",
    )
    assert out == "/tmp/plan.md"


def test_resolve_plan_todo_file_prefers_explicit() -> None:
    out = resolve_plan_todo_file(
        explicit_path="/tmp/todo.md",
        state_file="/tmp/state.json",
    )
    assert out == "/tmp/todo.md"


def test_resolve_final_report_file_uses_review_dir() -> None:
    out = resolve_final_report_file(
        explicit_path=None,
        review_summaries_dir="/tmp/reviews",
        operator_messages_file="/tmp/operator_messages.md",
        control_file=None,
        state_file=None,
    )
    assert out == "/tmp/reviews/final-task-report.md"


def test_resolve_pptx_report_file_uses_operator_messages_dir() -> None:
    out = resolve_pptx_report_file(
        explicit_path=None,
        operator_messages_file="/tmp/operator_messages.md",
        control_file=None,
        state_file=None,
    )
    assert out == "/tmp/run-report.pptx"


def test_format_control_status_includes_pptx_report_details() -> None:
    rendered = format_control_status(
        {
            "status": "completed",
            "round": 3,
            "session_id": "thread-1",
            "success": True,
            "stop_reason": "done",
            "plan_mode": "auto",
            "final_report_file": "/tmp/final-task-report.md",
            "final_report_ready": True,
            "pptx_report_file": "/tmp/run-report.pptx",
            "pptx_report_ready": True,
        }
    )

    assert "final_report_file=/tmp/final-task-report.md" in rendered
    assert "final_report_ready=True" in rendered
    assert "pptx_report_file=/tmp/run-report.pptx" in rendered
    assert "pptx_report_ready=True" in rendered

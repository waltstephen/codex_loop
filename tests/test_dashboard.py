from codex_autoloop.dashboard import DashboardStore
from codex_autoloop.cli import (
    parse_telegram_events,
    resolve_operator_messages_file,
    resolve_plan_report_file,
    resolve_plan_todo_file,
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

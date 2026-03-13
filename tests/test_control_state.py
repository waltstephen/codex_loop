from codex_autoloop.control_state import LoopControlState
from codex_autoloop.core.state_store import LoopStateStore
from codex_autoloop.models import PlanDecision, ReviewDecision, RoundSummary


def test_control_state_inject_and_consume() -> None:
    state = LoopControlState()
    state.request_inject("please continue with plan B", source="telegram")
    reason = state.consume_interrupt_reason()
    assert reason is not None
    assert "instruction update" in reason
    assert state.consume_pending_instruction() == "please continue with plan B"
    assert state.consume_pending_instruction() is None


def test_control_state_stop_sets_flag() -> None:
    state = LoopControlState()
    state.request_stop(source="telegram")
    assert state.is_stop_requested() is True
    reason = state.consume_interrupt_reason()
    assert reason is not None
    assert "requested stop" in reason


def test_control_state_records_messages() -> None:
    state = LoopControlState()
    state.record_message(text="initial objective", source="terminal", kind="initial-objective")
    state.request_inject("patch config", source="telegram")
    messages = state.list_messages()
    assert len(messages) == 2
    assert "initial-objective" in messages[0]
    assert "patch config" in messages[1]


def test_control_state_writes_markdown_doc(tmp_path) -> None:
    doc_path = tmp_path / "operator_messages.md"
    state = LoopControlState(operator_messages_file=str(doc_path))
    state.record_message(text="initial goal", source="terminal", kind="initial-objective")
    state.request_inject("fix test", source="telegram")
    content = doc_path.read_text(encoding="utf-8")
    assert "Operator Messages" in content
    assert "initial goal" in content
    assert "fix test" in content


def test_state_store_writes_main_prompt_markdown(tmp_path) -> None:
    prompt_path = tmp_path / "main_prompt.md"
    state = LoopStateStore(objective="ship", main_prompt_file=str(prompt_path), plan_mode="off")
    state.record_main_prompt(round_index=1, phase="initial", prompt="Objective:\nship\n")
    content = prompt_path.read_text(encoding="utf-8")
    assert "# Main Prompt" in content
    assert "Round: `1`" in content
    assert "Phase: `initial`" in content
    assert "Objective:" in content


def test_targeted_messages_respect_audience() -> None:
    state = LoopControlState()
    state.record_message(text="shared", source="terminal", kind="note", audience="broadcast")
    state.request_plan_direction("extend roadmap", source="telegram")
    state.request_review_criteria("strict on tests", source="telegram")
    assert any("shared" in item for item in state.list_messages_for_role("main"))
    assert any("extend roadmap" in item for item in state.list_messages_for_role("plan"))
    assert not any("extend roadmap" in item for item in state.list_messages_for_role("main"))
    assert any("strict on tests" in item for item in state.list_messages_for_role("review"))
    assert not any("strict on tests" in item for item in state.list_messages_for_role("plan"))


def test_plan_mode_can_be_hot_switched() -> None:
    state = LoopStateStore(objective="ship", plan_mode="auto")
    assert state.current_plan_mode() == "auto"
    assert state.request_plan_mode("record", source="telegram") == "record"
    assert state.current_plan_mode() == "record"
    assert state.request_plan_mode("OFF", source="telegram") == "off"
    assert state.current_plan_mode() == "off"
    assert state.request_plan_mode("invalid", source="telegram") is None


def test_state_store_writes_plan_and_review_docs(tmp_path) -> None:
    plan_path = tmp_path / "plan_overview.md"
    review_dir = tmp_path / "reviews"
    state = LoopStateStore(
        objective="ship feature",
        plan_overview_file=str(plan_path),
        review_summaries_dir=str(review_dir),
        plan_mode="auto",
    )
    state.record_plan(
        PlanDecision(
            follow_up_required=True,
            next_explore="inspect failing tests",
            main_instruction="fix the parser",
            review_instruction="verify acceptance checks",
            overview_markdown="## TODO\n- fix parser\n",
        ),
        round_index=0,
        session_id="thread-1",
    )
    round_summary = RoundSummary(
        round_index=1,
        thread_id="thread-1",
        main_exit_code=0,
        main_turn_completed=True,
        main_turn_failed=False,
        checks=[],
        review=ReviewDecision(
            status="done",
            confidence=1.0,
            reason="all checks pass",
            next_action="stop",
            round_summary_markdown="## Review Round\n- parser fixed\n",
            completion_summary_markdown="## Final\n- objective complete\n",
        ),
        main_last_message="DONE",
        plan=PlanDecision(
            follow_up_required=False,
            next_explore="none",
            main_instruction="none",
            review_instruction="none",
            overview_markdown="## Summary\n- complete\n",
        ),
    )
    state.record_round(
        round_summary,
        session_id="thread-1",
        current_review=round_summary.review,
        current_plan=round_summary.plan,
    )
    assert "Runtime Data" in plan_path.read_text(encoding="utf-8")
    assert (review_dir / "round-001.md").exists()
    assert (review_dir / "completion.md").exists()
    assert "Round 1" in (review_dir / "index.md").read_text(encoding="utf-8")


def test_state_store_renders_plan_and_review_context(tmp_path) -> None:
    state = LoopStateStore(
        objective="ship feature",
        operator_messages_file=str(tmp_path / "operator_messages.md"),
        check_commands=["python -m compileall ."],
        plan_mode="auto",
    )
    state.record_message(text="shared context", source="operator", kind="initial-objective", audience="broadcast")
    state.request_plan_direction("focus on data pipeline", source="telegram")
    state.request_review_criteria("must pass compileall", source="telegram")
    state.record_plan(
        PlanDecision(
            follow_up_required=True,
            next_explore="pipeline",
            main_instruction="inspect pipeline",
            review_instruction="validate compileall",
            overview_markdown="## Plan\n- pipeline\n",
        ),
        round_index=0,
        session_id="thread-1",
    )
    review = ReviewDecision(
        status="done",
        confidence=1.0,
        reason="good",
        next_action="stop",
        round_summary_markdown="round",
        completion_summary_markdown="final completion",
    )
    state.record_round(
        RoundSummary(
            round_index=1,
            thread_id="thread-1",
            main_exit_code=0,
            main_turn_completed=True,
            main_turn_failed=False,
            checks=[],
            review=review,
            main_last_message="done",
        ),
        session_id="thread-1",
        current_review=review,
    )
    assert "Plan-Only Directions" in state.render_plan_context_markdown()
    rendered_review = state.render_review_context_markdown()
    assert "Acceptance Checks" in rendered_review
    assert "must pass compileall" in rendered_review

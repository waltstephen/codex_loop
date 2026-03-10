from codex_autoloop.control_state import LoopControlState


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

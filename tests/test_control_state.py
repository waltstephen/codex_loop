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

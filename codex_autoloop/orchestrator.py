from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .codex_runner import CodexRunner
from .core.engine import LoopConfig, LoopEngine, LoopResult
from .core.state_store import LoopStateStore
from .reviewer import Reviewer

LoopEventCallback = Callable[[dict[str, Any]], None]


@dataclass
class AutoLoopConfig(LoopConfig):
    state_file: str | None = None
    loop_event_callback: LoopEventCallback | None = None
    external_interrupt_reason_provider: Callable[[], str | None] | None = None
    pending_instruction_consumer: Callable[[], str | None] | None = None
    stop_requested_checker: Callable[[], bool] | None = None
    operator_messages_provider: Callable[[], list[str]] | None = None


AutoLoopResult = LoopResult


class _CallbackStateStore(LoopStateStore):
    def __init__(self, *, config: AutoLoopConfig) -> None:
        super().__init__(objective=config.objective, state_file=config.state_file)
        self._config = config

    def consume_interrupt_reason(self) -> str | None:
        provider = self._config.external_interrupt_reason_provider
        if provider is not None:
            reason = provider()
            if reason:
                return reason
        return super().consume_interrupt_reason()

    def consume_pending_instruction(self) -> str | None:
        consumer = self._config.pending_instruction_consumer
        if consumer is not None:
            instruction = consumer()
            if instruction:
                return instruction
        return super().consume_pending_instruction()

    def is_stop_requested(self) -> bool:
        checker = self._config.stop_requested_checker
        if checker is not None and checker():
            return True
        return super().is_stop_requested()

    def list_messages(self) -> list[str]:
        provider = self._config.operator_messages_provider
        if provider is not None:
            messages = provider()
            if messages:
                return messages
        return super().list_messages()

    def handle_event(self, event: dict[str, object]) -> None:
        super().handle_event(event)
        callback = self._config.loop_event_callback
        if callback is not None:
            callback(dict(event))


class AutoLoopOrchestrator:
    def __init__(self, runner: CodexRunner, reviewer: Reviewer, config: AutoLoopConfig) -> None:
        self._engine = LoopEngine(
            runner=runner,
            reviewer=reviewer,
            config=LoopConfig(
                objective=config.objective,
                max_rounds=config.max_rounds,
                max_no_progress_rounds=config.max_no_progress_rounds,
                check_commands=config.check_commands,
                check_timeout_seconds=config.check_timeout_seconds,
                main_model=config.main_model,
                main_reasoning_effort=config.main_reasoning_effort,
                reviewer_model=config.reviewer_model,
                reviewer_reasoning_effort=config.reviewer_reasoning_effort,
                main_extra_args=config.main_extra_args,
                reviewer_extra_args=config.reviewer_extra_args,
                skip_git_repo_check=config.skip_git_repo_check,
                full_auto=config.full_auto,
                dangerous_yolo=config.dangerous_yolo,
                stall_soft_idle_seconds=config.stall_soft_idle_seconds,
                stall_hard_idle_seconds=config.stall_hard_idle_seconds,
                initial_session_id=config.initial_session_id,
            ),
            state_store=_CallbackStateStore(config=config),
        )

    def run(self) -> AutoLoopResult:
        return self._engine.run()

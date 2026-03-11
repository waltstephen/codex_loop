from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..checks import all_checks_passed, run_checks
from ..codex_runner import CodexRunner, InactivitySnapshot, RunnerOptions
from ..models import ReviewDecision, RoundSummary
from ..reviewer import Reviewer, ReviewerConfig
from ..stall_subagent import analyze_stall
from .ports import EventSink
from .state_store import LoopStateStore


@dataclass
class LoopConfig:
    objective: str
    max_rounds: int = 50
    max_no_progress_rounds: int = 3
    check_commands: list[str] | None = None
    check_timeout_seconds: int = 1200
    main_model: str | None = None
    main_reasoning_effort: str | None = None
    reviewer_model: str | None = None
    reviewer_reasoning_effort: str | None = None
    main_extra_args: list[str] | None = None
    reviewer_extra_args: list[str] | None = None
    skip_git_repo_check: bool = False
    full_auto: bool = False
    dangerous_yolo: bool = False
    stall_soft_idle_seconds: int = 1200
    stall_hard_idle_seconds: int = 10800
    initial_session_id: str | None = None


@dataclass
class LoopResult:
    success: bool
    session_id: str | None
    rounds: list[RoundSummary]
    stop_reason: str


class LoopEngine:
    def __init__(
        self,
        *,
        runner: CodexRunner,
        reviewer: Reviewer,
        config: LoopConfig,
        state_store: LoopStateStore | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.runner = runner
        self.reviewer = reviewer
        self.config = config
        self.state_store = state_store or LoopStateStore(objective=config.objective)
        self.event_sink = event_sink

    def run(self) -> LoopResult:
        rounds: list[RoundSummary] = []
        session_id = self.config.initial_session_id
        no_progress_rounds = 0
        previous_main_message = ""
        next_main_prompt = self._initial_main_prompt(self.config.objective)
        self._emit(
            {
                "type": "loop.started",
                "objective": self.config.objective,
                "max_rounds": self.config.max_rounds,
                "session_id": session_id,
            }
        )

        for round_index in range(1, self.config.max_rounds + 1):
            if self.state_store.is_stop_requested():
                return self._complete(
                    success=False,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason="Stopped by operator command.",
                )

            def inactivity_callback(snapshot: InactivitySnapshot) -> str:
                return self._handle_inactivity(round_index=round_index, snapshot=snapshot)

            self._emit(
                {
                    "type": "round.started",
                    "round_index": round_index,
                    "session_id": session_id,
                }
            )
            main_result = self.runner.run_exec(
                prompt=next_main_prompt,
                resume_thread_id=session_id,
                options=RunnerOptions(
                    model=self.config.main_model,
                    reasoning_effort=self.config.main_reasoning_effort,
                    dangerous_yolo=self.config.dangerous_yolo,
                    full_auto=self.config.full_auto,
                    skip_git_repo_check=self.config.skip_git_repo_check,
                    extra_args=self.config.main_extra_args,
                    watchdog_soft_idle_seconds=self.config.stall_soft_idle_seconds,
                    watchdog_hard_idle_seconds=self.config.stall_hard_idle_seconds,
                    inactivity_callback=inactivity_callback,
                    external_interrupt_reason_provider=self.state_store.consume_interrupt_reason,
                ),
                run_label="main",
            )
            session_id = main_result.thread_id or session_id
            self._emit(
                {
                    "type": "round.main.completed",
                    "round_index": round_index,
                    "session_id": session_id,
                    "exit_code": main_result.exit_code,
                    "turn_completed": main_result.turn_completed,
                    "turn_failed": main_result.turn_failed,
                    "fatal_error": main_result.fatal_error,
                    "last_message": main_result.last_agent_message,
                }
            )

            interrupted = (
                main_result.fatal_error is not None
                and main_result.fatal_error.startswith("External interrupt:")
            )
            if interrupted:
                injected_instruction = self.state_store.consume_pending_instruction()
                review_reason = main_result.fatal_error
                next_action = "Continue with prior objective after external interruption."
                if injected_instruction:
                    review_reason = (
                        f"{main_result.fatal_error}. New operator instruction injected and will be applied."
                    )
                    next_action = "Apply injected operator instruction in next round."
                    self._emit(
                        {
                            "type": "round.control.injected",
                            "round_index": round_index,
                            "instruction": injected_instruction,
                        }
                    )
                review = ReviewDecision(
                    status="continue",
                    confidence=1.0,
                    reason=review_reason,
                    next_action=next_action,
                )
                round_summary = RoundSummary(
                    round_index=round_index,
                    thread_id=session_id,
                    main_exit_code=main_result.exit_code,
                    main_turn_completed=main_result.turn_completed,
                    main_turn_failed=True,
                    checks=[],
                    review=review,
                    main_last_message=main_result.last_agent_message,
                )
                rounds.append(round_summary)
                self.state_store.record_round(round_summary, session_id=session_id, current_review=review)

                if self.state_store.is_stop_requested():
                    return self._complete(
                        success=False,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Stopped by operator command.",
                    )

                if injected_instruction:
                    next_main_prompt = self._build_operator_override_prompt(
                        objective=self.config.objective,
                        instruction=injected_instruction,
                    )
                else:
                    next_main_prompt = self._build_continue_prompt(
                        objective=self.config.objective,
                        review=review,
                        checks_ok=False,
                    )
                continue

            checks = run_checks(self.config.check_commands or [], self.config.check_timeout_seconds)
            self._emit(
                {
                    "type": "round.checks.completed",
                    "round_index": round_index,
                    "checks": [
                        {
                            "command": item.command,
                            "exit_code": item.exit_code,
                            "passed": item.passed,
                        }
                        for item in checks
                    ],
                }
            )
            review = self.reviewer.evaluate(
                objective=self.config.objective,
                operator_messages=self.state_store.list_messages(),
                round_index=round_index,
                session_id=session_id,
                main_summary=main_result.last_agent_message,
                main_error=main_result.fatal_error,
                checks=checks,
                config=ReviewerConfig(
                    model=self.config.reviewer_model,
                    reasoning_effort=self.config.reviewer_reasoning_effort,
                    extra_args=self.config.reviewer_extra_args,
                    skip_git_repo_check=self.config.skip_git_repo_check,
                    full_auto=self.config.full_auto,
                    dangerous_yolo=self.config.dangerous_yolo,
                ),
            )
            self._emit(
                {
                    "type": "round.review.completed",
                    "round_index": round_index,
                    "status": review.status,
                    "confidence": review.confidence,
                    "reason": review.reason,
                    "next_action": review.next_action,
                }
            )

            round_summary = RoundSummary(
                round_index=round_index,
                thread_id=session_id,
                main_exit_code=main_result.exit_code,
                main_turn_completed=main_result.turn_completed,
                main_turn_failed=main_result.turn_failed,
                checks=checks,
                review=review,
                main_last_message=main_result.last_agent_message,
            )
            rounds.append(round_summary)
            self.state_store.record_round(round_summary, session_id=session_id, current_review=review)

            checks_ok = all_checks_passed(checks)
            if review.status == "done" and checks_ok:
                return self._complete(
                    success=True,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason="Reviewer marked done and acceptance checks passed.",
                )

            if review.status == "blocked":
                return self._complete(
                    success=False,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason=f"Reviewer blocked: {review.reason}",
                )

            current_main_message = (main_result.last_agent_message or "").strip()
            if current_main_message and current_main_message == previous_main_message:
                no_progress_rounds += 1
            else:
                no_progress_rounds = 0
                previous_main_message = current_main_message

            if no_progress_rounds >= self.config.max_no_progress_rounds:
                return self._complete(
                    success=False,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason=(
                        "Stopped due to repeated no-progress rounds. "
                        "Reviewer kept requesting continuation without new output."
                    ),
                )

            next_main_prompt = self._build_continue_prompt(
                objective=self.config.objective,
                review=review,
                checks_ok=checks_ok,
            )

        return self._complete(
            success=False,
            session_id=session_id,
            rounds=rounds,
            stop_reason=f"Reached max rounds ({self.config.max_rounds}).",
        )

    def _complete(
        self,
        *,
        success: bool,
        session_id: str | None,
        rounds: list[RoundSummary],
        stop_reason: str,
    ) -> LoopResult:
        self.state_store.record_completion(success=success, stop_reason=stop_reason, session_id=session_id)
        self._emit(
            {
                "type": "loop.completed",
                "success": success,
                "stop_reason": stop_reason,
            }
        )
        return LoopResult(
            success=success,
            session_id=session_id,
            rounds=rounds,
            stop_reason=stop_reason,
        )

    def _emit(self, event: dict[str, Any]) -> None:
        payload = dict(event)
        payload.setdefault("ts", datetime.now(timezone.utc).isoformat())
        self.state_store.handle_event(payload)
        if self.event_sink is not None:
            self.event_sink.handle_event(payload)

    def _handle_inactivity(self, *, round_index: int, snapshot: InactivitySnapshot) -> str:
        decision = analyze_stall(snapshot)
        self._emit(
            {
                "type": "round.watchdog.checked",
                "round_index": round_index,
                "idle_seconds": int(snapshot.idle_seconds),
                "should_restart": decision.should_restart,
                "reason": decision.reason,
                "matched_pattern": decision.matched_pattern,
            }
        )
        if decision.should_restart:
            self._emit(
                {
                    "type": "round.watchdog.restart_requested",
                    "round_index": round_index,
                    "idle_seconds": int(snapshot.idle_seconds),
                    "reason": decision.reason,
                }
            )
            return "restart"
        return "continue"

    @staticmethod
    def _initial_main_prompt(objective: str) -> str:
        return (
            "You are the primary implementation agent.\n"
            "Complete the objective end-to-end by executing required edits and commands directly.\n"
            "Do not stop after a partial plan.\n"
            "If one path fails, try alternatives before declaring a blocker.\n"
            "Do not ask the user to perform next steps.\n\n"
            f"Objective:\n{objective}\n\n"
            "At the end, output a concise execution summary:\n"
            "- DONE:\n- REMAINING:\n- BLOCKERS:\n"
        )

    @staticmethod
    def _build_continue_prompt(*, objective: str, review: ReviewDecision, checks_ok: bool) -> str:
        check_instruction = (
            "Acceptance checks passed in previous round."
            if checks_ok
            else "Acceptance checks failed in previous round; fix them first."
        )
        return (
            "Continue the same objective in this session.\n"
            f"Objective:\n{objective}\n\n"
            f"Reviewer reason:\n{review.reason}\n\n"
            f"Reviewer next action:\n{review.next_action}\n\n"
            f"{check_instruction}\n"
            "Execute concrete work now. Do not stop at guidance-only output.\n"
            "End your response with updated DONE/REMAINING/BLOCKERS."
        )

    @staticmethod
    def _build_operator_override_prompt(*, objective: str, instruction: str) -> str:
        return (
            "Operator override received from control channel.\n"
            "Immediately switch to the following instruction while preserving repository safety.\n\n"
            f"Original objective:\n{objective}\n\n"
            f"New operator instruction:\n{instruction}\n\n"
            "Execute concrete work now and continue until completion gates are met.\n"
            "End with DONE/REMAINING/BLOCKERS."
        )

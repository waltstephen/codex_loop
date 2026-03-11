from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .checks import all_checks_passed, run_checks
from .codex_runner import CodexRunner, InactivitySnapshot, RunnerOptions
from .models import PlanSnapshot, ReviewDecision, RoundSummary
from .planner_modes import planner_mode_enabled
from .planner import Planner, PlannerConfig, format_plan_todo_markdown
from .reviewer import Reviewer, ReviewerConfig
from .stall_subagent import analyze_stall

LoopEventCallback = Callable[[dict[str, Any]], None]


@dataclass
class AutoLoopConfig:
    objective: str
    max_rounds: int = 50
    max_no_progress_rounds: int = 3
    check_commands: list[str] | None = None
    check_timeout_seconds: int = 1200
    main_model: str | None = None
    main_reasoning_effort: str | None = None
    reviewer_model: str | None = None
    reviewer_reasoning_effort: str | None = None
    planner_model: str | None = None
    planner_reasoning_effort: str | None = None
    planner_mode: str = "auto"
    main_extra_args: list[str] | None = None
    reviewer_extra_args: list[str] | None = None
    planner_extra_args: list[str] | None = None
    skip_git_repo_check: bool = False
    full_auto: bool = False
    dangerous_yolo: bool = False
    state_file: str | None = None
    plan_report_file: str | None = None
    plan_todo_file: str | None = None
    initial_session_id: str | None = None
    loop_event_callback: LoopEventCallback | None = None
    stall_soft_idle_seconds: int = 1200
    stall_hard_idle_seconds: int = 10800
    plan_update_interval_seconds: int = 1800
    planner_enabled: bool = True
    external_interrupt_reason_provider: Callable[[], str | None] | None = None
    pending_instruction_consumer: Callable[[], str | None] | None = None
    stop_requested_checker: Callable[[], bool] | None = None
    operator_messages_provider: Callable[[], list[str]] | None = None


@dataclass
class AutoLoopResult:
    success: bool
    session_id: str | None
    rounds: list[RoundSummary]
    stop_reason: str
    plan: PlanSnapshot | None = None


@dataclass
class _PlannerContext:
    round_index: int
    session_id: str | None
    rounds: list[RoundSummary]
    latest_review: ReviewDecision | None
    latest_checks: list[Any]
    stop_reason: str | None


class AutoLoopOrchestrator:
    def __init__(
        self,
        runner: CodexRunner,
        reviewer: Reviewer,
        planner: Planner | None,
        config: AutoLoopConfig,
    ) -> None:
        self.runner = runner
        self.reviewer = reviewer
        self.planner = planner
        self.config = config
        self._planner_context_lock = threading.Lock()
        self._planner_run_lock = threading.Lock()
        self._planner_stop_event = threading.Event()
        self._planner_thread: threading.Thread | None = None
        self._latest_plan: PlanSnapshot | None = None
        self._planner_context = _PlannerContext(
            round_index=0,
            session_id=config.initial_session_id,
            rounds=[],
            latest_review=None,
            latest_checks=[],
            stop_reason=None,
        )

    def run(self) -> AutoLoopResult:
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
        self._persist_state(rounds=rounds, session_id=session_id, current_review=None)
        self._start_planner_loop()
        self._run_planner_update(trigger="initial", terminal=False, wait=True)
        self._persist_state(rounds=rounds, session_id=session_id, current_review=None)

        try:
            for round_index in range(1, self.config.max_rounds + 1):
                if self._is_stop_requested():
                    return self._finish_loop(
                        success=False,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Stopped by operator command.",
                        round_index=round_index - 1,
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
                self._update_planner_context(
                    round_index=round_index,
                    session_id=session_id,
                    rounds=rounds,
                    latest_review=self._planner_context.latest_review,
                    latest_checks=self._planner_context.latest_checks,
                    stop_reason=None,
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
                        external_interrupt_reason_provider=self.config.external_interrupt_reason_provider,
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
                    injected_instruction = self._consume_pending_instruction()
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
                    self._update_planner_context(
                        round_index=round_index,
                        session_id=session_id,
                        rounds=rounds,
                        latest_review=review,
                        latest_checks=[],
                        stop_reason=None,
                    )
                    self._run_planner_update(trigger="round", terminal=False, wait=True)
                    self._persist_state(rounds=rounds, session_id=session_id, current_review=review)

                    if self._is_stop_requested():
                        return self._finish_loop(
                            success=False,
                            session_id=session_id,
                            rounds=rounds,
                            stop_reason="Stopped by operator command.",
                            round_index=round_index,
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
                    operator_messages=self._get_operator_messages(),
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
                self._update_planner_context(
                    round_index=round_index,
                    session_id=session_id,
                    rounds=rounds,
                    latest_review=review,
                    latest_checks=checks,
                    stop_reason=None,
                )
                self._run_planner_update(trigger="round", terminal=False, wait=True)
                self._persist_state(rounds=rounds, session_id=session_id, current_review=review)

                checks_ok = all_checks_passed(checks)
                if review.status == "done" and checks_ok:
                    return self._finish_loop(
                        success=True,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Reviewer marked done and acceptance checks passed.",
                        round_index=round_index,
                    )

                if review.status == "blocked":
                    return self._finish_loop(
                        success=False,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason=f"Reviewer blocked: {review.reason}",
                        round_index=round_index,
                    )

                current_main_message = (main_result.last_agent_message or "").strip()
                if current_main_message and current_main_message == previous_main_message:
                    no_progress_rounds += 1
                else:
                    no_progress_rounds = 0
                    previous_main_message = current_main_message

                if no_progress_rounds >= self.config.max_no_progress_rounds:
                    return self._finish_loop(
                        success=False,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason=(
                            "Stopped due to repeated no-progress rounds. "
                            "Reviewer kept requesting continuation without new output."
                        ),
                        round_index=round_index,
                    )

                next_main_prompt = self._build_continue_prompt(
                    objective=self.config.objective,
                    review=review,
                    checks_ok=checks_ok,
                )

            return self._finish_loop(
                success=False,
                session_id=session_id,
                rounds=rounds,
                stop_reason=f"Reached max rounds ({self.config.max_rounds}).",
                round_index=len(rounds),
            )
        finally:
            self._stop_planner_loop()

    def _finish_loop(
        self,
        *,
        success: bool,
        session_id: str | None,
        rounds: list[RoundSummary],
        stop_reason: str,
        round_index: int,
    ) -> AutoLoopResult:
        self._planner_stop_event.set()
        latest_review = rounds[-1].review if rounds else None
        latest_checks = rounds[-1].checks if rounds else []
        self._update_planner_context(
            round_index=round_index,
            session_id=session_id,
            rounds=rounds,
            latest_review=latest_review,
            latest_checks=latest_checks,
            stop_reason=stop_reason,
        )
        self._run_planner_update(trigger="final", terminal=True, wait=True)
        self._persist_state(rounds=rounds, session_id=session_id, current_review=latest_review)
        result = AutoLoopResult(
            success=success,
            session_id=session_id,
            rounds=rounds,
            stop_reason=stop_reason,
            plan=self._latest_plan,
        )
        self._emit({"type": "loop.completed", "success": result.success, "stop_reason": result.stop_reason})
        return result

    def _persist_state(
        self,
        *,
        rounds: list[RoundSummary],
        session_id: str | None,
        current_review: ReviewDecision | None,
    ) -> None:
        if not self.config.state_file:
            self._write_plan_artifacts()
            return
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "objective": self.config.objective,
            "session_id": session_id,
            "round_count": len(rounds),
            "latest_review_status": current_review.status if current_review is not None else None,
            "rounds": [self._serialize_round(item) for item in rounds],
            "plan": self._serialize_plan(self._latest_plan) if self._latest_plan is not None else None,
        }
        path = Path(self.config.state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._write_plan_artifacts()

    @staticmethod
    def _serialize_round(round_summary: RoundSummary) -> dict:
        data = asdict(round_summary)
        data["checks"] = [asdict(item) for item in round_summary.checks]
        data["review"] = asdict(round_summary.review)
        return data

    @staticmethod
    def _serialize_plan(plan: PlanSnapshot) -> dict[str, Any]:
        data = asdict(plan)
        data["workstreams"] = [asdict(item) for item in plan.workstreams]
        return data

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

    def _emit(self, event: dict[str, Any]) -> None:
        callback = self.config.loop_event_callback
        if callback is None:
            return
        callback(event)

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

    def _consume_pending_instruction(self) -> str | None:
        consumer = self.config.pending_instruction_consumer
        if consumer is None:
            return None
        return consumer()

    def _is_stop_requested(self) -> bool:
        checker = self.config.stop_requested_checker
        if checker is None:
            return False
        return checker()

    def _get_operator_messages(self) -> list[str]:
        provider = self.config.operator_messages_provider
        if provider is None:
            return []
        return provider()

    def _update_planner_context(
        self,
        *,
        round_index: int,
        session_id: str | None,
        rounds: list[RoundSummary],
        latest_review: ReviewDecision | None,
        latest_checks: list[Any],
        stop_reason: str | None,
    ) -> None:
        with self._planner_context_lock:
            self._planner_context = _PlannerContext(
                round_index=round_index,
                session_id=session_id,
                rounds=list(rounds),
                latest_review=latest_review,
                latest_checks=list(latest_checks),
                stop_reason=stop_reason,
            )

    def _run_planner_update(self, *, trigger: str, terminal: bool, wait: bool) -> None:
        if not self._planner_enabled():
            return
        acquired = self._planner_run_lock.acquire(blocking=wait)
        if not acquired:
            return
        try:
            with self._planner_context_lock:
                context = _PlannerContext(
                    round_index=self._planner_context.round_index,
                    session_id=self._planner_context.session_id,
                    rounds=list(self._planner_context.rounds),
                    latest_review=self._planner_context.latest_review,
                    latest_checks=list(self._planner_context.latest_checks),
                    stop_reason=self._planner_context.stop_reason,
                )
            assert self.planner is not None
            plan = self.planner.update(
                objective=self.config.objective,
                operator_messages=self._get_operator_messages(),
                round_index=context.round_index,
                session_id=context.session_id,
                rounds=context.rounds,
                latest_review=context.latest_review,
                latest_checks=context.latest_checks,
                trigger=trigger,
                terminal=terminal,
                stop_reason=context.stop_reason,
                config=PlannerConfig(
                    model=self.config.planner_model or self.config.reviewer_model,
                    reasoning_effort=self.config.planner_reasoning_effort or self.config.reviewer_reasoning_effort,
                    extra_args=self.config.planner_extra_args or self.config.reviewer_extra_args,
                    skip_git_repo_check=self.config.skip_git_repo_check,
                    full_auto=self.config.full_auto,
                    dangerous_yolo=self.config.dangerous_yolo,
                    mode=self.config.planner_mode,
                ),
            )
            self._latest_plan = plan
            event_type = "plan.finalized" if terminal else "plan.updated"
            self._emit(
                {
                    "type": event_type,
                    "round_index": context.round_index,
                    "session_id": context.session_id,
                    "plan_id": plan.plan_id,
                    "trigger": plan.trigger,
                    "terminal": plan.terminal,
                    "summary": plan.summary,
                    "workstreams": [asdict(item) for item in plan.workstreams],
                    "done_items": plan.done_items,
                    "remaining_items": plan.remaining_items,
                    "risks": plan.risks,
                    "next_steps": plan.next_steps,
                    "exploration_items": plan.exploration_items,
                    "suggested_next_objective": plan.suggested_next_objective,
                    "should_propose_follow_up": plan.should_propose_follow_up,
                    "report_markdown": plan.report_markdown,
                }
            )
        finally:
            self._planner_run_lock.release()

    def _start_planner_loop(self) -> None:
        if not self._planner_enabled():
            return
        if self.config.plan_update_interval_seconds <= 0:
            return
        if self._planner_thread is not None and self._planner_thread.is_alive():
            return
        self._planner_stop_event.clear()
        self._planner_thread = threading.Thread(target=self._planner_loop, daemon=True)
        self._planner_thread.start()

    def _planner_loop(self) -> None:
        interval = max(30, int(self.config.plan_update_interval_seconds))
        while not self._planner_stop_event.wait(interval):
            self._run_planner_update(trigger="timer", terminal=False, wait=False)
            with self._planner_context_lock:
                context = self._planner_context
            self._persist_state(
                rounds=context.rounds,
                session_id=context.session_id,
                current_review=context.latest_review,
            )

    def _stop_planner_loop(self) -> None:
        self._planner_stop_event.set()
        if self._planner_thread is not None:
            self._planner_thread.join(timeout=5.0)
            self._planner_thread = None

    def _planner_enabled(self) -> bool:
        return self.config.planner_enabled and planner_mode_enabled(self.config.planner_mode) and self.planner is not None

    def _write_plan_artifacts(self) -> None:
        if self._latest_plan is None:
            return
        if self.config.plan_report_file:
            path = Path(self.config.plan_report_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._latest_plan.report_markdown, encoding="utf-8")
        if self.config.plan_todo_file:
            path = Path(self.config.plan_todo_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                format_plan_todo_markdown(
                    objective=self.config.objective,
                    snapshot=self._latest_plan,
                ),
                encoding="utf-8",
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

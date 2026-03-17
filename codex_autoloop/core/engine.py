from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..checks import all_checks_passed, run_checks
from ..codex_runner import CodexRunner, InactivitySnapshot, RunnerOptions
from ..failure_modes import build_progress_signature, build_quota_exhaustion_stop_reason, looks_like_quota_exhaustion
from ..models import PlanDecision, PlanMode, ReviewDecision, RoundSummary
from ..planner import Planner, PlannerConfig
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
    plan_mode: PlanMode = "off"
    plan_model: str | None = None
    plan_reasoning_effort: str | None = None
    plan_extra_args: list[str] | None = None


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
        planner: Planner | None,
        config: LoopConfig,
        state_store: LoopStateStore | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.runner = runner
        self.reviewer = reviewer
        self.planner = planner
        self.config = config
        self.state_store = state_store or LoopStateStore(objective=config.objective, plan_mode=config.plan_mode)
        self.event_sink = event_sink

    def run(self) -> LoopResult:
        rounds: list[RoundSummary] = []
        session_id = self.config.initial_session_id
        no_progress_rounds = 0
        previous_progress_signature = ""
        self._emit(
            {
                "type": "loop.started",
                "objective": self.config.objective,
                "max_rounds": self.config.max_rounds,
                "session_id": session_id,
                "plan_mode": self._current_plan_mode(),
            }
        )
        current_plan: PlanDecision | None = None
        next_main_prompt = self._initial_main_prompt(
            self.config.objective,
            operator_messages=self.state_store.list_messages_for_role("main"),
            plan=current_plan,
            plan_mode=self._current_plan_mode(),
        )
        next_main_prompt_phase = "initial"

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
            self.state_store.record_main_prompt(
                round_index=round_index,
                phase=next_main_prompt_phase,
                prompt=next_main_prompt,
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
                    round_summary_markdown=(
                        "# Review Summary\n\n"
                        f"- Round interrupted: {main_result.fatal_error}\n"
                        f"- Latest main summary: {main_result.last_agent_message or 'none'}\n"
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
                    main_turn_failed=True,
                    checks=[],
                    review=review,
                    main_last_message=main_result.last_agent_message,
                    plan=current_plan,
                )
                rounds.append(round_summary)
                self.state_store.record_round(
                    round_summary,
                    session_id=session_id,
                    current_review=review,
                    current_plan=current_plan,
                )

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
                        operator_messages=self.state_store.list_messages_for_role("main"),
                        plan=current_plan,
                        plan_mode=self._current_plan_mode(),
                    )
                    next_main_prompt_phase = "operator-override"
                else:
                    next_main_prompt = self._build_continue_prompt(
                        objective=self.config.objective,
                        review=review,
                        checks_ok=False,
                        operator_messages=self.state_store.list_messages_for_role("main"),
                        plan=current_plan,
                        plan_mode=self._current_plan_mode(),
                    )
                    next_main_prompt_phase = "continue"
                continue

            if looks_like_quota_exhaustion(main_result.fatal_error):
                review = ReviewDecision(
                    status="blocked",
                    confidence=1.0,
                    reason="Main agent hit a non-recoverable Codex quota or billing limit.",
                    next_action="Wait for quota reset or increase available quota, then rerun the objective.",
                    round_summary_markdown=(
                        "# Review Summary\n\n"
                        "- Main agent hit a non-recoverable Codex quota or billing limit.\n"
                        f"- Fatal error: {main_result.fatal_error or 'none'}\n"
                        "- Automatic retries would not make progress.\n"
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
                    checks=[],
                    review=review,
                    main_last_message=main_result.last_agent_message,
                    plan=current_plan,
                )
                rounds.append(round_summary)
                self.state_store.record_round(
                    round_summary,
                    session_id=session_id,
                    current_review=review,
                    current_plan=current_plan,
                )
                return self._complete(
                    success=False,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason=build_quota_exhaustion_stop_reason(main_result.fatal_error),
                )

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
                operator_messages=self.state_store.list_messages_for_role("review"),
                planner_review_instruction=(current_plan.review_instruction if current_plan is not None else ""),
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
            checks_ok = all_checks_passed(checks)
            planned_follow_up: PlanDecision | None = None
            current_plan_mode = self._current_plan_mode()
            if review.status == "done" and checks_ok and current_plan_mode != "off":
                planned_follow_up = self._maybe_run_planner(
                    round_index=round_index,
                    session_id=session_id,
                    latest_review_completion_summary=review.completion_summary_markdown,
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
                plan=planned_follow_up if planned_follow_up is not None else current_plan,
            )
            rounds.append(round_summary)
            self.state_store.record_round(
                round_summary,
                session_id=session_id,
                current_review=review,
                current_plan=planned_follow_up if planned_follow_up is not None else current_plan,
            )

            if review.status == "done" and checks_ok:
                current_plan_mode = self._current_plan_mode()
                if current_plan_mode == "off":
                    return self._complete(
                        success=True,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Reviewer marked done and acceptance checks passed.",
                    )
                if current_plan_mode == "record":
                    return self._complete(
                        success=True,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Reviewer marked done, checks passed, and planner recorded the final summary.",
                    )
                if planned_follow_up is None or not planned_follow_up.follow_up_required:
                    return self._complete(
                        success=True,
                        session_id=session_id,
                        rounds=rounds,
                        stop_reason="Reviewer marked done, checks passed, and planner did not require a follow-up phase.",
                    )
                current_plan = planned_follow_up
                no_progress_rounds = 0
                previous_progress_signature = ""
                next_main_prompt = self._build_follow_up_prompt(
                    objective=self.config.objective,
                    operator_messages=self.state_store.list_messages_for_role("main"),
                    plan=current_plan,
                )
                next_main_prompt_phase = "follow-up"
                continue

            if review.status == "blocked":
                return self._complete(
                    success=False,
                    session_id=session_id,
                    rounds=rounds,
                    stop_reason=f"Reviewer blocked: {review.reason}",
                )

            current_progress_signature = build_progress_signature(main_result=main_result)
            if current_progress_signature and current_progress_signature == previous_progress_signature:
                no_progress_rounds += 1
            else:
                no_progress_rounds = 0
                previous_progress_signature = current_progress_signature

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
                operator_messages=self.state_store.list_messages_for_role("main"),
                plan=current_plan,
                plan_mode=self._current_plan_mode(),
            )
            next_main_prompt_phase = "continue"

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

    def _current_plan_mode(self) -> PlanMode:
        return self.state_store.current_plan_mode()

    def _maybe_run_planner(
        self,
        *,
        round_index: int,
        session_id: str | None,
        latest_review_completion_summary: str,
    ) -> PlanDecision | None:
        current_plan_mode = self._current_plan_mode()
        if current_plan_mode == "off" or self.planner is None:
            return None
        plan = self.planner.evaluate(
            objective=self.config.objective,
            plan_messages=self.state_store.list_messages_for_role("plan"),
            round_index=round_index,
            session_id=session_id,
            latest_review_completion_summary=latest_review_completion_summary,
            latest_plan_overview=self.state_store.latest_plan_overview(),
            config=PlannerConfig(
                mode=current_plan_mode,
                model=self.config.plan_model,
                reasoning_effort=self.config.plan_reasoning_effort,
                extra_args=self.config.plan_extra_args,
                skip_git_repo_check=self.config.skip_git_repo_check,
                full_auto=self.config.full_auto,
                dangerous_yolo=self.config.dangerous_yolo,
            ),
        )
        self.state_store.record_plan(plan, round_index=round_index, session_id=session_id)
        self._emit(
            {
                "type": "plan.completed",
                "round_index": round_index,
                "plan_mode": current_plan_mode,
                "follow_up_required": plan.follow_up_required,
                "next_explore": plan.next_explore,
                "main_instruction": plan.main_instruction,
                "review_instruction": plan.review_instruction,
            }
        )
        return plan

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
    def _initial_main_prompt(
        objective: str,
        *,
        operator_messages: list[str],
        plan: PlanDecision | None,
        plan_mode: PlanMode,
    ) -> str:
        prompt = (
            "You are the primary implementation agent.\n"
            "Complete the objective end-to-end by executing required edits and commands directly.\n"
            "Do not stop after a partial plan.\n"
            "If one path fails, try alternatives before declaring a blocker.\n"
            "Do not ask the user to perform next steps.\n\n"
            f"Objective:\n{objective}\n\n"
        )
        if operator_messages:
            prompt += "Operator messages visible to you:\n" + "\n".join(f"- {item}" for item in operator_messages) + "\n\n"
        if plan_mode == "auto" and plan is not None:
            prompt += (
                "Planner guidance:\n"
                f"- Next explore: {plan.next_explore}\n"
                f"- Main instruction: {plan.main_instruction}\n\n"
            )
        prompt += (
            "Do not reply with a generic role acknowledgment or a promise to start later.\n"
            "Your first response in this turn must reflect concrete execution progress in the repository.\n"
            "Before finishing this turn, do at least one concrete repo action such as reading key files, running a read-only inspection command, or making a targeted code change.\n"
            "If the task is still unclear, first inspect the repository and state what you found, instead of asking the user what to do.\n"
            "Your final message must include specific evidence of action taken in this turn.\n\n"
            "At the end, output a concise execution summary:\n"
            "- DONE:\n- REMAINING:\n- BLOCKERS:\n"
        )
        return prompt

    @staticmethod
    def _build_continue_prompt(
        *,
        objective: str,
        review: ReviewDecision,
        checks_ok: bool,
        operator_messages: list[str],
        plan: PlanDecision | None,
        plan_mode: PlanMode,
    ) -> str:
        check_instruction = (
            "Acceptance checks passed in previous round."
            if checks_ok
            else "Acceptance checks failed in previous round; fix them first."
        )
        prompt = (
            "Continue the same objective in this session.\n"
            f"Objective:\n{objective}\n\n"
            f"Reviewer reason:\n{review.reason}\n\n"
            f"Reviewer next action:\n{review.next_action}\n\n"
        )
        if operator_messages:
            prompt += "Operator messages visible to you:\n" + "\n".join(f"- {item}" for item in operator_messages) + "\n\n"
        if plan_mode == "auto" and plan is not None:
            prompt += (
                "Planner follow-up:\n"
                f"- Next explore: {plan.next_explore}\n"
                f"- Main instruction: {plan.main_instruction}\n\n"
            )
        prompt += (
            "Do not reply with a generic role acknowledgment or a promise to start later.\n"
            "In this turn, perform concrete work or concrete inspection in the repository before you finish.\n"
            "Your final message must include evidence of what you actually did in this turn.\n"
            f"{check_instruction}\n"
            "Execute concrete work now. Do not stop at guidance-only output.\n"
            "End your response with updated DONE/REMAINING/BLOCKERS."
        )
        return prompt

    @staticmethod
    def _build_follow_up_prompt(
        *,
        objective: str,
        operator_messages: list[str],
        plan: PlanDecision,
    ) -> str:
        prompt = (
            "The previous implementation/review phase completed successfully.\n"
            "Start the next automatic follow-up phase planned below.\n\n"
            f"Objective:\n{objective}\n\n"
            "Planner follow-up:\n"
            f"- Next explore: {plan.next_explore}\n"
            f"- Main instruction: {plan.main_instruction}\n\n"
        )
        if operator_messages:
            prompt += "Operator messages visible to you:\n" + "\n".join(f"- {item}" for item in operator_messages) + "\n\n"
        prompt += (
            "Do not reply with a generic role acknowledgment or a promise to start later.\n"
            "You must begin concrete follow-up work immediately in this turn.\n"
            "Your final message must include evidence of what changed or what was inspected.\n"
            "Execute concrete work now. Do not stop at guidance-only output.\n"
            "End your response with updated DONE/REMAINING/BLOCKERS."
        )
        return prompt

    @staticmethod
    def _build_operator_override_prompt(
        *,
        objective: str,
        instruction: str,
        operator_messages: list[str],
        plan: PlanDecision | None,
        plan_mode: PlanMode,
    ) -> str:
        prompt = (
            "Operator override received from control channel.\n"
            "Immediately switch to the following instruction while preserving repository safety.\n\n"
            f"Original objective:\n{objective}\n\n"
            f"New operator instruction:\n{instruction}\n\n"
        )
        if operator_messages:
            prompt += "Operator messages visible to you:\n" + "\n".join(f"- {item}" for item in operator_messages) + "\n\n"
        if plan_mode == "auto" and plan is not None:
            prompt += (
                "Planner context:\n"
                f"- Next explore: {plan.next_explore}\n"
                f"- Main instruction: {plan.main_instruction}\n\n"
            )
        prompt += (
            "Do not reply with a generic role acknowledgment or a promise to start later.\n"
            "After receiving this override, take concrete action in the repository within this turn.\n"
            "Your final message must include evidence of actual work done or files inspected.\n"
            "Execute concrete work now and continue until completion gates are met.\n"
            "End with DONE/REMAINING/BLOCKERS."
        )
        return prompt

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .checks import summarize_checks
from .codex_runner import CodexRunner, RunnerOptions
from .models import CheckResult, ReviewDecision


@dataclass
class ReviewerConfig:
    model: str | None = None
    reasoning_effort: str | None = None
    extra_args: list[str] | None = None
    skip_git_repo_check: bool = False
    full_auto: bool = False
    dangerous_yolo: bool = False


class Reviewer:
    def __init__(self, runner: CodexRunner) -> None:
        self.runner = runner
        self.schema_path = str(Path(__file__).with_name("reviewer_schema.json"))

    def evaluate(
        self,
        *,
        objective: str,
        operator_messages: list[str],
        planner_review_instruction: str = "",
        round_index: int,
        session_id: str | None,
        main_summary: str,
        main_error: str | None,
        checks: list[CheckResult],
        config: ReviewerConfig,
    ) -> ReviewDecision:
        prompt = self._build_prompt(
            objective=objective,
            operator_messages=operator_messages,
            planner_review_instruction=planner_review_instruction,
            round_index=round_index,
            session_id=session_id,
            main_summary=main_summary,
            main_error=main_error,
            checks=checks,
        )
        result = self.runner.run_exec(
            prompt=prompt,
            resume_thread_id=None,
            options=RunnerOptions(
                model=config.model,
                reasoning_effort=config.reasoning_effort,
                dangerous_yolo=config.dangerous_yolo,
                full_auto=config.full_auto,
                skip_git_repo_check=config.skip_git_repo_check,
                extra_args=config.extra_args,
                output_schema_path=self.schema_path,
            ),
            run_label="reviewer",
        )
        if not result.last_agent_message:
            return ReviewDecision(
                status="continue",
                confidence=0.0,
                reason=f"Reviewer returned empty output. exit={result.exit_code}",
                next_action="Continue implementation and provide concrete completed work.",
                round_summary_markdown="# Review Summary\n\n- Reviewer returned empty output.\n",
            )

        parsed = parse_decision_text(result.last_agent_message)
        if parsed is None:
            return ReviewDecision(
                status="continue",
                confidence=0.0,
                reason="Reviewer output was not valid JSON.",
                next_action="Continue implementation and include clear completion evidence.",
                round_summary_markdown="# Review Summary\n\n- Reviewer output was not valid JSON.\n",
            )
        return parsed

    def _build_prompt(
        self,
        *,
        objective: str,
        operator_messages: list[str],
        planner_review_instruction: str = "",
        round_index: int,
        session_id: str | None,
        main_summary: str,
        main_error: str | None,
        checks: list[CheckResult],
    ) -> str:
        error_text = main_error or "none"
        check_text = summarize_checks(checks)
        operator_text = "\n".join(f"- {line}" for line in operator_messages) if operator_messages else "- none"
        return (
            "You are the reviewer sub-agent for a Codex autoloop run.\n"
            "Decide whether the objective is fully complete.\n\n"
            "Rules:\n"
            "1) `done` only when objective is fully satisfied, no blocker remains, and acceptance checks pass.\n"
            "2) If uncertain, choose `continue`.\n"
            "3) Use `blocked` only if additional user input is strictly required.\n"
            "4) `next_action` must be a concrete instruction for the primary agent.\n\n"
            "5) `round_summary_markdown` must summarize this round's completed work, evidence, and gaps.\n"
            "6) If status is not `done`, `completion_summary_markdown` should be a short placeholder or empty note.\n"
            "7) If status is `done`, `completion_summary_markdown` must summarize final completion evidence.\n\n"
            f"Objective:\n{objective}\n\n"
            "Operator message history (source of truth for user instructions):\n"
            f"{operator_text}\n\n"
            "Planner guidance for this review:\n"
            f"{planner_review_instruction or 'none'}\n\n"
            f"Round: {round_index}\n"
            f"Session ID: {session_id or 'none'}\n"
            f"Main agent fatal error: {error_text}\n\n"
            "Main agent last summary:\n"
            f"{main_summary}\n\n"
            "Acceptance check results:\n"
            f"{check_text}\n"
        )


def parse_decision_text(text: str) -> ReviewDecision | None:
    candidate = text.strip()
    parsed = _load_json(candidate)
    if parsed is None:
        left = candidate.find("{")
        right = candidate.rfind("}")
        if left >= 0 and right > left:
            parsed = _load_json(candidate[left : right + 1])
    if parsed is None:
        return None
    status = parsed.get("status")
    if status not in {"done", "continue", "blocked"}:
        return None
    confidence = parsed.get("confidence", 0.0)
    reason = parsed.get("reason", "")
    next_action = parsed.get("next_action", "")
    round_summary_markdown = parsed.get("round_summary_markdown", "")
    completion_summary_markdown = parsed.get("completion_summary_markdown", "")
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    if not isinstance(reason, str):
        reason = str(reason)
    if not isinstance(next_action, str):
        next_action = str(next_action)
    if not isinstance(round_summary_markdown, str):
        round_summary_markdown = str(round_summary_markdown)
    if not isinstance(completion_summary_markdown, str):
        completion_summary_markdown = str(completion_summary_markdown)
    return ReviewDecision(
        status=status,
        confidence=max(0.0, min(float(confidence), 1.0)),
        reason=reason.strip(),
        next_action=next_action.strip(),
        round_summary_markdown=round_summary_markdown.strip(),
        completion_summary_markdown=completion_summary_markdown.strip(),
    )


def _load_json(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return value

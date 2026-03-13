from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .codex_runner import CodexRunner, RunnerOptions
from .models import PlanDecision, PlanMode


@dataclass
class PlannerConfig:
    mode: PlanMode = "auto"
    model: str | None = None
    reasoning_effort: str | None = None
    extra_args: list[str] | None = None
    skip_git_repo_check: bool = False
    full_auto: bool = False
    dangerous_yolo: bool = False


class Planner:
    def __init__(self, runner: CodexRunner) -> None:
        self.runner = runner
        self.schema_path = str(Path(__file__).with_name("planner_schema.json"))

    def evaluate(
        self,
        *,
        objective: str,
        plan_messages: list[str],
        round_index: int,
        session_id: str | None,
        latest_review_completion_summary: str,
        latest_plan_overview: str,
        config: PlannerConfig,
    ) -> PlanDecision:
        prompt = self._build_prompt(
            objective=objective,
            plan_messages=plan_messages,
            round_index=round_index,
            session_id=session_id,
            latest_review_completion_summary=latest_review_completion_summary,
            latest_plan_overview=latest_plan_overview,
            mode=config.mode,
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
            run_label="planner",
        )
        if not result.last_agent_message:
            return _fallback_plan(
                latest_plan_overview=latest_plan_overview,
                reason=f"Planner returned empty output. exit={result.exit_code}",
            )

        parsed = parse_plan_text(result.last_agent_message)
        if parsed is None:
            return _fallback_plan(
                latest_plan_overview=latest_plan_overview,
                reason="Planner output was not valid JSON.",
            )
        return parsed

    def _build_prompt(
        self,
        *,
        objective: str,
        plan_messages: list[str],
        round_index: int,
        session_id: str | None,
        latest_review_completion_summary: str,
        latest_plan_overview: str,
        mode: PlanMode,
    ) -> str:
        message_text = "\n".join(f"- {item}" for item in plan_messages) if plan_messages else "- none"
        completion_summary = latest_review_completion_summary or "none"
        plan_overview = latest_plan_overview or "none"
        return (
            "You are the plan agent for a Codex autoloop run.\n"
            "Maintain the evolving task structure after a completed implementation/review phase.\n\n"
            "Rules:\n"
            "1) Use operator messages tagged for plan as the source of truth for extensions and direction changes.\n"
            "2) `follow_up_required` must be true only if another automatic follow-up phase should run.\n"
            "3) `next_explore` should name the next repo area, question, or validation target to investigate.\n"
            "4) `main_instruction` should be concrete and executable by the implementation agent.\n"
            "5) `review_instruction` should sharpen the next review focus and audit criteria.\n"
            "6) `overview_markdown` must be a concise but human-readable markdown summary with TODOs.\n"
            "7) In `record` mode, maintain structure and TODOs, but do not rely on automatic follow-up execution.\n"
            "8) If no automatic follow-up is needed, set `follow_up_required=false` and still update the overview.\n"
            "9) You may inspect the repository if needed before producing the plan.\n\n"
            f"Plan mode: {mode}\n"
            f"Objective:\n{objective}\n\n"
            "Operator direction for plan (broadcast + plan-only):\n"
            f"{message_text}\n\n"
            f"Round index for this planning pass: {round_index}\n"
            f"Session ID: {session_id or 'none'}\n"
            "Latest reviewer completion summary markdown (source of truth for finished work):\n"
            f"{completion_summary}\n\n"
            "Previous plan overview markdown:\n"
            f"{plan_overview}\n"
        )


def parse_plan_text(text: str) -> PlanDecision | None:
    candidate = text.strip()
    parsed = _load_json(candidate)
    if parsed is None:
        left = candidate.find("{")
        right = candidate.rfind("}")
        if left >= 0 and right > left:
            parsed = _load_json(candidate[left : right + 1])
    if parsed is None:
        return None
    follow_up_required = parsed.get("follow_up_required")
    next_explore = parsed.get("next_explore", "")
    main_instruction = parsed.get("main_instruction", "")
    review_instruction = parsed.get("review_instruction", "")
    overview_markdown = parsed.get("overview_markdown", "")
    if not isinstance(follow_up_required, bool):
        return None
    values = [next_explore, main_instruction, review_instruction, overview_markdown]
    if not all(isinstance(item, str) and item.strip() for item in values):
        return None
    return PlanDecision(
        follow_up_required=follow_up_required,
        next_explore=next_explore.strip(),
        main_instruction=main_instruction.strip(),
        review_instruction=review_instruction.strip(),
        overview_markdown=overview_markdown.strip(),
    )


def _load_json(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return value


def _fallback_plan(
    *,
    latest_plan_overview: str,
    reason: str,
) -> PlanDecision:
    next_explore = "Re-check the latest reviewer request and current repo state."
    main_instruction = "No automatic follow-up was planned."
    review_instruction = "Verify the claimed completed work against the explicit objective and checks."
    overview = latest_plan_overview.strip() if latest_plan_overview.strip() else "# Plan Overview\n\n- Planner fallback engaged."
    overview += f"\n\n## Planner Note\n- {reason}\n"
    return PlanDecision(
        follow_up_required=False,
        next_explore=next_explore,
        main_instruction=main_instruction,
        review_instruction=review_instruction,
        overview_markdown=overview.strip(),
    )

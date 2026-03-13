from pathlib import Path

from codex_autoloop.core.engine import LoopConfig, LoopEngine
from codex_autoloop.core.state_store import LoopStateStore
from codex_autoloop.models import CodexRunResult, PlanDecision, ReviewDecision
from codex_autoloop.planner import parse_plan_text


def test_parse_plan_text_valid() -> None:
    decision = parse_plan_text(
        '{"follow_up_required":true,"next_explore":"inspect parser","main_instruction":"fix parser","review_instruction":"check tests","overview_markdown":"# Plan\\n"}'
    )
    assert decision is not None
    assert decision.follow_up_required is True
    assert decision.next_explore == "inspect parser"


def test_parse_plan_text_invalid() -> None:
    assert parse_plan_text("not json") is None


class _FakeRunner:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.calls = 0

    def run_exec(self, *, prompt: str, resume_thread_id: str | None, options, run_label: str | None = None):
        self.prompts.append(prompt)
        self.calls += 1
        return CodexRunResult(
            command=["codex", "exec"],
            exit_code=0,
            thread_id="thread-1",
            agent_messages=[f"main-summary-{self.calls}"],
            turn_completed=True,
            turn_failed=False,
        )


class _FakeReviewer:
    def __init__(self) -> None:
        self.instructions: list[str] = []
        self.calls = 0

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
        checks: list,
        config,
    ) -> ReviewDecision:
        self.instructions.append(planner_review_instruction)
        self.calls += 1
        if self.calls == 1:
            return ReviewDecision(
                status="continue",
                confidence=0.7,
                reason="need one more pass",
                next_action="continue work",
                round_summary_markdown="## Round 1\n- more work needed\n",
            )
        if self.calls == 2:
            return ReviewDecision(
                status="done",
                confidence=1.0,
                reason="phase 1 complete",
                next_action="stop",
                round_summary_markdown="## Round 2\n- phase 1 done\n",
                completion_summary_markdown="## Complete Phase 1\n- shipped first milestone\n",
            )
        return ReviewDecision(
            status="done",
            confidence=1.0,
            reason="phase 2 complete",
            next_action="stop",
            round_summary_markdown="## Round 3\n- phase 2 done\n",
            completion_summary_markdown="## Complete Phase 2\n- shipped follow-up milestone\n",
        )


class _DoneReviewer:
    def __init__(self) -> None:
        self.calls = 0

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
        checks: list,
        config,
    ) -> ReviewDecision:
        self.calls += 1
        return ReviewDecision(
            status="done",
            confidence=1.0,
            reason="objective complete",
            next_action="stop",
            round_summary_markdown="## Round\n- complete\n",
            completion_summary_markdown="## Final\n- complete\n",
        )


class _FakePlanner:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def evaluate(
        self,
        *,
        objective: str,
        plan_messages: list[str],
        round_index: int,
        session_id: str | None,
        latest_review_completion_summary: str,
        latest_plan_overview: str,
        config,
    ) -> PlanDecision:
        self.calls.append((round_index, latest_review_completion_summary))
        follow_up_required = round_index == 2
        return PlanDecision(
            follow_up_required=follow_up_required,
            next_explore=f"explore-{round_index}",
            main_instruction=f"main-follow-up-{round_index}",
            review_instruction=f"review-focus-{round_index}",
            overview_markdown=f"## Plan {round_index}\n- update\n",
        )


class _InterruptingRunner:
    def __init__(self, *, fatal_error: str) -> None:
        self.prompts: list[str] = []
        self.calls = 0
        self.fatal_error = fatal_error

    def run_exec(self, *, prompt: str, resume_thread_id: str | None, options, run_label: str | None = None):
        self.prompts.append(prompt)
        self.calls += 1
        if self.calls == 1:
            return CodexRunResult(
                command=["codex", "exec"],
                exit_code=1,
                thread_id="thread-1",
                agent_messages=["main-summary-interrupted"],
                turn_completed=False,
                turn_failed=True,
                fatal_error=self.fatal_error,
            )
        return CodexRunResult(
            command=["codex", "exec", "resume"],
            exit_code=0,
            thread_id="thread-1",
            agent_messages=[f"main-summary-{self.calls}"],
            turn_completed=True,
            turn_failed=False,
        )


def test_loop_engine_auto_plan_influences_main_and_review(tmp_path: Path) -> None:
    runner = _FakeRunner()
    reviewer = _FakeReviewer()
    planner = _FakePlanner()
    state = LoopStateStore(
        objective="ship feature",
        plan_overview_file=str(tmp_path / "plan.md"),
        review_summaries_dir=str(tmp_path / "reviews"),
        plan_mode="auto",
    )
    state.record_message(text="ship feature", source="operator", kind="initial-objective")
    engine = LoopEngine(
        runner=runner,
        reviewer=reviewer,
        planner=planner,
        state_store=state,
        config=LoopConfig(objective="ship feature", max_rounds=3, plan_mode="auto"),
    )
    result = engine.run()
    assert result.success is True
    assert planner.calls == [
        (2, "## Complete Phase 1\n- shipped first milestone\n"),
        (3, "## Complete Phase 2\n- shipped follow-up milestone\n"),
    ]
    assert "main-follow-up-2" not in runner.prompts[0]
    assert "main-follow-up-2" not in runner.prompts[1]
    assert "main-follow-up-2" in runner.prompts[2]
    assert reviewer.instructions == ["", "", "review-focus-2"]


def test_loop_engine_record_mode_keeps_plan_out_of_main_prompts(tmp_path: Path) -> None:
    runner = _FakeRunner()
    reviewer = _FakeReviewer()
    planner = _FakePlanner()
    state = LoopStateStore(
        objective="ship feature",
        plan_overview_file=str(tmp_path / "plan.md"),
        review_summaries_dir=str(tmp_path / "reviews"),
        plan_mode="record",
    )
    state.record_message(text="ship feature", source="operator", kind="initial-objective")
    engine = LoopEngine(
        runner=runner,
        reviewer=reviewer,
        planner=planner,
        state_store=state,
        config=LoopConfig(objective="ship feature", max_rounds=3, plan_mode="record"),
    )
    result = engine.run()
    assert result.success is True
    assert planner.calls == [(2, "## Complete Phase 1\n- shipped first milestone\n")]
    assert "main-follow-up-2" not in runner.prompts[0]
    assert "main-follow-up-2" not in runner.prompts[1]


def test_initial_main_prompt_forbids_generic_ack() -> None:
    prompt = LoopEngine._initial_main_prompt(
        "ship feature",
        operator_messages=[],
        plan=None,
        plan_mode="off",
    )
    assert "Do not reply with a generic role acknowledgment" in prompt


def test_continue_prompt_requires_concrete_execution_evidence() -> None:
    prompt = LoopEngine._build_continue_prompt(
        objective="ship feature",
        review=ReviewDecision(
            status="continue",
            confidence=0.5,
            reason="need more work",
            next_action="inspect failing tests",
        ),
        checks_ok=False,
        operator_messages=[],
        plan=None,
        plan_mode="off",
    )
    assert "Do not reply with a generic role acknowledgment" in prompt
    assert "perform concrete work or concrete inspection in the repository" in prompt
    assert "Your final message must include evidence of what you actually did in this turn." in prompt


def test_follow_up_prompt_requires_immediate_concrete_work() -> None:
    prompt = LoopEngine._build_follow_up_prompt(
        objective="ship feature",
        operator_messages=[],
        plan=PlanDecision(
            follow_up_required=True,
            next_explore="inspect metrics",
            main_instruction="ship phase 2",
            review_instruction="verify phase 2",
            overview_markdown="## Plan\n",
        ),
    )
    assert "Do not reply with a generic role acknowledgment" in prompt
    assert "You must begin concrete follow-up work immediately in this turn." in prompt
    assert "Your final message must include evidence of what changed or what was inspected." in prompt


def test_operator_override_prompt_requires_repo_action() -> None:
    prompt = LoopEngine._build_operator_override_prompt(
        objective="ship feature",
        instruction="fix tests first",
        operator_messages=[],
        plan=None,
        plan_mode="off",
    )
    assert "Do not reply with a generic role acknowledgment" in prompt
    assert "take concrete action in the repository within this turn" in prompt
    assert "Your final message must include evidence of actual work done or files inspected." in prompt


def test_interrupt_with_pending_instruction_switches_to_override_prompt(tmp_path: Path) -> None:
    runner = _InterruptingRunner(fatal_error="External interrupt: telegram requested instruction update")
    reviewer = _DoneReviewer()
    state = LoopStateStore(
        objective="ship feature",
        plan_overview_file=str(tmp_path / "plan.md"),
        review_summaries_dir=str(tmp_path / "reviews"),
        plan_mode="off",
    )
    state.record_message(text="ship feature", source="operator", kind="initial-objective")
    state.request_inject("fix tests first", source="telegram")
    engine = LoopEngine(
        runner=runner,
        reviewer=reviewer,
        planner=None,
        state_store=state,
        config=LoopConfig(objective="ship feature", max_rounds=2, plan_mode="off"),
    )

    result = engine.run()

    assert result.success is True
    assert len(runner.prompts) == 2
    assert "Operator override received from control channel." in runner.prompts[1]
    assert "fix tests first" in runner.prompts[1]
    assert reviewer.calls == 1


def test_interrupt_without_pending_instruction_uses_continue_prompt(tmp_path: Path) -> None:
    runner = _InterruptingRunner(fatal_error="External interrupt: terminal requested status refresh")
    reviewer = _DoneReviewer()
    state = LoopStateStore(
        objective="ship feature",
        plan_overview_file=str(tmp_path / "plan.md"),
        review_summaries_dir=str(tmp_path / "reviews"),
        plan_mode="off",
    )
    state.record_message(text="ship feature", source="operator", kind="initial-objective")
    engine = LoopEngine(
        runner=runner,
        reviewer=reviewer,
        planner=None,
        state_store=state,
        config=LoopConfig(objective="ship feature", max_rounds=2, plan_mode="off"),
    )

    result = engine.run()

    assert result.success is True
    assert len(runner.prompts) == 2
    assert "Continue the same objective in this session." in runner.prompts[1]
    assert "Operator override received from control channel." not in runner.prompts[1]
    assert reviewer.calls == 1

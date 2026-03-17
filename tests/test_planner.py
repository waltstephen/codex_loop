from codex_autoloop.models import CheckResult, CodexRunResult, PlanSnapshot, PlanWorkstream, ReviewDecision
from codex_autoloop.planner import Planner, PlannerConfig, format_plan_markdown, parse_plan_text


def test_parse_plan_text_plain_json() -> None:
    snapshot = parse_plan_text(
        """
        {
          "summary": "Core loop is implemented and planner wiring is in progress.",
          "workstreams": [
            {
              "area": "Planner wiring",
              "status": "in_progress",
              "evidence": "Planner module exists.",
              "next_step": "Connect it to daemon."
            }
          ],
          "done_items": ["Planner schema added"],
          "remaining_items": ["Daemon follow-up buttons"],
          "risks": ["Need callback parsing"],
          "next_steps": ["Finish Telegram callback flow"],
          "exploration_items": ["Inspect Telegram callback UX patterns from similar bots"],
          "suggested_next_objective": "Ship daemon callback buttons for planner follow-up",
          "should_propose_follow_up": true
        }
        """
    )
    assert snapshot is not None
    assert snapshot.summary.startswith("Core loop")
    assert snapshot.workstreams[0].status == "in_progress"
    assert snapshot.exploration_items[0].startswith("Inspect Telegram")
    assert snapshot.should_propose_follow_up is True


def test_parse_plan_text_rejects_missing_required_field() -> None:
    snapshot = parse_plan_text(
        """
        {
          "summary": "Core loop is implemented and planner wiring is in progress.",
          "workstreams": [
            {
              "area": "Planner wiring",
              "status": "in_progress",
              "evidence": "Planner module exists.",
              "next_step": "Connect it to daemon."
            }
          ],
          "done_items": ["Planner schema added"],
          "remaining_items": ["Daemon follow-up buttons"],
          "risks": ["Need callback parsing"],
          "next_steps": ["Finish Telegram callback flow"],
          "exploration_items": ["Inspect Telegram callback UX patterns from similar bots"],
          "suggested_next_objective": "Ship daemon callback buttons for planner follow-up"
        }
        """
    )
    assert snapshot is None


def test_parse_plan_text_rejects_empty_follow_up_objective() -> None:
    snapshot = parse_plan_text(
        """
        {
          "summary": "Core loop is implemented and planner wiring is in progress.",
          "workstreams": [
            {
              "area": "Planner wiring",
              "status": "in_progress",
              "evidence": "Planner module exists.",
              "next_step": "Connect it to daemon."
            }
          ],
          "done_items": ["Planner schema added"],
          "remaining_items": ["Daemon follow-up buttons"],
          "risks": ["Need callback parsing"],
          "next_steps": ["Finish Telegram callback flow"],
          "exploration_items": ["Inspect Telegram callback UX patterns from similar bots"],
          "suggested_next_objective": "",
          "should_propose_follow_up": true
        }
        """
    )
    assert snapshot is None


def test_format_plan_markdown_includes_follow_up() -> None:
    snapshot = PlanSnapshot(
        plan_id="plan-1",
        generated_at="2026-03-12T00:00:00+00:00",
        trigger="final",
        terminal=True,
        summary="Implementation complete; follow-up benchmarking remains.",
        workstreams=[
            PlanWorkstream(
                area="Implementation",
                status="done",
                evidence="Core planner path merged.",
                next_step="Benchmark latency.",
            )
        ],
        done_items=["Planner agent integrated"],
        remaining_items=["Measure behavior on long sessions"],
        risks=["Concurrent planner sweeps share repo access"],
        next_steps=["Benchmark the daemon flow"],
        exploration_items=["Compare other Telegram bot follow-up patterns"],
        suggested_next_objective="Benchmark the planner-managed daemon flow end-to-end",
        should_propose_follow_up=True,
    )
    markdown = format_plan_markdown(
        objective="Add a planner manager agent",
        snapshot=snapshot,
        review=ReviewDecision(
            status="done",
            confidence=0.9,
            reason="Core feature merged.",
            next_action="Stop.",
        ),
        checks=[CheckResult(command="pytest -q", exit_code=0, passed=True, output_tail="ok")],
        stop_reason="Reviewer marked done.",
    )
    assert "Planning Snapshot" in markdown
    assert "Suggested Next Objective" in markdown
    assert "Benchmark the planner-managed daemon flow end-to-end" in markdown


def test_planner_evaluate_returns_plan_decision() -> None:
    class _FakeRunner:
        def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
            _ = kwargs
            payload = """
            {
              "summary": "Need one more follow-up run.",
              "workstreams": [
                {
                  "area": "Planner follow-up",
                  "status": "todo",
                  "evidence": "review passed",
                  "next_step": "launch follow-up"
                }
              ],
              "done_items": ["core implementation done"],
              "remaining_items": ["final benchmark"],
              "risks": ["benchmark dataset mismatch"],
              "next_steps": ["run benchmark"],
              "exploration_items": ["compare baseline"],
              "suggested_next_objective": "Run final benchmark and summarize metrics",
              "should_propose_follow_up": true
            }
            """
            return CodexRunResult(command=["codex", "exec"], exit_code=0, agent_messages=[payload])

    planner = Planner(runner=_FakeRunner())  # type: ignore[arg-type]
    decision = planner.evaluate(
        objective="ship feature",
        plan_messages=["focus on benchmark quality"],
        round_index=3,
        session_id="thread-1",
        latest_review_completion_summary="all checks passed",
        latest_plan_overview="",
        config=PlannerConfig(mode="auto"),
    )
    assert decision.follow_up_required is True
    assert "compare baseline" in decision.next_explore
    assert "Run final benchmark" in decision.main_instruction
    assert "benchmark dataset mismatch" in decision.review_instruction
    assert "Planning Snapshot" in decision.overview_markdown


def test_planner_evaluate_fallback_when_output_invalid() -> None:
    class _FakeRunner:
        def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
            _ = kwargs
            return CodexRunResult(command=["codex", "exec"], exit_code=1, agent_messages=["not json"])

    planner = Planner(runner=_FakeRunner())  # type: ignore[arg-type]
    decision = planner.evaluate(
        objective="ship feature",
        plan_messages=[],
        round_index=1,
        session_id=None,
        latest_review_completion_summary="",
        latest_plan_overview="",
        config=PlannerConfig(mode="record"),
    )
    assert decision.follow_up_required is False
    assert decision.main_instruction != ""
    assert decision.overview_markdown.strip() != ""

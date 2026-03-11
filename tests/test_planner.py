from codex_autoloop.models import CheckResult, PlanSnapshot, PlanWorkstream, ReviewDecision
from codex_autoloop.planner import format_plan_markdown, parse_plan_text


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
          "suggested_next_objective": "Ship daemon callback buttons for planner follow-up",
          "should_propose_follow_up": true
        }
        """
    )
    assert snapshot is not None
    assert snapshot.summary.startswith("Core loop")
    assert snapshot.workstreams[0].status == "in_progress"
    assert snapshot.should_propose_follow_up is True


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

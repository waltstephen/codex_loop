import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from codex_autoloop import cli
from codex_autoloop.apps import cli_app
from codex_autoloop.models import CodexRunResult, ReviewDecision


class _DummyBtwAgent:
    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        return

    def start_async(self, *args, **kwargs) -> bool:  # type: ignore[no-untyped-def]
        return False


class _DummyLoopEngine:
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.state_store = kwargs["state_store"]
        self.config = kwargs["config"]

    def run(self):  # type: ignore[no-untyped-def]
        pptx_path = Path(self.state_store.pptx_report_path())
        pptx_path.parent.mkdir(parents=True, exist_ok=True)
        pptx_path.write_bytes(b"pptx-smoke")
        self.state_store.record_pptx_report(str(pptx_path))
        return SimpleNamespace(
            success=True,
            session_id="thread-1",
            stop_reason="smoke test complete",
            rounds=[],
        )


class _PptxE2ERunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_exec(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        run_label = kwargs.get("run_label")
        if run_label == "main":
            return CodexRunResult(
                command=["codex", "exec"],
                exit_code=0,
                thread_id="thread-1",
                agent_messages=["DONE:\n- implemented\nREMAINING:\n- none\nBLOCKERS:\n- none"],
                turn_completed=True,
                turn_failed=False,
                fatal_error=None,
            )
        if run_label == "main-final-report":
            return CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=1,
                thread_id="thread-1",
                agent_messages=["report not written in test runner"],
                turn_completed=False,
                turn_failed=True,
                fatal_error="report write skipped in test runner",
            )
        if run_label == "main-pptx-report":
            # Agent attempt fails; fallback JS script will generate the PPTX
            return CodexRunResult(
                command=["codex", "exec", "resume"],
                exit_code=1,
                thread_id="thread-1",
                agent_messages=["pptx not written in test runner"],
                turn_completed=False,
                turn_failed=True,
                fatal_error="pptx write skipped in test runner",
            )
        raise AssertionError(f"unexpected run label: {run_label}")


class _DoneReviewer:
    def evaluate(self, **kwargs):  # type: ignore[no-untyped-def]
        return ReviewDecision(
            status="done",
            confidence=1.0,
            reason="complete",
            next_action="stop",
            round_summary_markdown="## Round Summary\n- done\n",
            completion_summary_markdown="## Completion\n- complete\n",
        )


def test_build_parser_accepts_pptx_report_file_option() -> None:
    args = cli.build_parser().parse_args(
        [
            "--pptx-report-file",
            "/tmp/run-report.pptx",
            "开始工作",
        ]
    )

    assert args.pptx_report_file == "/tmp/run-report.pptx"


def test_build_parser_help_mentions_pptx_report_file() -> None:
    help_text = cli.build_parser().format_help()

    assert "--pptx-report-file PPTX_REPORT_FILE" in help_text
    assert "auto-generated PPTX run report" in help_text


def test_run_cli_smoke_returns_pptx_report_payload(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    pptx_report = tmp_path / "artifacts" / "run-report.pptx"

    monkeypatch.setattr(cli_app, "build_codex_runner", lambda **kwargs: object())
    monkeypatch.setattr(cli_app, "BtwAgent", _DummyBtwAgent)
    monkeypatch.setattr(cli_app, "Reviewer", lambda runner: object())
    monkeypatch.setattr(cli_app, "Planner", lambda runner: object())
    monkeypatch.setattr(cli_app, "LoopEngine", _DummyLoopEngine)

    args = cli.build_parser().parse_args(
        [
            "--state-file",
            str(state_file),
            "--pptx-report-file",
            str(pptx_report),
            "开始工作",
        ]
    )
    if not args.planner:
        args.plan_mode = "off"
    if args.main_prompt_file is None:
        args.main_prompt_file = cli.resolve_main_prompt_file(
            state_file=args.state_file,
            control_file=args.control_file,
        )

    payload, exit_code = cli_app.run_cli(args)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["session_id"] == "thread-1"
    assert payload["pptx_report_file"] == str(pptx_report)
    assert payload["pptx_report_ready"] is True
    assert pptx_report.exists()


def test_run_cli_generates_default_pptx_report_artifact_end_to_end(tmp_path, monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    if shutil.which("node") is None:
        pytest.skip("node is required for real PPTX generation")
    if not (project_root / "node_modules" / "pptxgenjs").exists():
        pytest.skip("pptxgenjs runtime is not installed in this workspace")

    state_file = tmp_path / "state.json"
    default_pptx_report = tmp_path / "run-report.pptx"
    runner = _PptxE2ERunner()

    monkeypatch.setattr(cli_app, "build_codex_runner", lambda **kwargs: runner)
    monkeypatch.setattr(cli_app, "BtwAgent", _DummyBtwAgent)
    monkeypatch.setattr(cli_app, "Reviewer", lambda runner: _DoneReviewer())

    args = cli.build_parser().parse_args(
        [
            "--state-file",
            str(state_file),
            "--no-planner",
            "开始工作",
        ]
    )
    if not args.planner:
        args.plan_mode = "off"
    if args.main_prompt_file is None:
        args.main_prompt_file = cli.resolve_main_prompt_file(
            state_file=args.state_file,
            control_file=args.control_file,
        )

    payload, exit_code = cli_app.run_cli(args)

    assert exit_code == 0
    assert payload["success"] is True
    assert payload["session_id"] == "thread-1"
    assert payload["pptx_report_file"] == str(default_pptx_report)
    assert payload["pptx_report_ready"] is True
    assert default_pptx_report.exists()
    assert default_pptx_report.stat().st_size > 0
    assert any(call.get("run_label") == "main" for call in runner.calls)
    assert any(call.get("run_label") == "main-final-report" for call in runner.calls)
    assert any(call.get("run_label") == "main-pptx-report" for call in runner.calls)

    with zipfile.ZipFile(default_pptx_report) as archive:
        names = set(archive.namelist())
    assert "[Content_Types].xml" in names
    assert "ppt/presentation.xml" in names

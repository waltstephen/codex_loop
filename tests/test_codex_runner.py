from codex_autoloop.codex_runner import CodexRunner, RunnerOptions


def test_build_command_new_exec() -> None:
    runner = CodexRunner(codex_bin="codex")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            model="o3",
            full_auto=True,
            skip_git_repo_check=True,
            extra_args=["--search"],
            output_schema_path="/tmp/schema.json",
        ),
    )
    assert command[:3] == ["codex", "exec", "--json"]
    assert "--output-schema" in command
    assert command[-1] == "do work"


def test_build_command_resume() -> None:
    runner = CodexRunner(codex_bin="codex")
    command = runner._build_command(
        prompt="continue",
        resume_thread_id="thread123",
        options=RunnerOptions(output_schema_path="/tmp/schema.json"),
    )
    assert command[:4] == ["codex", "exec", "resume", "--json"]
    assert "--output-schema" not in command
    assert command[-2:] == ["thread123", "continue"]


def test_run_exec_marks_nonzero_exit_without_turn_completion_as_failed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fake_codex = tmp_path / "fake-codex"
    fake_codex.write_text("#!/bin/sh\nexit 17\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    runner = CodexRunner(codex_bin=str(fake_codex))
    result = runner.run_exec(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(),
    )

    assert result.exit_code == 17
    assert result.turn_completed is False
    assert result.turn_failed is True
    assert result.fatal_error == "Process exited with code 17 before turn completion."

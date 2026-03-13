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


def test_resolve_executable_uses_which_for_bare_command(monkeypatch) -> None:
    monkeypatch.setattr("codex_autoloop.codex_runner.shutil.which", lambda name: "C:/Users/test/AppData/Roaming/npm/codex.CMD")
    assert CodexRunner._resolve_executable("codex") == "C:/Users/test/AppData/Roaming/npm/codex.CMD"


def test_resolve_executable_keeps_explicit_path(monkeypatch) -> None:
    called = False

    def fake_which(name: str) -> str | None:
        nonlocal called
        called = True
        return None

    monkeypatch.setattr("codex_autoloop.codex_runner.shutil.which", fake_which)
    assert CodexRunner._resolve_executable(r".\tools\codex.cmd") == r".\tools\codex.cmd"
    assert called is False

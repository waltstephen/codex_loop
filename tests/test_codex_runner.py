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
    assert command[-1] == "-"


def test_build_command_resume() -> None:
    runner = CodexRunner(codex_bin="codex")
    command = runner._build_command(
        prompt="continue",
        resume_thread_id="thread123",
        options=RunnerOptions(output_schema_path="/tmp/schema.json"),
    )
    assert command[:4] == ["codex", "exec", "resume", "--json"]
    assert "--output-schema" not in command
    assert command[-2:] == ["thread123", "-"]


def test_build_command_claude_new_exec(tmp_path) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{\n  "type": "object"\n}\n', encoding="utf-8")
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            model="sonnet",
            reasoning_effort="xhigh",
            full_auto=True,
            extra_args=["--append-system-prompt", "Stay terse"],
            output_schema_path=str(schema_path),
        ),
    )
    assert command[:5] == ["claude", "-p", "--verbose", "--output-format", "stream-json"]
    assert "--model" in command
    assert "--effort" in command
    assert command[command.index("--effort") + 1] == "high"
    assert "--permission-mode" in command
    assert command[command.index("--permission-mode") + 1] == "acceptEdits"
    assert "--json-schema" in command
    assert command[command.index("--json-schema") + 1] == '{"type":"object"}'
    assert command[-2:] == ["--append-system-prompt", "Stay terse"]


def test_build_command_claude_resume_omits_schema() -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="continue",
        resume_thread_id="session-123",
        options=RunnerOptions(output_schema_path="/tmp/schema.json", dangerous_yolo=True),
    )
    assert command[:5] == ["claude", "-p", "--verbose", "--output-format", "stream-json"]
    assert "--json-schema" not in command
    assert command[-2:] == ["--resume", "session-123"]
    assert command[command.index("--permission-mode") + 1] == "bypassPermissions"


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


def test_run_exec_writes_prompt_to_stdin(monkeypatch) -> None:
    written: list[str] = []

    class _FakeStdin:
        def write(self, text: str) -> None:
            written.append(text)

        def close(self) -> None:
            written.append("<closed>")

    class _FakeProcess:
        def __init__(self) -> None:
            self.stdin = _FakeStdin()
            self.stdout = iter(())
            self.stderr = iter(())
            self.returncode = 0

        def poll(self):
            return 0

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

    monkeypatch.setattr(
        "codex_autoloop.codex_runner.subprocess.Popen",
        lambda *args, **kwargs: _FakeProcess(),
    )
    monkeypatch.setattr(
        "codex_autoloop.codex_runner.shutil.which",
        lambda name: "C:/Users/test/AppData/Roaming/npm/codex.CMD",
    )

    runner = CodexRunner(codex_bin="codex")
    result = runner.run_exec(
        prompt="line1\nline2",
        resume_thread_id=None,
        options=RunnerOptions(skip_git_repo_check=True),
        run_label="main",
    )

    assert result.command[-1] == "-"
    assert written == ["line1\nline2", "\n", "<closed>"]


def test_consume_claude_success_event_tracks_session_and_structured_output() -> None:
    agent_messages: list[str] = []
    thread_id, turn_completed, turn_failed, fatal_error = CodexRunner._consume_claude_event(
        event={
            "type": "result",
            "subtype": "success",
            "session_id": "session-123",
            "structured_output": {"status": "ok"},
        },
        thread_id=None,
        agent_messages=agent_messages,
        turn_completed=False,
        turn_failed=False,
        fatal_error=None,
    )
    assert thread_id == "session-123"
    assert turn_completed is True
    assert turn_failed is False
    assert fatal_error is None
    assert agent_messages == ['{"status": "ok"}']


def test_consume_claude_error_result_marks_failed() -> None:
    agent_messages: list[str] = []
    thread_id, turn_completed, turn_failed, fatal_error = CodexRunner._consume_claude_event(
        event={
            "type": "result",
            "subtype": "error_max_turns",
            "session_id": "session-456",
            "is_error": True,
            "result": "out of turns",
        },
        thread_id=None,
        agent_messages=agent_messages,
        turn_completed=False,
        turn_failed=False,
        fatal_error=None,
    )
    assert thread_id == "session-456"
    assert turn_completed is False
    assert turn_failed is True
    assert fatal_error == "out of turns"


def test_extract_claude_message_text_joins_text_parts() -> None:
    text = CodexRunner._extract_claude_message_text(
        {
            "content": [
                {"type": "text", "text": "line one"},
                {"type": "tool_use", "name": "bash"},
                {"type": "text", "text": "line two"},
            ]
        }
    )
    assert text == "line one\nline two"

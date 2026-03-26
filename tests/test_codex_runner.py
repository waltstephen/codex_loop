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


def test_build_command_copilot_uses_prompt_flag_and_tool_auto_approval() -> None:
    runner = CodexRunner(codex_bin="copilot", backend="copilot")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            reasoning_effort="xhigh",
            add_dirs=["/tmp/project"],
            plugin_dirs=["/plugins/main"],
            extra_args=["--agent", "coding-agent"],
        ),
    )
    assert command[:7] == [
        "copilot",
        "--output-format",
        "json",
        "--stream",
        "on",
        "--no-auto-update",
        "--no-ask-user",
    ]
    assert "--allow-all-tools" in command
    assert "--model" not in command
    assert command[command.index("--reasoning-effort") + 1] == "xhigh"
    assert command[command.index("--add-dir") + 1] == "/tmp/project"
    assert command[command.index("--plugin-dir") + 1] == "/plugins/main"
    assert command[-4:] == ["--agent", "coding-agent", "-p", "do work"]


def test_build_command_copilot_yolo_uses_highest_permission_mode() -> None:
    runner = CodexRunner(codex_bin="copilot", backend="copilot")
    command = runner._build_command(
        prompt="continue",
        resume_thread_id="session-123",
        options=RunnerOptions(dangerous_yolo=True),
    )
    assert "--yolo" in command
    assert "--allow-all-tools" not in command
    assert command[-4:] == ["--resume", "session-123", "-p", "continue"]


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


def test_run_exec_copilot_closes_stdin_without_writing_prompt(monkeypatch) -> None:
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
        lambda name: "/usr/bin/copilot",
    )

    runner = CodexRunner(codex_bin="copilot", backend="copilot")
    result = runner.run_exec(
        prompt="line1\nline2",
        resume_thread_id=None,
        options=RunnerOptions(),
        run_label="main",
    )

    assert result.command[-2:] == ["-p", "line1\nline2"]
    assert written == ["<closed>"]


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


def test_consume_copilot_success_event_tracks_session_and_message() -> None:
    agent_messages: list[str] = []
    thread_id, turn_completed, turn_failed, fatal_error = CodexRunner._consume_copilot_event(
        event={
            "type": "assistant.message",
            "data": {"content": "hello from copilot"},
        },
        thread_id=None,
        agent_messages=agent_messages,
        turn_completed=False,
        turn_failed=False,
        fatal_error=None,
    )
    assert thread_id is None
    assert turn_completed is False
    assert turn_failed is False
    assert fatal_error is None
    assert agent_messages == ["hello from copilot"]

    thread_id, turn_completed, turn_failed, fatal_error = CodexRunner._consume_copilot_event(
        event={
            "type": "result",
            "sessionId": "session-789",
            "exitCode": 0,
        },
        thread_id=thread_id,
        agent_messages=agent_messages,
        turn_completed=turn_completed,
        turn_failed=turn_failed,
        fatal_error=fatal_error,
    )
    assert thread_id == "session-789"
    assert turn_completed is True
    assert turn_failed is False
    assert fatal_error is None


def test_consume_copilot_error_event_marks_failed() -> None:
    agent_messages: list[str] = []
    thread_id, turn_completed, turn_failed, fatal_error = CodexRunner._consume_copilot_event(
        event={
            "type": "error",
            "data": {"message": "permission denied"},
        },
        thread_id="existing-session",
        agent_messages=agent_messages,
        turn_completed=False,
        turn_failed=False,
        fatal_error=None,
    )
    assert thread_id == "existing-session"
    assert turn_completed is False
    assert turn_failed is True
    assert fatal_error == "permission denied"


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


def test_build_command_claude_add_dirs(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            add_dirs=["/tmp", "/var/log"],
        ),
    )
    assert "--add-dir" in command
    assert command[command.index("--add-dir") + 1] == "/tmp"
    assert command[command.index("--add-dir", command.index("--add-dir") + 1) + 1] == "/var/log"


def test_build_command_claude_plugin_dirs(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            plugin_dirs=["/plugins", "/custom/plugins"],
        ),
    )
    assert "--plugin-dir" in command
    assert command[command.index("--plugin-dir") + 1] == "/plugins"
    assert command[command.index("--plugin-dir", command.index("--plugin-dir") + 1) + 1] == "/custom/plugins"


def test_build_command_claude_file_specs(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            file_specs=["file_abc:doc.txt", "file_xyz:readme.md"],
        ),
    )
    assert "--file" in command
    assert command[command.index("--file") + 1] == "file_abc:doc.txt"
    assert command[command.index("--file", command.index("--file") + 1) + 1] == "file_xyz:readme.md"


def test_build_command_claude_worktree(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            worktree_name="feature-branch",
        ),
    )
    assert "--worktree" in command
    assert command[command.index("--worktree") + 1] == "feature-branch"


def test_build_command_claude_worktree_default(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            worktree_name="default",
        ),
    )
    assert "--worktree" in command
    assert command[command.index("--worktree") + 1] == "default"


def test_build_command_claude_all_new_params_combined(tmp_path) -> None:
    runner = CodexRunner(codex_bin="claude", backend="claude")
    command = runner._build_command(
        prompt="do work",
        resume_thread_id=None,
        options=RunnerOptions(
            add_dirs=["/tmp"],
            plugin_dirs=["/plugins"],
            file_specs=["file_abc:doc.txt"],
            worktree_name="test-tree",
        ),
    )
    assert "--add-dir" in command
    assert "--plugin-dir" in command
    assert "--file" in command
    assert "--worktree" in command

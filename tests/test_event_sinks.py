import json
from pathlib import Path

from codex_autoloop.adapters.event_sinks import FeishuEventSink, TelegramEventSink, TerminalEventSink


class _FakeFeishuNotifier:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.messages: list[str] = []
        self.files: list[tuple[str, str]] = []
        self.closed = False

    def notify_event(self, event: dict[str, object]) -> None:
        self.events.append(event)

    def send_message(self, message: str) -> bool:
        self.messages.append(message)
        return True

    def send_local_file(self, path: str | Path, *, caption: str = "") -> bool:
        self.files.append((str(path), caption))
        return True

    def close(self) -> None:
        self.closed = True


def test_feishu_event_sink_forwards_events() -> None:
    notifier = _FakeFeishuNotifier()
    sink = FeishuEventSink(notifier=notifier, live_updates=False, live_interval_seconds=30)
    event = {"type": "loop.started", "round": 1}
    sink.handle_event(event)
    sink.close()
    assert notifier.events == [event]
    assert notifier.closed is True


def test_feishu_event_sink_live_updates_flush_on_close() -> None:
    notifier = _FakeFeishuNotifier()
    sink = FeishuEventSink(notifier=notifier, live_updates=True, live_interval_seconds=30)
    line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "hello from main"},
        }
    )
    sink.handle_stream_line("main.stdout", line)
    sink.close()
    assert len(notifier.messages) == 1
    assert "main: hello from main" in notifier.messages[0]


def test_feishu_event_sink_discards_live_update_backlog_after_completion() -> None:
    notifier = _FakeFeishuNotifier()
    sink = FeishuEventSink(notifier=notifier, live_updates=True, live_interval_seconds=30)
    line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "late main output"},
        }
    )

    sink.handle_stream_line("main.stdout", line)
    sink.handle_event({"type": "loop.completed", "success": True, "stop_reason": "done"})
    sink.close()

    assert not any("late main output" in message for message in notifier.messages)


def test_feishu_event_sink_sends_final_report_immediately(tmp_path: Path) -> None:
    notifier = _FakeFeishuNotifier()
    report = tmp_path / "final-task-report.md"
    report.write_text("# report\n\nbody\n", encoding="utf-8")
    sink = FeishuEventSink(notifier=notifier, live_updates=False, live_interval_seconds=30)

    sink.handle_event({"type": "final.report.ready", "path": str(report)})

    assert notifier.messages and "final task report ready" in notifier.messages[0]
    assert "# report" in notifier.messages[0]
    assert notifier.files == [(str(report), "ArgusBot final task report")]


def test_telegram_event_sink_sends_final_report_immediately(tmp_path: Path) -> None:
    notifier = _FakeFeishuNotifier()
    report = tmp_path / "final-task-report.md"
    report.write_text("# report\n\nbody\n", encoding="utf-8")
    sink = TelegramEventSink(notifier=notifier, live_updates=False, live_interval_seconds=30)

    sink.handle_event({"type": "final.report.ready", "path": str(report)})

    assert notifier.messages and "final task report ready" in notifier.messages[0]
    assert "# report" in notifier.messages[0]
    assert notifier.files == [(str(report), "ArgusBot final task report")]


def test_telegram_event_sink_discards_live_update_backlog_after_final_report(tmp_path: Path) -> None:
    notifier = _FakeFeishuNotifier()
    report = tmp_path / "final-task-report.md"
    report.write_text("# report\n\nbody\n", encoding="utf-8")
    sink = TelegramEventSink(notifier=notifier, live_updates=True, live_interval_seconds=30)
    line = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "late planner output"},
        }
    )

    sink.handle_stream_line("planner.stdout", line)
    sink.handle_event({"type": "final.report.ready", "path": str(report)})
    sink.close()

    assert not any("late planner output" in message for message in notifier.messages)
    assert any("final task report ready" in message for message in notifier.messages)


def test_terminal_event_sink_prints_final_report_markdown(tmp_path: Path, capsys) -> None:
    report = tmp_path / "final-task-report.md"
    report.write_text("# Final Report\n\nsummary\n", encoding="utf-8")
    sink = TerminalEventSink(live_terminal=False, verbose_events=False)

    sink.handle_event({"type": "final.report.ready", "path": str(report)})

    captured = capsys.readouterr()
    assert "final task report ready" in captured.out
    assert "# Final Report" in captured.out

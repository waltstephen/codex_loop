import json

from codex_autoloop.adapters.event_sinks import FeishuEventSink


class _FakeFeishuNotifier:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.messages: list[str] = []
        self.closed = False

    def notify_event(self, event: dict[str, object]) -> None:
        self.events.append(event)

    def send_message(self, message: str) -> None:
        self.messages.append(message)

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
    # Format is markdown with bold actor header
    assert "**main:**" in notifier.messages[0]
    assert "hello from main" in notifier.messages[0]


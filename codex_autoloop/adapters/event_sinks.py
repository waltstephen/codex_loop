from __future__ import annotations

import sys
from typing import Iterable

from ..core.ports import EventSink
from ..dashboard import DashboardStore
from ..feishu_adapter import FeishuNotifier
from ..live_updates import TelegramStreamReporter, TelegramStreamReporterConfig, extract_agent_message
from ..teams_adapter import TeamsNotifier
from ..telegram_notifier import TelegramNotifier


class CompositeEventSink:
    def __init__(self, sinks: Iterable[EventSink]) -> None:
        self._sinks = [sink for sink in sinks]

    def handle_event(self, event: dict[str, object]) -> None:
        for sink in self._sinks:
            sink.handle_event(event)

    def handle_stream_line(self, stream: str, line: str) -> None:
        for sink in self._sinks:
            sink.handle_stream_line(stream, line)

    def close(self) -> None:
        for sink in reversed(self._sinks):
            sink.close()


class TerminalEventSink:
    def __init__(self, *, live_terminal: bool, verbose_events: bool) -> None:
        self.live_terminal = live_terminal
        self.verbose_events = verbose_events

    def handle_event(self, event: dict[str, object]) -> None:
        return

    def handle_stream_line(self, stream: str, line: str) -> None:
        extracted = extract_agent_message(stream, line)
        if extracted is not None and self.live_terminal:
            actor, message = extracted
            print(f"\n[{actor} agent]\n{message}\n", file=sys.stderr)
        if not self.verbose_events:
            return
        prefix = f"[{stream}]"
        to_stderr = stream == "stderr" or stream.endswith(".stderr")
        print(f"{prefix} {line}", file=sys.stderr if to_stderr else sys.stdout)

    def close(self) -> None:
        return


class DashboardEventSink:
    def __init__(self, store: DashboardStore) -> None:
        self.store = store

    def handle_event(self, event: dict[str, object]) -> None:
        self.store.apply_loop_event(event)

    def handle_stream_line(self, stream: str, line: str) -> None:
        self.store.add_stream_line(stream=stream, line=line)

    def close(self) -> None:
        return


class TelegramEventSink:
    def __init__(
        self,
        *,
        notifier: TelegramNotifier,
        live_updates: bool,
        live_interval_seconds: int,
        on_error=None,
    ) -> None:
        self.notifier = notifier
        self._stream_reporter: TelegramStreamReporter | None = None
        if live_updates:
            self._stream_reporter = TelegramStreamReporter(
                notifier=notifier,
                config=TelegramStreamReporterConfig(interval_seconds=live_interval_seconds),
                on_error=on_error,
            )
            self._stream_reporter.start()

    def handle_event(self, event: dict[str, object]) -> None:
        self.notifier.notify_event(event)

    def handle_stream_line(self, stream: str, line: str) -> None:
        if self._stream_reporter is None:
            return
        extracted = extract_agent_message(stream, line)
        if extracted is None:
            return
        actor, message = extracted
        self._stream_reporter.add_message(actor=actor, message=message)

    def close(self) -> None:
        if self._stream_reporter is not None:
            self._stream_reporter.stop()
        self.notifier.close()


class FeishuEventSink:
    def __init__(
        self,
        *,
        notifier: FeishuNotifier,
        live_updates: bool,
        live_interval_seconds: int,
        on_error=None,
    ) -> None:
        self.notifier = notifier
        self._stream_reporter: TelegramStreamReporter | None = None
        if live_updates:
            self._stream_reporter = TelegramStreamReporter(
                notifier=notifier,
                config=TelegramStreamReporterConfig(interval_seconds=live_interval_seconds),
                on_error=on_error,
                channel_name="feishu",
            )
            self._stream_reporter.start()

    def handle_event(self, event: dict[str, object]) -> None:
        self.notifier.notify_event(event)

    def handle_stream_line(self, stream: str, line: str) -> None:
        if self._stream_reporter is None:
            return
        extracted = extract_agent_message(stream, line)
        if extracted is None:
            return
        actor, message = extracted
        self._stream_reporter.add_message(actor=actor, message=message)

    def close(self) -> None:
        if self._stream_reporter is not None:
            self._stream_reporter.stop()
        self.notifier.close()


class TeamsEventSink:
    def __init__(
        self,
        *,
        notifier: TeamsNotifier,
        live_updates: bool,
        live_interval_seconds: int,
        on_error=None,
    ) -> None:
        self.notifier = notifier
        self._stream_reporter: TelegramStreamReporter | None = None
        if live_updates:
            self._stream_reporter = TelegramStreamReporter(
                notifier=notifier,
                config=TelegramStreamReporterConfig(interval_seconds=live_interval_seconds),
                on_error=on_error,
                channel_name="teams",
            )
            self._stream_reporter.start()

    def handle_event(self, event: dict[str, object]) -> None:
        self.notifier.notify_event(event)

    def handle_stream_line(self, stream: str, line: str) -> None:
        if self._stream_reporter is None:
            return
        extracted = extract_agent_message(stream, line)
        if extracted is None:
            return
        actor, message = extracted
        self._stream_reporter.add_message(actor=actor, message=message)

    def close(self) -> None:
        if self._stream_reporter is not None:
            self._stream_reporter.stop()
        self.notifier.close()

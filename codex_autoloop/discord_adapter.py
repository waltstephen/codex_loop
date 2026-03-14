from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .command_protocol import parse_control_text


@dataclass
class DiscordCommand:
    kind: str
    text: str


ErrorCallback = Callable[[str], None]
CommandCallback = Callable[[DiscordCommand], None]


@dataclass
class DiscordConfig:
    bot_token: str
    channel_id: str
    events: set[str]
    timeout_seconds: int = 10


class DiscordNotifier:
    def __init__(self, config: DiscordConfig, on_error: ErrorCallback | None = None) -> None:
        self.config = config
        self.on_error = on_error
        self._send_message_url = f"https://discord.com/api/v10/channels/{config.channel_id}/messages"

    def notify_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type not in self.config.events:
            return
        message = format_discord_event_message(event)
        if message:
            self.send_message(message)

    def send_message(self, message: str) -> None:
        payload = json.dumps({"content": message[:1900]}, ensure_ascii=True).encode("utf-8")
        req = urllib.request.Request(
            self._send_message_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bot {self.config.bot_token}",
                "Content-Type": "application/json",
            },
        )
        self._perform(req)

    def close(self) -> None:
        return

    def _perform(self, req: urllib.request.Request) -> dict[str, Any] | None:
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            self._emit_error(f"Discord HTTP {exc.code}: {body[:300]}")
            return None
        except urllib.error.URLError as exc:
            self._emit_error(f"Discord network error: {exc}")
            return None
        except (TimeoutError, socket.timeout) as exc:
            self._emit_error(f"Discord timeout: {exc}")
            return None
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._emit_error("Discord response is not JSON.")
            return None

    def _emit_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)


class DiscordCommandPoller:
    def __init__(
        self,
        *,
        bot_token: str,
        channel_id: str,
        on_command: CommandCallback,
        on_error: ErrorCallback | None = None,
        poll_interval_seconds: int = 2,
        plain_text_kind: str = "inject",
    ) -> None:
        self.bot_token = bot_token
        self.channel_id = str(channel_id)
        self.on_command = on_command
        self.on_error = on_error
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self.plain_text_kind = plain_text_kind
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_message_id: str | None = None
        self._base_url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            for item in self._fetch_messages():
                message_id = str(item.get("id") or "").strip()
                if message_id:
                    self._last_message_id = message_id
                author = item.get("author")
                if isinstance(author, dict) and author.get("bot") is True:
                    continue
                content = str(item.get("content") or "").strip()
                parsed = parse_control_text(text=content, plain_text_kind=self.plain_text_kind)
                if parsed is None:
                    continue
                try:
                    self.on_command(DiscordCommand(kind=parsed.kind, text=parsed.text))
                except Exception as exc:
                    self._emit_error(f"discord command handler error: {exc}")
            self._stop_event.wait(self.poll_interval_seconds)

    def _fetch_messages(self) -> list[dict[str, Any]]:
        params = {"limit": "50"}
        if self._last_message_id:
            params["after"] = self._last_message_id
        url = f"{self._base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"Authorization": f"Bot {self.bot_token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            self._emit_error(f"discord get messages http {exc.code}: {body[:300]}")
            return []
        except urllib.error.URLError as exc:
            self._emit_error(f"discord get messages network error: {exc}")
            return []
        except (TimeoutError, socket.timeout) as exc:
            self._emit_error(f"discord get messages timeout: {exc}")
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._emit_error("discord get messages non-JSON response")
            return []
        if not isinstance(payload, list):
            return []
        items = [item for item in payload if isinstance(item, dict)]
        return list(reversed(items))

    def _emit_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)


def format_discord_event_message(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    if event_type == "loop.started":
        return f"[autoloop] started\nobjective={str(event.get('objective', ''))[:1200]}"
    if event_type == "round.review.completed":
        return (
            f"[autoloop] reviewer decision\n"
            f"round={event.get('round_index')} status={event.get('status')}\n"
            f"reason={str(event.get('reason', ''))[:1200]}"
        )
    if event_type == "plan.finalized":
        return (
            f"[autoloop] planner final\n"
            f"summary={str(event.get('summary', ''))[:800]}\n"
            f"next={str(event.get('suggested_next_objective', ''))[:800]}"
        )
    if event_type == "loop.completed":
        return (
            f"[autoloop] completed\n"
            f"success={event.get('success')} stop_reason={str(event.get('stop_reason', ''))[:1200]}"
        )
    return ""

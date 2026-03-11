from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    events: set[str]
    timeout_seconds: int = 10
    typing_enabled: bool = True
    typing_interval_seconds: int = 4


ErrorCallback = Callable[[str], None]


class TelegramNotifier:
    def __init__(self, config: TelegramConfig, on_error: ErrorCallback | None = None) -> None:
        self.config = config
        self.on_error = on_error
        base = f"https://api.telegram.org/bot{config.bot_token}"
        self.send_message_url = f"{base}/sendMessage"
        self.send_chat_action_url = f"{base}/sendChatAction"
        self.answer_callback_query_url = f"{base}/answerCallbackQuery"
        self._typing_stop = threading.Event()
        self._typing_thread: threading.Thread | None = None

    def notify_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type == "loop.started":
            self._start_typing()
        elif event_type == "loop.completed":
            self._stop_typing()

        if event_type not in self.config.events:
            return
        message = format_event_message(event)
        if not message:
            return
        self.send_message(message)

    def send_message(self, message: str, reply_markup: dict[str, Any] | None = None) -> None:
        payload = {
            "chat_id": self.config.chat_id,
            "text": message[:3900],
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=True)
        self._post_form(self.send_message_url, payload)

    def send_typing(self) -> None:
        payload = {
            "chat_id": self.config.chat_id,
            "action": "typing",
        }
        self._post_form(self.send_chat_action_url, payload)

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        payload = {
            "callback_query_id": callback_query_id,
        }
        if text:
            payload["text"] = text[:180]
        self._post_form(self.answer_callback_query_url, payload)

    def close(self) -> None:
        self._stop_typing()

    def _start_typing(self) -> None:
        if not self.config.typing_enabled:
            return
        if self._typing_thread is not None and self._typing_thread.is_alive():
            return
        self._typing_stop.clear()
        self._typing_thread = threading.Thread(target=self._typing_loop, daemon=True)
        self._typing_thread.start()

    def _stop_typing(self) -> None:
        self._typing_stop.set()
        if self._typing_thread is not None:
            self._typing_thread.join(timeout=2.0)
            self._typing_thread = None

    def _typing_loop(self) -> None:
        self.send_typing()
        interval = max(2, int(self.config.typing_interval_seconds))
        while not self._typing_stop.wait(interval):
            self.send_typing()

    def _post_form(self, url: str, payload: dict[str, Any]) -> bool:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            self._emit_error(f"Telegram HTTP {exc.code}: {body[:300]}")
            return False
        except urllib.error.URLError as exc:
            self._emit_error(f"Telegram network error: {exc}")
            return False

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            self._emit_error("Telegram response is not JSON.")
            return False
        if not parsed.get("ok"):
            desc = str(parsed.get("description", "unknown"))
            self._emit_error(f"Telegram API error: {desc}")
            return False
        return True

    def _emit_error(self, message: str) -> None:
        if self.on_error is None:
            return
        self.on_error(message)


def resolve_chat_id(
    *,
    bot_token: str,
    timeout_seconds: int = 90,
    poll_interval_seconds: int = 2,
    on_error: ErrorCallback | None = None,
) -> str | None:
    base = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    deadline = datetime.now(timezone.utc).timestamp() + max(5, timeout_seconds)
    while datetime.now(timezone.utc).timestamp() < deadline:
        req = urllib.request.Request(base, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            if on_error:
                on_error(f"getUpdates HTTP {exc.code}: {body[:300]}")
            return None
        except urllib.error.URLError as exc:
            if on_error:
                on_error(f"getUpdates network error: {exc}")
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            if on_error:
                on_error("getUpdates response is not JSON.")
            return None

        if not parsed.get("ok"):
            if on_error:
                on_error(f"getUpdates API error: {parsed.get('description', 'unknown')}")
            return None

        updates = parsed.get("result", [])
        if isinstance(updates, list):
            for update in reversed(updates):
                chat_id = extract_chat_id_from_update(update)
                if chat_id:
                    return chat_id

        threading.Event().wait(max(1, poll_interval_seconds))

    return None


def extract_chat_id_from_update(update: dict[str, Any]) -> str | None:
    candidates = [
        ("message", "chat", "id"),
        ("edited_message", "chat", "id"),
        ("channel_post", "chat", "id"),
        ("edited_channel_post", "chat", "id"),
        ("my_chat_member", "chat", "id"),
        ("chat_member", "chat", "id"),
        ("chat_join_request", "chat", "id"),
        ("callback_query", "message", "chat", "id"),
    ]
    for path in candidates:
        value: Any = update
        ok = True
        for key in path:
            if not isinstance(value, dict) or key not in value:
                ok = False
                break
            value = value[key]
        if ok and isinstance(value, (int, str)):
            return str(value)
    return None


def format_event_message(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    if event_type == "loop.started":
        objective = str(event.get("objective", ""))[:600]
        max_rounds = event.get("max_rounds")
        return (
            f"[autoloop] started {now}\n"
            f"max_rounds={max_rounds}\n"
            f"objective={objective}"
        )
    if event_type == "round.started":
        return (
            f"[autoloop] round started {now}\n"
            f"round={event.get('round_index')}\n"
            f"session_id={event.get('session_id')}"
        )
    if event_type == "round.main.completed":
        last_message = str(event.get("last_message", "")).strip().replace("\n", " ")
        last_message = last_message[:400]
        return (
            f"[autoloop] main completed {now}\n"
            f"round={event.get('round_index')} exit={event.get('exit_code')} "
            f"turn_completed={event.get('turn_completed')} turn_failed={event.get('turn_failed')}\n"
            f"session_id={event.get('session_id')}\n"
            f"summary={last_message}"
        )
    if event_type == "round.review.completed":
        reason = str(event.get("reason", "")).strip().replace("\n", " ")
        next_action = str(event.get("next_action", "")).strip().replace("\n", " ")
        return (
            f"[autoloop] reviewer decision {now}\n"
            f"round={event.get('round_index')} status={event.get('status')} "
            f"confidence={event.get('confidence')}\n"
            f"reason={reason[:320]}\n"
            f"next_action={next_action[:320]}"
        )
    if event_type == "loop.completed":
        return (
            f"[autoloop] completed {now}\n"
            f"success={event.get('success')}\n"
            f"stop_reason={str(event.get('stop_reason', ''))[:500]}"
        )
    if event_type in {"plan.updated", "plan.finalized"}:
        label = "planner final" if event_type == "plan.finalized" else "planner update"
        summary = str(event.get("summary", "")).strip().replace("\n", " ")
        next_objective = str(event.get("suggested_next_objective", "")).strip().replace("\n", " ")
        return (
            f"[autoloop] {label} {now}\n"
            f"trigger={event.get('trigger')} terminal={event.get('terminal')}\n"
            f"summary={summary[:320]}\n"
            f"next_objective={next_objective[:320]}"
        )
    return ""

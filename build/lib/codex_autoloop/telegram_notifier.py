from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4


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
        self.send_photo_url = f"{base}/sendPhoto"
        self.send_document_url = f"{base}/sendDocument"
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

    def send_message(self, message: str) -> None:
        payload = {
            "chat_id": self.config.chat_id,
            "text": message[:3900],
            "disable_web_page_preview": True,
        }
        self._post_form(self.send_message_url, payload)

    def send_typing(self) -> None:
        payload = {
            "chat_id": self.config.chat_id,
            "action": "typing",
        }
        self._post_form(self.send_chat_action_url, payload)

    def send_local_file(self, path: str | Path, *, caption: str = "") -> bool:
        file_path = Path(path)
        if not file_path.exists():
            self._emit_error(f"Telegram local file missing: {file_path}")
            return False
        try:
            file_bytes = file_path.read_bytes()
        except OSError as exc:
            self._emit_error(f"Telegram local file read failed: {exc}")
            return False
        url = self.send_photo_url if file_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"} else self.send_document_url
        field_name = "photo" if url == self.send_photo_url else "document"
        return self._post_multipart_file(
            url=url,
            field_name=field_name,
            file_name=file_path.name,
            file_bytes=file_bytes,
            caption=caption,
        )

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

    def _post_multipart_file(
        self,
        *,
        url: str,
        field_name: str,
        file_name: str,
        file_bytes: bytes,
        caption: str,
    ) -> bool:
        boundary = f"----codexautoloop{uuid4().hex}"
        body = bytearray()
        body.extend(_multipart_text_part(boundary, "chat_id", self.config.chat_id))
        if caption.strip():
            body.extend(_multipart_text_part(boundary, "caption", caption[:900]))
        body.extend(_multipart_text_part(boundary, "disable_content_type_detection", "false"))
        body.extend(_multipart_file_part(boundary, field_name, file_name, file_bytes))
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        req = urllib.request.Request(
            url,
            data=bytes(body),
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8")
            except Exception:
                body_text = ""
            self._emit_error(f"Telegram HTTP {exc.code}: {body_text[:300]}")
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


def _multipart_text_part(boundary: str, field: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def _multipart_file_part(boundary: str, field: str, file_name: str, file_bytes: bytes) -> bytes:
    safe_name = file_name.replace('"', "_")
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{safe_name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_bytes + b"\r\n"


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
    if event_type == "plan.completed":
        next_explore = str(event.get("next_explore", "")).strip().replace("\n", " ")
        main_instruction = str(event.get("main_instruction", "")).strip().replace("\n", " ")
        follow_up_required = event.get("follow_up_required")
        return (
            f"[autoloop] plan updated {now}\n"
            f"round={event.get('round_index')} mode={event.get('plan_mode')}\n"
            f"follow_up_required={follow_up_required}\n"
            f"next_explore={next_explore[:320]}\n"
            f"main_instruction={main_instruction[:320]}"
        )
    if event_type == "loop.completed":
        return (
            f"[autoloop] completed {now}\n"
            f"success={event.get('success')}\n"
            f"stop_reason={str(event.get('stop_reason', ''))[:500]}"
        )
    return ""

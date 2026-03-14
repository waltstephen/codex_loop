from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .telegram_control import normalize_command_prefix, parse_command_text, parse_mode_selection_text
from .telegram_notifier import format_event_message


@dataclass
class FeishuCommand:
    kind: str
    text: str


ErrorCallback = Callable[[str], None]
CommandCallback = Callable[[FeishuCommand], None]


@dataclass
class FeishuConfig:
    app_id: str
    app_secret: str
    chat_id: str
    events: set[str]
    receive_id_type: str = "chat_id"
    timeout_seconds: int = 10


class FeishuTokenManager:
    def __init__(self, *, app_id: str, app_secret: str, timeout_seconds: int, on_error: ErrorCallback | None) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout_seconds = timeout_seconds
        self.on_error = on_error
        self._token: str | None = None
        self._expires_at = 0.0

    def get_token(self) -> str | None:
        now = time.time()
        if self._token and now < self._expires_at - 30:
            return self._token
        payload = json.dumps(
            {"app_id": self.app_id, "app_secret": self.app_secret},
            ensure_ascii=True,
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        parsed = _perform_json_request(
            req,
            timeout_seconds=self.timeout_seconds,
            on_error=self.on_error,
            label="feishu auth",
        )
        if not isinstance(parsed, dict):
            return None
        token = parsed.get("tenant_access_token")
        expire = parsed.get("expire")
        if not isinstance(token, str) or not token.strip():
            _emit(self.on_error, "feishu auth missing tenant_access_token")
            return None
        self._token = token.strip()
        self._expires_at = now + int(expire or 7200)
        return self._token


class FeishuNotifier:
    def __init__(self, config: FeishuConfig, on_error: ErrorCallback | None = None) -> None:
        self.config = config
        self.on_error = on_error
        self._tokens = FeishuTokenManager(
            app_id=config.app_id,
            app_secret=config.app_secret,
            timeout_seconds=config.timeout_seconds,
            on_error=on_error,
        )

    def notify_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type not in self.config.events:
            return
        message = format_feishu_event_message(event)
        if message:
            self.send_message(message)

    def send_message(self, message: str) -> bool:
        token = self._tokens.get_token()
        if not token:
            return False
        ok = True
        for chunk in split_feishu_message(message):
            body = json.dumps(
                {
                    "receive_id": self.config.chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": chunk}, ensure_ascii=False),
                },
                ensure_ascii=False,
            ).encode("utf-8")
            req = urllib.request.Request(
                "https://open.feishu.cn/open-apis/im/v1/messages"
                + f"?{urllib.parse.urlencode({'receive_id_type': self.config.receive_id_type})}",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {token}",
                },
            )
            ok = (
                _perform_json_request(
                    req,
                    timeout_seconds=self.config.timeout_seconds,
                    on_error=self.on_error,
                    label="feishu send",
                )
                is not None
                and ok
            )
        return ok

    def close(self) -> None:
        return


class FeishuCommandPoller:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        chat_id: str,
        on_command: CommandCallback,
        on_error: ErrorCallback | None = None,
        poll_interval_seconds: int = 2,
        plain_text_kind: str = "inject",
    ) -> None:
        self.chat_id = chat_id
        self.on_command = on_command
        self.on_error = on_error
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self.plain_text_kind = plain_text_kind
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tokens = FeishuTokenManager(
            app_id=app_id,
            app_secret=app_secret,
            timeout_seconds=20,
            on_error=on_error,
        )
        self._last_message_id: str | None = None

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
                message_id = str(item.get("message_id") or "").strip()
                if message_id:
                    self._last_message_id = message_id
                if is_feishu_self_message(item):
                    continue
                if str(item.get("msg_type") or "") != "text":
                    continue
                text = extract_feishu_text(item)
                if not text:
                    continue
                parsed = parse_feishu_command_text(text=text, plain_text_kind=self.plain_text_kind)
                if parsed is None:
                    continue
                try:
                    self.on_command(parsed)
                except Exception as exc:
                    _emit(self.on_error, f"feishu command handler error: {exc}")
            self._stop_event.wait(self.poll_interval_seconds)

    def _fetch_messages(self) -> list[dict[str, Any]]:
        token = self._tokens.get_token()
        if not token:
            return []
        params = {
            "container_id_type": "chat",
            "container_id": self.chat_id,
            "sort_type": "ByCreateTimeDesc",
            "page_size": "50",
        }
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?" + urllib.parse.urlencode(params),
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        parsed = _perform_json_request(req, timeout_seconds=20, on_error=self.on_error, label="feishu list")
        if not isinstance(parsed, dict):
            return []
        data = parsed.get("data")
        if not isinstance(data, dict):
            return []
        items = data.get("items")
        if not isinstance(items, list):
            return []
        rows = [item for item in items if isinstance(item, dict)]
        if not self._last_message_id:
            if rows:
                latest_id = str(rows[0].get("message_id") or "").strip()
                if latest_id:
                    self._last_message_id = latest_id
            return []
        fresh: list[dict[str, Any]] = []
        for item in rows:
            if str(item.get("message_id") or "").strip() == self._last_message_id:
                break
            fresh.append(item)
        return list(reversed(fresh))


def parse_feishu_command_text(*, text: str, plain_text_kind: str) -> FeishuCommand | None:
    normalized = normalize_command_prefix(text.strip())
    if not normalized:
        return None
    parsed = parse_command_text(
        text=normalized,
        plain_text_as_inject=(plain_text_kind == "inject"),
    )
    if parsed is not None:
        return FeishuCommand(kind=parsed.kind, text=parsed.text)
    mode_selection = parse_mode_selection_text(normalized)
    if mode_selection is not None:
        return FeishuCommand(kind=mode_selection.kind, text=mode_selection.text)
    if normalized.startswith("/"):
        return None
    if plain_text_kind == "run":
        return FeishuCommand(kind="run", text=normalized)
    if plain_text_kind == "inject":
        return FeishuCommand(kind="inject", text=normalized)
    return None


def extract_feishu_text(item: dict[str, Any]) -> str:
    body = item.get("body")
    if not isinstance(body, dict):
        return ""
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        return ""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return ""
    text = parsed.get("text")
    return text.strip() if isinstance(text, str) else ""


def is_feishu_self_message(item: dict[str, Any]) -> bool:
    sender = item.get("sender")
    if isinstance(sender, dict):
        sender_type = str(sender.get("sender_type") or "").strip().lower()
        if sender_type in {"app", "bot"}:
            return True
    text = extract_feishu_text(item)
    lowered = text.lower()
    return lowered.startswith("[daemon]") or lowered.startswith("[autoloop]") or lowered.startswith("[btw]")


def format_feishu_event_message(event: dict[str, Any]) -> str:
    return format_event_message(event)


def split_feishu_message(message: str, *, max_chunk_chars: int = 1500) -> list[str]:
    text = (message or "").strip()
    if not text:
        return []
    if len(text) <= max_chunk_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chunk_chars:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_chunk_chars)
        if cut <= 0:
            cut = remaining.rfind(" ", 0, max_chunk_chars)
        if cut <= 0:
            cut = max_chunk_chars
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    total = len(chunks)
    if total <= 1:
        return chunks
    width = len(str(total))
    return [f"[{index + 1}/{total:0{width}d}]\n{chunk}" for index, chunk in enumerate(chunks)]


def _perform_json_request(
    req: urllib.request.Request,
    *,
    timeout_seconds: int,
    on_error: ErrorCallback | None,
    label: str,
) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        _emit(on_error, f"{label} http {exc.code}: {body[:300]}")
        return None
    except urllib.error.URLError as exc:
        _emit(on_error, f"{label} network error: {exc}")
        return None
    except (TimeoutError, socket.timeout) as exc:
        _emit(on_error, f"{label} timeout: {exc}")
        return None
    except OSError as exc:
        _emit(on_error, f"{label} os error: {exc}")
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        _emit(on_error, f"{label} non-JSON response")
        return None
    code = parsed.get("code", 0)
    if code not in {0, "0", None}:
        _emit(on_error, f"{label} api error: code={code} msg={parsed.get('msg', '')}")
        return None
    return parsed


def _emit(on_error: ErrorCallback | None, message: str) -> None:
    if on_error is not None:
        on_error(message)

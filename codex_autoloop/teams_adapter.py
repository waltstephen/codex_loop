from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .telegram_control import normalize_command_prefix, parse_command_text, parse_mode_selection_text
from .telegram_notifier import format_event_message

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
_TEAMS_MENTION_PREFIX = re.compile(r"^(?:<at>.*?</at>\s*)+", re.IGNORECASE | re.DOTALL)
_TEAMS_MENTION_TAG_RE = re.compile(r"<at>.*?</at>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_BOTFRAMEWORK_SCOPE = "https://api.botframework.com/.default"
_BOTFRAMEWORK_TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"


@dataclass
class TeamsCommand:
    kind: str
    text: str


ErrorCallback = Callable[[str], None]
CommandCallback = Callable[[TeamsCommand], None]


@dataclass
class TeamsConversationReference:
    service_url: str
    conversation_id: str
    bot_id: str
    bot_name: str = ""
    user_id: str = ""
    user_name: str = ""
    tenant_id: str = ""
    channel_id: str = "msteams"
    last_activity_id: str = ""


@dataclass
class TeamsConfig:
    app_id: str
    app_password: str
    events: set[str]
    conversation_id: str | None = None
    service_url: str | None = None
    tenant_id: str | None = None
    bot_name: str = "ArgusBot"
    timeout_seconds: int = 10
    endpoint_host: str = "0.0.0.0"
    endpoint_port: int = 3978
    endpoint_path: str = "/api/messages"
    reference_file: str | None = None


class TeamsTokenManager:
    def __init__(self, *, app_id: str, app_password: str, timeout_seconds: int, on_error: ErrorCallback | None) -> None:
        self.app_id = app_id
        self.app_password = app_password
        self.timeout_seconds = timeout_seconds
        self.on_error = on_error
        self._token: str | None = None
        self._expires_at = 0.0

    def get_token(self) -> str | None:
        now = time.time()
        if self._token and now < self._expires_at - 60:
            return self._token
        payload = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.app_id,
                "client_secret": self.app_password,
                "scope": _BOTFRAMEWORK_SCOPE,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            _BOTFRAMEWORK_TOKEN_URL,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        parsed = _perform_json_request(
            req,
            timeout_seconds=self.timeout_seconds,
            on_error=self.on_error,
            label="teams auth",
        )
        if not isinstance(parsed, dict):
            return None
        token = parsed.get("access_token")
        expires_in = parsed.get("expires_in")
        if not isinstance(token, str) or not token.strip():
            _emit(self.on_error, "teams auth missing access_token")
            return None
        self._token = token.strip()
        self._expires_at = now + int(expires_in or 3600)
        return self._token


class TeamsNotifier:
    def __init__(self, config: TeamsConfig, on_error: ErrorCallback | None = None) -> None:
        self.config = config
        self.on_error = on_error
        self._tokens = TeamsTokenManager(
            app_id=config.app_id,
            app_password=config.app_password,
            timeout_seconds=config.timeout_seconds,
            on_error=on_error,
        )
        self._lock = threading.Lock()
        self._missing_reference_reported = False
        self._reference = self._load_reference()
        if self._reference is None:
            seeded = build_seed_reference(config)
            if seeded is not None:
                self._reference = seeded
                self._persist_reference(seeded)

    def notify_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type not in self.config.events:
            return
        message = format_event_message(event)
        if message:
            self.send_message(message)

    def send_message(self, message: str) -> bool:
        token = self._tokens.get_token()
        if not token:
            return False
        reference = self.get_reference()
        if reference is None:
            self._report_missing_reference()
            return False
        ok = True
        for chunk in split_teams_message(message):
            ok = self._send_activity(
                token=token,
                reference=reference,
                payload=_message_activity(
                    text=chunk,
                    reference=reference,
                    bot_name=self.config.bot_name,
                    bot_app_id=self.config.app_id,
                ),
            ) and ok
        return ok

    def send_local_file(self, path: str | Path, *, caption: str = "") -> bool:
        file_path = Path(path)
        if not file_path.exists():
            _emit(self.on_error, f"teams local file missing: {file_path}")
            return False
        try:
            file_bytes = file_path.read_bytes()
        except OSError as exc:
            _emit(self.on_error, f"teams local file read failed: {exc}")
            return False

        token = self._tokens.get_token()
        if not token:
            return False
        reference = self.get_reference()
        if reference is None:
            self._report_missing_reference()
            return False

        mime_type, _ = mimetypes.guess_type(file_path.name)
        content_type = mime_type or "application/octet-stream"
        attachment = {
            "contentType": content_type,
            "contentUrl": _build_data_url(content_type=content_type, payload=file_bytes),
            "name": file_path.name,
        }
        message = caption.strip() or f"[teams attachment] {file_path.name}"
        ok = self._send_activity(
            token=token,
            reference=reference,
            payload=_message_activity(
                text=message,
                reference=reference,
                bot_name=self.config.bot_name,
                bot_app_id=self.config.app_id,
                attachments=[attachment],
            ),
        )
        if ok:
            return True
        suffix = file_path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS or suffix in VIDEO_EXTENSIONS:
            return False
        fallback = (
            f"{message}\n"
            f"[teams] file upload fallback: {file_path}"
        )
        return self.send_message(fallback)

    def update_reference_from_activity(self, activity: dict[str, Any]) -> None:
        reference = extract_teams_conversation_reference(
            activity=activity,
            fallback_bot_id=self.config.app_id,
            fallback_bot_name=self.config.bot_name,
        )
        if reference is None:
            return
        with self._lock:
            self._reference = reference
            self._missing_reference_reported = False
        self._persist_reference(reference)

    def get_reference(self) -> TeamsConversationReference | None:
        with self._lock:
            return self._reference

    def close(self) -> None:
        return

    def _send_activity(
        self,
        *,
        token: str,
        reference: TeamsConversationReference,
        payload: dict[str, Any],
    ) -> bool:
        url = _join_url(
            reference.service_url,
            f"/v3/conversations/{urllib.parse.quote(reference.conversation_id, safe='')}/activities",
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}",
            },
        )
        return (
            _perform_json_request(
                req,
                timeout_seconds=self.config.timeout_seconds,
                on_error=self.on_error,
                label="teams send",
            )
            is not None
        )

    def _load_reference(self) -> TeamsConversationReference | None:
        path = self._reference_path()
        if path is None or not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return _reference_from_dict(payload)

    def _persist_reference(self, reference: TeamsConversationReference) -> None:
        path = self._reference_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(reference), ensure_ascii=True, indent=2), encoding="utf-8")
        except OSError as exc:
            _emit(self.on_error, f"teams reference write failed: {exc}")

    def _reference_path(self) -> Path | None:
        raw = str(self.config.reference_file or "").strip()
        if not raw:
            return None
        return Path(raw).resolve()

    def _report_missing_reference(self) -> None:
        with self._lock:
            if self._missing_reference_reported:
                return
            self._missing_reference_reported = True
        _emit(self.on_error, "teams conversation reference is not available yet")


class TeamsCommandListener:
    def __init__(
        self,
        *,
        config: TeamsConfig,
        on_command: CommandCallback,
        on_error: ErrorCallback | None = None,
        plain_text_kind: str = "inject",
        notifier: TeamsNotifier | None = None,
    ) -> None:
        self.config = config
        self.on_command = on_command
        self.on_error = on_error
        self.plain_text_kind = plain_text_kind
        self.notifier = notifier
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return
        server = ThreadingHTTPServer((self.config.endpoint_host, int(self.config.endpoint_port)), self._build_handler())
        server.daemon_threads = True
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        server.shutdown()
        server.server_close()
        self._server = None
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _build_handler(self):
        parent = self
        expected_path = normalize_teams_endpoint_path(parent.config.endpoint_path)

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = json.dumps({"ok": True, "channel": "teams"}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                try:
                    raw = self.rfile.read(max(0, length))
                    payload = json.loads(raw.decode("utf-8"))
                except Exception:
                    self.send_response(400)
                    self.end_headers()
                    return
                if isinstance(payload, dict):
                    parent._handle_activity(payload)
                response = json.dumps({"ok": True}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        return _Handler

    def _handle_activity(self, activity: dict[str, Any]) -> None:
        if self.notifier is not None:
            self.notifier.update_reference_from_activity(activity)
        activity_type = str(activity.get("type", "")).strip().lower()
        if activity_type != "message":
            return
        parsed = parse_teams_command_text(
            text=extract_teams_activity_text(activity),
            plain_text_kind=self.plain_text_kind,
        )
        if parsed is None:
            return
        try:
            self.on_command(parsed)
        except Exception as exc:
            _emit(self.on_error, f"teams command handler error: {exc}")


def build_seed_reference(config: TeamsConfig) -> TeamsConversationReference | None:
    service_url = str(config.service_url or "").strip()
    conversation_id = str(config.conversation_id or "").strip()
    if not service_url or not conversation_id:
        return None
    return TeamsConversationReference(
        service_url=service_url,
        conversation_id=conversation_id,
        bot_id=config.app_id,
        bot_name=config.bot_name,
        tenant_id=str(config.tenant_id or "").strip(),
    )


def normalize_teams_endpoint_path(value: str) -> str:
    raw = str(value or "").strip() or "/api/messages"
    if not raw.startswith("/"):
        raw = "/" + raw
    return raw


def extract_teams_activity_text(activity: dict[str, Any]) -> str:
    text = activity.get("text")
    if isinstance(text, str) and text.strip():
        return strip_leading_teams_mentions(_strip_teams_markup(text))
    value = activity.get("value")
    if isinstance(value, dict):
        nested = value.get("text")
        if isinstance(nested, str) and nested.strip():
            return strip_leading_teams_mentions(_strip_teams_markup(nested))
    return ""


def parse_teams_command_text(*, text: str, plain_text_kind: str) -> TeamsCommand | None:
    normalized = strip_leading_teams_mentions(normalize_command_prefix(text.strip()))
    if not normalized:
        return None
    parsed = parse_command_text(
        text=normalized,
        plain_text_as_inject=(plain_text_kind == "inject"),
    )
    if parsed is not None:
        return TeamsCommand(kind=parsed.kind, text=parsed.text)
    mode_selection = parse_mode_selection_text(normalized)
    if mode_selection is not None:
        return TeamsCommand(kind=mode_selection.kind, text=mode_selection.text)
    if normalized.startswith("/"):
        return None
    if plain_text_kind == "run":
        return TeamsCommand(kind="run", text=normalized)
    if plain_text_kind == "inject":
        return TeamsCommand(kind="inject", text=normalized)
    return None


def strip_leading_teams_mentions(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    previous = None
    current = normalized
    while current and current != previous:
        previous = current
        current = _TEAMS_MENTION_PREFIX.sub("", current).lstrip()
    return current


def extract_teams_conversation_reference(
    *,
    activity: dict[str, Any],
    fallback_bot_id: str,
    fallback_bot_name: str = "ArgusBot",
) -> TeamsConversationReference | None:
    service_url = str(activity.get("serviceUrl") or "").strip()
    conversation = activity.get("conversation")
    if not isinstance(conversation, dict):
        return None
    conversation_id = str(conversation.get("id") or "").strip()
    if not service_url or not conversation_id:
        return None
    recipient = activity.get("recipient")
    sender = activity.get("from")
    bot_id = fallback_bot_id
    bot_name = fallback_bot_name
    if isinstance(recipient, dict):
        bot_id = str(recipient.get("id") or bot_id).strip() or bot_id
        bot_name = str(recipient.get("name") or bot_name).strip() or bot_name
    user_id = ""
    user_name = ""
    if isinstance(sender, dict):
        user_id = str(sender.get("id") or "").strip()
        user_name = str(sender.get("name") or "").strip()
    channel_data = activity.get("channelData")
    tenant_id = ""
    if isinstance(channel_data, dict):
        tenant = channel_data.get("tenant")
        if isinstance(tenant, dict):
            tenant_id = str(tenant.get("id") or "").strip()
    return TeamsConversationReference(
        service_url=service_url,
        conversation_id=conversation_id,
        bot_id=bot_id,
        bot_name=bot_name,
        user_id=user_id,
        user_name=user_name,
        tenant_id=tenant_id,
        channel_id=str(activity.get("channelId") or "msteams").strip() or "msteams",
        last_activity_id=str(activity.get("id") or "").strip(),
    )


def split_teams_message(text: str, *, max_chunk_chars: int = 3200) -> list[str]:
    content = str(text or "").strip()
    if not content:
        return []
    chunks: list[str] = []
    remaining = content
    max_len = max(200, int(max_chunk_chars))
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        window = remaining[:max_len]
        split_at = window.rfind("\n")
        if split_at < max_len // 3:
            split_at = window.rfind(" ")
        if split_at <= 0:
            split_at = max_len
        chunk = remaining[:split_at]
        chunks.append(chunk)
        remaining = remaining[split_at:].lstrip("\n ")
    return chunks


def _message_activity(
    *,
    text: str,
    reference: TeamsConversationReference,
    bot_name: str,
    bot_app_id: str,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "message",
        "text": text,
        "conversation": {"id": reference.conversation_id},
        "from": {
            "id": reference.bot_id or bot_app_id,
            "name": reference.bot_name or bot_name,
        },
    }
    if reference.user_id:
        payload["recipient"] = {
            "id": reference.user_id,
            "name": reference.user_name,
        }
    if reference.tenant_id:
        payload["channelData"] = {"tenant": {"id": reference.tenant_id}}
    if attachments:
        payload["attachments"] = attachments
    return payload


def _strip_teams_markup(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = _TEAMS_MENTION_TAG_RE.sub("", text)
    text = (
        text.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
        .replace("</div>", "\n")
        .replace("</p>", "\n")
    )
    text = _HTML_TAG_RE.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _build_data_url(*, content_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _reference_from_dict(payload: dict[str, Any]) -> TeamsConversationReference | None:
    service_url = str(payload.get("service_url") or "").strip()
    conversation_id = str(payload.get("conversation_id") or "").strip()
    bot_id = str(payload.get("bot_id") or "").strip()
    if not service_url or not conversation_id or not bot_id:
        return None
    return TeamsConversationReference(
        service_url=service_url,
        conversation_id=conversation_id,
        bot_id=bot_id,
        bot_name=str(payload.get("bot_name") or "").strip(),
        user_id=str(payload.get("user_id") or "").strip(),
        user_name=str(payload.get("user_name") or "").strip(),
        tenant_id=str(payload.get("tenant_id") or "").strip(),
        channel_id=str(payload.get("channel_id") or "msteams").strip() or "msteams",
        last_activity_id=str(payload.get("last_activity_id") or "").strip(),
    )


def _join_url(base: str, path: str) -> str:
    return str(base or "").rstrip("/") + path


def _perform_json_request(
    req: urllib.request.Request,
    *,
    timeout_seconds: int,
    on_error: ErrorCallback | None,
    label: str,
) -> dict[str, Any] | list[Any] | None:
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        _emit(on_error, f"{label} HTTP {exc.code}: {body[:300]}")
        return None
    except urllib.error.URLError as exc:
        _emit(on_error, f"{label} network error: {exc}")
        return None
    except (TimeoutError, socket.timeout) as exc:
        _emit(on_error, f"{label} timeout: {exc}")
        return None
    except OSError as exc:
        _emit(on_error, f"{label} network error: {exc}")
        return None
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        _emit(on_error, f"{label} non-JSON response")
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _emit(callback: ErrorCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)

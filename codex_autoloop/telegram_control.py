from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from uuid import uuid4
from typing import Any, Callable


@dataclass
class TelegramCommand:
    kind: str
    text: str
    callback_query_id: str | None = None


CommandCallback = Callable[[TelegramCommand], None]
ErrorCallback = Callable[[str], None]


@dataclass
class TelegramAudioFile:
    file_id: str
    file_name: str


class TelegramWhisperTranscriber:
    def __init__(
        self,
        *,
        bot_token: str,
        api_key: str | None = None,
        model: str = "whisper-1",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 90,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        self.model = (model or "whisper-1").strip() or "whisper-1"
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.on_error = on_error
        self._missing_api_key_reported = False
        self._get_file_url = f"https://api.telegram.org/bot{self.bot_token}/getFile"
        self._download_base_url = f"https://api.telegram.org/file/bot{self.bot_token}"

    def transcribe_update(self, *, update: dict[str, Any], expected_chat_id: str) -> str | None:
        message = extract_message_for_chat(update=update, expected_chat_id=expected_chat_id)
        if message is None:
            return None
        audio_file = extract_audio_file_from_message(message)
        if audio_file is None:
            return None
        if not self.api_key:
            if not self._missing_api_key_reported:
                self._emit_error(
                    "telegram voice transcription skipped: missing OPENAI_API_KEY or --telegram-control-whisper-api-key"
                )
                self._missing_api_key_reported = True
            return None
        file_path = self._resolve_file_path(audio_file.file_id)
        if not file_path:
            return None
        file_bytes = self._download_file(file_path)
        if file_bytes is None:
            return None
        text = self._transcribe_file(file_bytes=file_bytes, file_name=audio_file.file_name)
        if text is None:
            return None
        stripped = text.strip()
        if not stripped:
            return None
        return stripped

    def _resolve_file_path(self, file_id: str) -> str | None:
        url = f"{self._get_file_url}?{urllib.parse.urlencode({'file_id': file_id})}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            self._emit_error(f"telegram getFile network error: {exc}")
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._emit_error("telegram getFile non-JSON response")
            return None
        if not payload.get("ok"):
            self._emit_error(f"telegram getFile api error: {payload.get('description', 'unknown')}")
            return None
        result = payload.get("result")
        if not isinstance(result, dict):
            return None
        file_path = result.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            self._emit_error("telegram getFile missing file_path")
            return None
        return file_path

    def _download_file(self, file_path: str) -> bytes | None:
        quoted = urllib.parse.quote(file_path, safe="/")
        url = f"{self._download_base_url}/{quoted}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.URLError as exc:
            self._emit_error(f"telegram file download network error: {exc}")
            return None

    def _transcribe_file(self, *, file_bytes: bytes, file_name: str) -> str | None:
        boundary = f"----codexautoloop{uuid4().hex}"
        body = bytearray()
        body.extend(_multipart_text_part(boundary, "model", self.model))
        body.extend(_multipart_file_part(boundary, "file", file_name, file_bytes))
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            f"{self.base_url}/audio/transcriptions",
            data=bytes(body),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8")
            except Exception:
                body_text = ""
            self._emit_error(f"whisper http error {exc.code}: {body_text[:250]}")
            return None
        except urllib.error.URLError as exc:
            self._emit_error(f"whisper network error: {exc}")
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._emit_error("whisper non-JSON response")
            return None
        text = payload.get("text")
        if not isinstance(text, str):
            self._emit_error("whisper response missing text")
            return None
        return text

    def _emit_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)


class TelegramCommandPoller:
    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        on_command: CommandCallback,
        on_error: ErrorCallback | None = None,
        poll_interval_seconds: int = 2,
        long_poll_timeout_seconds: int = 20,
        plain_text_as_inject: bool = True,
        whisper_enabled: bool = True,
        whisper_api_key: str | None = None,
        whisper_model: str = "whisper-1",
        whisper_base_url: str = "https://api.openai.com/v1",
        whisper_timeout_seconds: int = 90,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.on_command = on_command
        self.on_error = on_error
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self.long_poll_timeout_seconds = max(1, int(long_poll_timeout_seconds))
        self.plain_text_as_inject = plain_text_as_inject
        self.whisper_enabled = whisper_enabled
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset: int | None = None
        self._base_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        self._transcriber: TelegramWhisperTranscriber | None = None
        if self.whisper_enabled:
            self._transcriber = TelegramWhisperTranscriber(
                bot_token=self.bot_token,
                api_key=whisper_api_key,
                model=whisper_model,
                base_url=whisper_base_url,
                timeout_seconds=whisper_timeout_seconds,
                on_error=self._emit_error,
            )

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
            updates = self._fetch_updates()
            if updates is None:
                self._stop_event.wait(self.poll_interval_seconds)
                continue
            if not updates:
                continue
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    self._offset = update_id + 1
                command = parse_command_from_update(
                    update=update,
                    expected_chat_id=self.chat_id,
                    plain_text_as_inject=self.plain_text_as_inject,
                )
                if command is None and self._transcriber is not None:
                    transcript = self._transcriber.transcribe_update(
                        update=update,
                        expected_chat_id=self.chat_id,
                    )
                    if transcript:
                        command = parse_command_text(
                            text=transcript,
                            plain_text_as_inject=self.plain_text_as_inject,
                        )
                if command is None:
                    continue
                try:
                    self.on_command(command)
                except Exception as exc:
                    self._emit_error(f"telegram command handler error: {exc}")

    def _fetch_updates(self) -> list[dict[str, Any]] | None:
        query = {
            "timeout": str(self.long_poll_timeout_seconds),
        }
        if self._offset is not None:
            query["offset"] = str(self._offset)
        url = self._base_url + "?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.long_poll_timeout_seconds + 10) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            self._emit_error(f"telegram getUpdates network error: {exc}")
            return None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._emit_error("telegram getUpdates non-JSON response")
            return None

        if not payload.get("ok"):
            self._emit_error(f"telegram getUpdates api error: {payload.get('description', 'unknown')}")
            return None
        result = payload.get("result", [])
        if not isinstance(result, list):
            return []
        return [item for item in result if isinstance(item, dict)]

    def _emit_error(self, message: str) -> None:
        if self.on_error is not None:
            self.on_error(message)


def parse_command_from_update(
    *,
    update: dict[str, Any],
    expected_chat_id: str,
    plain_text_as_inject: bool,
) -> TelegramCommand | None:
    callback_query = update.get("callback_query")
    if isinstance(callback_query, dict):
        message = callback_query.get("message")
        data = callback_query.get("data")
        callback_query_id = callback_query.get("id")
        if (
            isinstance(message, dict)
            and isinstance(data, str)
            and isinstance(callback_query_id, str)
            and _message_matches_chat(message=message, expected_chat_id=expected_chat_id)
        ):
            if data.startswith("plan_run:"):
                return TelegramCommand(
                    kind="plan-run",
                    text=data.split(":", 1)[1],
                    callback_query_id=callback_query_id,
                )
            if data.startswith("plan_skip:"):
                return TelegramCommand(
                    kind="plan-skip",
                    text=data.split(":", 1)[1],
                    callback_query_id=callback_query_id,
                )
    message = extract_message_for_chat(update=update, expected_chat_id=expected_chat_id)
    if message is None:
        return None
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return parse_command_text(text=text, plain_text_as_inject=plain_text_as_inject)
    caption = message.get("caption")
    if isinstance(caption, str) and caption.strip():
        return parse_command_text(text=caption, plain_text_as_inject=plain_text_as_inject)
    return None


def extract_message_for_chat(*, update: dict[str, Any], expected_chat_id: str) -> dict[str, Any] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    if not _message_matches_chat(message=message, expected_chat_id=expected_chat_id):
        return None
    return message


def _message_matches_chat(*, message: dict[str, Any], expected_chat_id: str) -> bool:
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return False
    chat_id = chat.get("id")
    return str(chat_id) == str(expected_chat_id)


def extract_audio_file_from_message(message: dict[str, Any]) -> TelegramAudioFile | None:
    voice = message.get("voice")
    if isinstance(voice, dict):
        file_id = voice.get("file_id")
        if isinstance(file_id, str) and file_id.strip():
            return TelegramAudioFile(file_id=file_id, file_name="voice.ogg")

    audio = message.get("audio")
    if isinstance(audio, dict):
        file_id = audio.get("file_id")
        if isinstance(file_id, str) and file_id.strip():
            file_name = audio.get("file_name")
            if not isinstance(file_name, str) or not file_name.strip():
                file_name = "audio.mp3"
            return TelegramAudioFile(file_id=file_id, file_name=file_name)

    document = message.get("document")
    if isinstance(document, dict):
        mime_type = str(document.get("mime_type", "")).lower()
        if mime_type.startswith("audio/"):
            file_id = document.get("file_id")
            if isinstance(file_id, str) and file_id.strip():
                file_name = document.get("file_name")
                if not isinstance(file_name, str) or not file_name.strip():
                    file_name = "audio.bin"
                return TelegramAudioFile(file_id=file_id, file_name=file_name)
    return None


def parse_command_text(*, text: str, plain_text_as_inject: bool) -> TelegramCommand | None:
    content = text.strip()
    if not content:
        return None
    if content.startswith("/inject "):
        return TelegramCommand(kind="inject", text=content[len("/inject ") :].strip())
    if content == "/inject":
        return None
    if content.startswith("/interrupt "):
        return TelegramCommand(kind="inject", text=content[len("/interrupt ") :].strip())
    if content.startswith("/run "):
        return TelegramCommand(kind="run", text=content[len("/run ") :].strip())
    if content == "/run":
        return None
    if content in {"/stop", "/halt"}:
        return TelegramCommand(kind="stop", text="")
    if content in {"/daemon-stop", "/shutdown-daemon"}:
        return TelegramCommand(kind="daemon-stop", text="")
    if content in {"/status", "/stat"}:
        return TelegramCommand(kind="status", text="")
    if content in {"/help", "/commands"}:
        return TelegramCommand(kind="help", text="")
    if content.startswith("/"):
        return None
    if plain_text_as_inject:
        return TelegramCommand(kind="inject", text=content)
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

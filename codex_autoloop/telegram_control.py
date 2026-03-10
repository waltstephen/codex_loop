from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TelegramCommand:
    kind: str
    text: str


CommandCallback = Callable[[TelegramCommand], None]
ErrorCallback = Callable[[str], None]


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
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.on_command = on_command
        self.on_error = on_error
        self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        self.long_poll_timeout_seconds = max(1, int(long_poll_timeout_seconds))
        self.plain_text_as_inject = plain_text_as_inject
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset: int | None = None
        self._base_url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"

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
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    if str(chat_id) != str(expected_chat_id):
        return None
    text = message.get("text")
    if not isinstance(text, str):
        return None
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
    if content in {"/status", "/stat"}:
        return TelegramCommand(kind="status", text="")
    if content in {"/help", "/commands"}:
        return TelegramCommand(kind="help", text="")
    if content.startswith("/") and not plain_text_as_inject:
        return None
    if content.startswith("/") and plain_text_as_inject:
        return None
    if plain_text_as_inject:
        return TelegramCommand(kind="inject", text=content)
    return None

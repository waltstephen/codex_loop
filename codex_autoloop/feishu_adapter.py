from __future__ import annotations

import json
import mimetypes
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .telegram_control import normalize_command_prefix, parse_command_text, parse_mode_selection_text
from .telegram_notifier import format_event_message
from .md_checker import validate_and_fix_markdown, quick_fix_for_feishu, check_markdown
from .output_extractor import (
    extract_and_format_reviewer,
    extract_and_format_planner,
    extract_message_content,
)

__all__ = [
    # Core classes
    'FeishuNotifier',
    'FeishuCommandPoller',
    'FeishuConfig',
    'FeishuCommand',
    # Constants
    'FEISHU_CARD_MAX_BYTES',
    'FEISHU_TEXT_MAX_BYTES',
    'FEISHU_ERROR_CODE_MESSAGE_TOO_LONG',
    'FEISHU_ERROR_CODE_CARD_CONTENT_FAILED',
    'FEISHU_COLOR_GREEN',
    'FEISHU_COLOR_BLUE',
    'FEISHU_COLOR_YELLOW',
    'FEISHU_COLOR_RED',
    'FEISHU_COLOR_ORANGE',
    'FEISHU_COLOR_PURPLE',
    'FEISHU_COLOR_GRAY',
    # Utilities
    'split_feishu_message',
    'markdown_to_feishu_post',
    'build_interactive_card',
    'format_feishu_event_card',
    'format_feishu_event_message',
    'strip_leading_feishu_mentions',
    'parse_feishu_command_text',
    'is_feishu_self_message',
    'extract_feishu_text',
]

_FEISHU_MENTION_PREFIX = re.compile(r"^(?:@[_\w-]+\s+)+")
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

# 飞书消息长度限制 (官方文档)
# 卡片消息：30 KB (请求体最大长度，包含模板数据)
# 文本消息：150 KB
# 错误码：230025 - 消息体长度超出限制
#        230099 - 创建卡片内容失败
FEISHU_CARD_MAX_BYTES = 30 * 1024  # 30 KB
FEISHU_TEXT_MAX_BYTES = 150 * 1024  # 150 KB
FEISHU_ERROR_CODE_MESSAGE_TOO_LONG = 230025
FEISHU_ERROR_CODE_CARD_CONTENT_FAILED = 230099

# 飞书卡片颜色模板 (用于不同事件状态)
FEISHU_COLOR_GREEN = "green"    # 成功/完成
FEISHU_COLOR_BLUE = "blue"      # 进行中/信息
FEISHU_COLOR_YELLOW = "yellow"  # 警告/继续
FEISHU_COLOR_RED = "red"        # 失败/受阻
FEISHU_COLOR_ORANGE = "orange"  # 已停止
FEISHU_COLOR_PURPLE = "purple"  # 规划相关
FEISHU_COLOR_GRAY = "gray"      # 中性/默认


def markdown_to_feishu_post(text: str, title: str = "ArgusBot Update") -> dict[str, Any]:
    """Convert Markdown text to Feishu post message format.

    Feishu post message format:
    {
      "msg_type": "post",
      "content": {
        "zh_cn": {
          "title": "...",
          "content": [
            [{"tag": "text", "text": "..."}],
            ...
          ]
        }
      }
    }

    Handles:
    - Bold: **text** → clean text
    - Lists: - item → • item
    - Headers: ### title → title with newlines
    - Code blocks: ```lang ... ``` → preserved content
    - Regular paragraphs
    """
    lines = text.split('\n')
    content_blocks: list[list[dict[str, Any]]] = []

    in_code_block = False
    code_block_content: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Handle code block start/end
        if stripped.startswith('```'):
            if in_code_block:
                # End of code block - emit as formatted code
                code_text = '\n'.join(code_block_content)
                content_blocks.append([{
                    "tag": "text",
                    "text": f"\n```\n{code_text}\n```\n"
                }])
                code_block_content = []
                in_code_block = False
            else:
                # Start of code block
                in_code_block = True
            continue

        if in_code_block:
            code_block_content.append(line)
            continue

        # Skip empty lines
        if not stripped:
            continue

        # Handle bold: **text**
        if re.match(r'^\*\*.*\*\*$', stripped):
            clean_text = stripped.replace('**', '')
            content_blocks.append([{
                "tag": "text",
                "text": clean_text
            }])
            continue

        # Handle list items: - item
        if re.match(r'^-\s+.*$', stripped):
            item_text = re.sub(r'^-\s+', '', stripped)
            content_blocks.append([{
                "tag": "text",
                "text": f"• {item_text}"
            }])
            continue

        # Handle headers: ### title → title with newlines
        if re.match(r'^###\s+.*$', stripped):
            title_text = re.sub(r'^###\s+', '', stripped)
            content_blocks.append([{
                "tag": "text",
                "text": f"\n{title_text}\n"
            }])
            continue

        # Handle ## headers (main sections)
        if re.match(r'^##\s+.*$', stripped):
            title_text = re.sub(r'^##\s+', '', stripped)
            content_blocks.append([{
                "tag": "text",
                "text": f"\n\n**{title_text}**\n"
            }])
            continue

        # Regular paragraphs
        if stripped:
            content_blocks.append([{
                "tag": "text",
                "text": stripped
            }])

    # Handle unclosed code block
    if in_code_block and code_block_content:
        code_text = '\n'.join(code_block_content)
        content_blocks.append([{
            "tag": "text",
            "text": f"\n```\n{code_text}\n```\n"
        }])

    return {
        "msg_type": "post",
        "content": {
            "zh_cn": {
                "title": title,
                "content": content_blocks if content_blocks else [[{"tag": "text", "text": text}]]
            }
        }
    }


def build_interactive_card(
    title: str,
    content: str,
    template: str = "blue",
    actions: list[dict] | None = None,
    wide_screen_mode: bool = True,
) -> dict[str, Any]:
    """Build an interactive card message for Feishu.

    Args:
        title: Card header title text
        content: Main content text (supports Markdown-like formatting)
        template: Header color template (blue, green, red, yellow, purple, gray)
        actions: Optional list of action buttons
        wide_screen_mode: Enable wide screen mode

    Returns:
        Interactive card message dict ready to be sent
    """
    elements: list[dict] = []

    # Add content as div element
    if content:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content
            }
        })

    # Add action buttons if provided
    if actions:
        elements.append({
            "tag": "action",
            "actions": actions
        })

    card_content = {
        "config": {
            "wide_screen_mode": wide_screen_mode
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": title
            },
            "template": template
        },
        "elements": elements
    }

    return card_content


# def _strip_markdown_code_blocks(text: str) -> str:
#     """Remove markdown code block markers (```lang ... ```) from text.

#     Feishu post messages don't support Markdown rendering, so we strip
#     the code block markers to display the content as plain text.

#     Example:
#         Input: "```json\\n{...}\\n```"
#         Output: "{...}"
#     """
#     if not text:
#         return text

#     result = text
#     # Pattern: ```(language)?\\n(content)```
#     # Match code blocks and keep only the content
#     pattern = r"```(\w*)?\s*(.*?)\s*```"

#     def replace_code_block(match: re.Match) -> str:
#         content = match.group(2) or ""
#         return content.strip()

#     result = re.sub(pattern, replace_code_block, result, flags=re.DOTALL)
#     return result


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
    wide_screen_mode: bool = True
    card_template_id: str | None = None


class FeishuTokenManager:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        timeout_seconds: int,
        on_error: ErrorCallback | None,
    ) -> None:
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

        # Try to format as interactive card first
        card_result = format_feishu_event_card(event)
        if card_result:
            title, content, template = card_result
            self.send_card_message(title=title, content=content, template=template)
        else:
            # Fallback to text-based message for events that don't support cards
            message = format_feishu_event_message(event)
            if message:
                self.send_message(message)

    def send_message(self, message: str) -> bool:
        """Send a text message using interactive card format with markdown element.

        Uses interactive card format with markdown element for proper Markdown rendering.
        This supports:
        - Headers: # H1, ## H2, ### H3
        - Bold: **text**
        - Italic: *text*
        - Lists: - item
        - Links: [text](url)
        - Code blocks: ```lang ... ```

        Before sending, validates and fixes common Markdown issues:
        - Unclosed code blocks
        - Missing newlines after headers
        - Incorrect list formatting

        Note: Message chunks are limited to FEISHU_CARD_MAX_BYTES (30 KB) to avoid
        error 230025 (message too long) and 230099 (card content failed).
        """
        token = self._tokens.get_token()
        if not token:
            return False

        # Validate and fix Markdown before sending
        fixed_message = validate_and_fix_markdown(message)

        ok = True
        for chunk in split_feishu_message(fixed_message, max_chunk_bytes=FEISHU_CARD_MAX_BYTES):
            # Build card content with markdown element for Markdown support
            card_content = {
                "config": {
                    "wide_screen_mode": self.config.wide_screen_mode
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "ArgusBot Update"
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": chunk
                    }
                ]
            }
            ok = (
                self._send_structured_message(
                    token=token,
                    msg_type="interactive",
                    content=card_content,
                )
                and ok
            )
        return ok

    def send_local_file(self, path: str | Path, *, caption: str = "") -> bool:
        token = self._tokens.get_token()
        if not token:
            return False
        file_path = Path(path)
        if not file_path.exists():
            _emit(self.on_error, f"feishu local file missing: {file_path}")
            return False
        try:
            file_bytes = file_path.read_bytes()
        except OSError as exc:
            _emit(self.on_error, f"feishu local file read failed: {exc}")
            return False

        suffix = file_path.suffix.lower()
        if suffix in _IMAGE_EXTENSIONS:
            image_key = self._upload_image(token=token, file_name=file_path.name, file_bytes=file_bytes)
            if not image_key:
                return False
            ok = self._send_structured_message(
                token=token,
                msg_type="image",
                content={"image_key": image_key},
            )
        else:
            is_video = suffix in _VIDEO_EXTENSIONS
            file_type = "mp4" if is_video and suffix == ".mp4" else "stream"
            file_key = self._upload_file(
                token=token,
                file_name=file_path.name,
                file_bytes=file_bytes,
                file_type=file_type,
            )
            if not file_key:
                return False
            ok = self._send_structured_message(
                token=token,
                msg_type="file",
                content={"file_key": file_key},
            )

        if caption.strip():
            ok = (
                self._send_structured_message(
                    token=token,
                    msg_type="text",
                    content={"text": caption[:1500]},
                )
                and ok
            )
        return ok

    # def _send_post_message(
    #     self,
    #     *,
    #     token: str,
    #     text_content: str,
    # ) -> bool:
    #     """Send a post message with Markdown converted to Feishu format.

    #     Uses markdown_to_feishu_post() to convert Markdown to structured
    #     Feishu post format with proper handling of:
    #     - Headers (##, ###)
    #     - Bold (**text**)
    #     - List items (- item)
    #     - Code blocks (```lang ... ```)
    #     """
    #     # Convert markdown to feishu post format
    #     post_data = markdown_to_feishu_post(text_content)

    #     body = json.dumps(
    #         {
    #             "receive_id": self.config.chat_id,
    #             "msg_type": "post",
    #             "content": json.dumps(post_data["content"], ensure_ascii=False),
    #         },
    #         ensure_ascii=False,
    #     ).encode("utf-8")
    #     req = urllib.request.Request(
    #         "https://open.feishu.cn/open-apis/im/v1/messages"
    #         + f"?{urllib.parse.urlencode({'receive_id_type': self.config.receive_id_type})}",
    #         data=body,
    #         method="POST",
    #         headers={
    #             "Content-Type": "application/json; charset=utf-8",
    #             "Authorization": f"Bearer {token}",
    #         },
    #     )
    #     return (
    #         _perform_json_request(
    #             req,
    #             timeout_seconds=self.config.timeout_seconds,
    #             on_error=self.on_error,
    #             label="feishu post send",
    #         )
    #         is not None
    #     )

    def _send_structured_message(
        self,
        *,
        token: str,
        msg_type: str,
        content: dict[str, Any],
    ) -> bool:
        """Send a structured message (interactive card, image, file, etc.).

        Handles Feishu API error codes:
        - 230025: Message too long - truncates content and retries
        - 230099: Card content failed - logs detailed error
        """
        body = json.dumps(
            {
                "receive_id": self.config.chat_id,
                "msg_type": msg_type,
                "content": json.dumps(content, ensure_ascii=False),
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
        return (
            _perform_json_request(
                req,
                timeout_seconds=self.config.timeout_seconds,
                on_error=self.on_error,
                label="feishu send",
            )
            is not None
        )

    def _upload_image(self, *, token: str, file_name: str, file_bytes: bytes) -> str | None:
        parsed = self._post_multipart(
            token=token,
            url="https://open.feishu.cn/open-apis/im/v1/images",
            field_name="image",
            file_name=file_name,
            file_bytes=file_bytes,
            extra_form_fields={"image_type": "message"},
            label="feishu upload image",
        )
        if not isinstance(parsed, dict):
            return None
        data = parsed.get("data")
        if not isinstance(data, dict):
            _emit(self.on_error, "feishu upload image missing data")
            return None
        image_key = data.get("image_key")
        if not isinstance(image_key, str) or not image_key.strip():
            _emit(self.on_error, "feishu upload image missing image_key")
            return None
        return image_key.strip()

    def _upload_file(
        self,
        *,
        token: str,
        file_name: str,
        file_bytes: bytes,
        file_type: str,
    ) -> str | None:
        parsed = self._post_multipart(
            token=token,
            url="https://open.feishu.cn/open-apis/im/v1/files",
            field_name="file",
            file_name=file_name,
            file_bytes=file_bytes,
            extra_form_fields={"file_type": file_type, "file_name": file_name},
            label="feishu upload file",
        )
        if not isinstance(parsed, dict):
            return None
        data = parsed.get("data")
        if not isinstance(data, dict):
            _emit(self.on_error, "feishu upload file missing data")
            return None
        file_key = data.get("file_key")
        if not isinstance(file_key, str) or not file_key.strip():
            _emit(self.on_error, "feishu upload file missing file_key")
            return None
        return file_key.strip()

    def _post_multipart(
        self,
        *,
        token: str,
        url: str,
        field_name: str,
        file_name: str,
        file_bytes: bytes,
        extra_form_fields: dict[str, str] | None,
        label: str,
    ) -> dict[str, Any] | None:
        boundary = f"----argusbot{uuid4().hex}"
        body = bytearray()
        if extra_form_fields:
            for key, value in extra_form_fields.items():
                body.extend(_multipart_text_part(boundary, key, value))
        guessed_mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        body.extend(
            _multipart_file_part(
                boundary,
                field_name,
                file_name,
                file_bytes,
                content_type=guessed_mime_type,
            )
        )
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        req = urllib.request.Request(
            url,
            data=bytes(body),
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        return _perform_json_request(
            req,
            timeout_seconds=self.config.timeout_seconds,
            on_error=self.on_error,
            label=label,
        )

    def close(self) -> None:
        return

    def send_card_message(
        self,
        title: str,
        content: str,
        template: str = "blue",
        actions: list[dict] | None = None,
    ) -> bool:
        """Send an interactive card message.

        Args:
            title: Card header title
            content: Main content (supports lark_md Markdown-like syntax)
            template: Header color (blue, green, red, yellow, purple, gray)
            actions: Optional list of button actions

        Returns:
            True if sent successfully, False otherwise
        """
        token = self._tokens.get_token()
        if not token:
            return False

        card_content = build_interactive_card(
            title=title,
            content=content,
            template=template,
            actions=actions,
            wide_screen_mode=self.config.wide_screen_mode,
        )

        return self._send_structured_message(
            token=token,
            msg_type="interactive",
            content=card_content,
        )


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
    normalized = strip_leading_feishu_mentions(normalized)
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


def strip_leading_feishu_mentions(text: str) -> str:
    normalized = normalize_command_prefix((text or "").strip())
    if not normalized:
        return ""
    previous = None
    current = normalized
    while current and current != previous:
        previous = current
        current = _FEISHU_MENTION_PREFIX.sub("", current).lstrip()
    return current


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
    """Format event message as text (legacy, for backward compatibility)."""
    return format_event_message(event)


def format_feishu_event_card(event: dict[str, Any]) -> tuple[str, str, str] | None:
    """Format event as interactive card (title, content, template_color).

    Returns:
        Tuple of (title, content, template) or None if event should not produce a card

    Event types handled:
        - loop.started: Blue card with objective
        - round.review.completed: Color based on status (green=done, yellow=continue, red=blocked)
        - loop.completed: Green summary card
        - reviewer.output: Reviewer 输出，提取 Markdown 字段
        - planner.output: Planner 输出，提取 Markdown 字段
    """
    event_type = str(event.get("type", ""))

    if event_type == "loop.started":
        objective = event.get("objective", "Unknown task")
        return (
            "任务启动",
            f"**目标:** {objective}\n\nArgusBot 已开始执行任务...",
            FEISHU_COLOR_BLUE
        )

    if event_type == "round.review.completed":
        review = event.get("review", {})
        status = str(review.get("status", "unknown"))
        reason = review.get("reason", "")
        round_num = event.get("round", 1)

        status_map = {
            "done": ("审核通过", FEISHU_COLOR_GREEN),
            "continue": ("继续执行", FEISHU_COLOR_YELLOW),
            "blocked": ("执行受阻", FEISHU_COLOR_RED),
        }
        title, color = status_map.get(status, ("审核状态", FEISHU_COLOR_BLUE))

        content = f"**第 {round_num} 轮审核**\n\n"
        content += f"**状态:** {status}\n"
        if reason:
            content += f"\n{reason}"

        return title, content, color

    if event_type == "reviewer.output":
        # 处理 Reviewer JSON 输出，提取并格式化为结构化 Markdown
        raw_output = event.get("raw_output", "")
        if raw_output:
            formatted = extract_and_format_reviewer(raw_output)
            return ("🔍 Reviewer 评审报告", formatted, FEISHU_COLOR_BLUE)
        return None

    if event_type == "planner.output":
        # 处理 Planner JSON 输出，提取并格式化为结构化 Markdown
        raw_output = event.get("raw_output", "")
        if raw_output:
            formatted = extract_and_format_planner(raw_output)
            return ("📋 Planner 规划报告", formatted, FEISHU_COLOR_PURPLE)
        return None

    if event_type == "plan.completed":
        # 处理 Planner 完成事件，包含原始 JSON 输出
        raw_output = event.get("raw_output", "")
        if raw_output:
            formatted = extract_and_format_planner(raw_output)
            return ("📋 Planner 规划报告", formatted, FEISHU_COLOR_PURPLE)
        # 如果没有 raw_output，使用传统格式
        summary = str(event.get("main_instruction", ""))[:400]
        return ("📋 Planner 更新", summary, FEISHU_COLOR_PURPLE)

    if event_type == "loop.completed":
        rounds = event.get("rounds", [])
        total_rounds = len(rounds)
        exit_code = event.get("exit_code", 0)
        objective = event.get("objective", "任务")
        stop_reason = event.get("stop_reason", "")

        # 根据结束原因选择不同颜色
        # - FEISHU_COLOR_GREEN: 成功完成 (exit_code=0 且通过检查)
        # - FEISHU_COLOR_RED: 失败/受阻
        # - FEISHU_COLOR_YELLOW: 达到最大轮次
        # - FEISHU_COLOR_ORANGE: 被用户停止
        color = FEISHU_COLOR_GREEN
        status_text = "成功"

        if exit_code != 0:
            color = FEISHU_COLOR_RED
            status_text = "失败"
        elif "blocked" in str(stop_reason).lower():
            color = FEISHU_COLOR_RED
            status_text = "受阻"
        elif "max rounds" in str(stop_reason).lower():
            color = FEISHU_COLOR_YELLOW
            status_text = "达到最大轮次"
        elif "stopped" in str(stop_reason).lower() or "operator" in str(stop_reason).lower():
            color = FEISHU_COLOR_ORANGE
            status_text = "已停止"

        content = f"**任务{status_text}**\n\n"
        content += f"**目标:** {objective}\n"
        content += f"**总轮数:** {total_rounds}\n"
        content += f"**状态码:** {exit_code}\n"
        if stop_reason:
            content += f"**原因:** {stop_reason[:200]}"

        return "任务完成", content, color

    return None


def split_feishu_message(
    message: str,
    *,
    max_chunk_chars: int = 1500,
    max_chunk_bytes: int | None = None,
) -> list[str]:
    """Split message into chunks that fit within Feishu API limits.

    Args:
        message: Message text to split
        max_chunk_chars: Maximum characters per chunk (default: 1500)
        max_chunk_bytes: Maximum bytes per chunk (default: None, use char limit only)
                        When set, ensures JSON-encoded message fits within limit

    Returns:
        List of message chunks with [n/total] prefix for multi-chunk messages

    Note:
        When max_chunk_bytes is set, the function accounts for JSON encoding overhead
        (escape sequences like \\n, unicode, etc.) to ensure the final request body
        stays within Feishu's 30 KB card message limit.
    """
    text = (message or "").strip()
    if not text:
        return []

    # Determine effective limit (bytes-aware)
    effective_limit = max_chunk_chars
    if max_chunk_bytes is not None:
        # Reserve ~30% space for JSON overhead when encoding
        # JSON escapes: \n → \\n, unicode → \\uXXXX, quotes → \\"
        estimated_overhead_factor = 1.3
        byte_limit = int(max_chunk_bytes / estimated_overhead_factor)
        # Use the smaller of char limit or byte-derived limit
        # (UTF-8: 1 char ≈ 1-3 bytes for common text)
        effective_limit = min(max_chunk_chars, byte_limit)

    if len(text.encode('utf-8')) <= (max_chunk_bytes or float('inf')):
        # Entire message fits within byte limit
        if len(text) <= effective_limit:
            return [text]
        # Message fits in bytes but exceeds char limit - use char-based splitting

    chunks: list[str] = []
    remaining = text
    while remaining:
        current_limit = effective_limit
        if max_chunk_bytes is not None:
            # Adjust limit based on actual byte size of current segment
            test_segment = remaining[:current_limit]
            test_bytes = len(_json_encode_for_feishu(test_segment).encode('utf-8'))
            # If exceeds byte limit, reduce character count
            while test_bytes > max_chunk_bytes and current_limit > 50:
                current_limit -= 50
                test_segment = remaining[:current_limit]
                test_bytes = len(_json_encode_for_feishu(test_segment).encode('utf-8'))

        if len(remaining) <= current_limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, current_limit)
        if cut <= 0:
            cut = remaining.rfind(" ", 0, current_limit)
        if cut <= 0:
            cut = current_limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()

    total = len(chunks)
    if total <= 1:
        return chunks
    width = len(str(total))
    return [f"[{index + 1}/{total:0{width}d}]\n{chunk}" for index, chunk in enumerate(chunks)]


def _json_encode_for_feishu(text: str) -> str:
    """JSON encode text as Feishu API would receive it (for size estimation)."""
    return json.dumps(text, ensure_ascii=False)


def _perform_json_request(
    req: urllib.request.Request,
    *,
    timeout_seconds: int,
    on_error: ErrorCallback | None,
    label: str,
    max_retries: int = 2,
) -> dict[str, Any] | None:
    """Perform HTTP request with optional retry for transient errors.

    Retries on SSL/EOF errors and connection reset errors that are often transient.
    """
    attempt = 0
    last_error: Exception | None = None

    while attempt <= max_retries:
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
            reason = str(exc.reason)
            # Retry on SSL/EOF errors
            if "UNEXPECTED_EOF" in reason or "EOF occurred" in reason or "connection reset" in reason.lower():
                last_error = exc
                attempt += 1
                if attempt <= max_retries:
                    time.sleep(0.5 * attempt)  # Exponential backoff
                    continue
            _emit(on_error, f"{label} network error: {exc}")
            return None
        except (TimeoutError, socket.timeout) as exc:
            _emit(on_error, f"{label} timeout: {exc}")
            return None
        except OSError as exc:
            reason = str(exc)
            # Retry on connection reset errors
            if "Connection reset" in reason or "Broken pipe" in reason:
                last_error = exc
                attempt += 1
                if attempt <= max_retries:
                    time.sleep(0.5 * attempt)
                    continue
            _emit(on_error, f"{label} os error: {exc}")
            return None

        # Success - parse and return
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            _emit(on_error, f"{label} non-JSON response")
            return None
        code = parsed.get("code", 0)
        if code not in {0, "0", None}:
            # Handle Feishu-specific error codes
            code_str = str(code)
            msg = parsed.get('msg', '')

            if code_str == str(FEISHU_ERROR_CODE_MESSAGE_TOO_LONG):
                # 230025: Message too long - caller should truncate and retry
                _emit(on_error, f"{label} message too long (code={code}): {msg}")
            elif code_str == str(FEISHU_ERROR_CODE_CARD_CONTENT_FAILED):
                # 230099: Card content failed - may contain markdown syntax issues
                _emit(on_error, f"{label} card content failed (code={code}): {msg}")
            else:
                _emit(on_error, f"{label} api error: code={code} msg={msg}")
            return None
        return parsed

    # All retries exhausted
    _emit(on_error, f"{label} failed after {max_retries} retries: {last_error}")
    return None


def _emit(on_error: ErrorCallback | None, message: str) -> None:
    if on_error is not None:
        on_error(message)


def _multipart_text_part(boundary: str, field: str, value: str) -> bytes:
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def _multipart_file_part(
    boundary: str,
    field: str,
    file_name: str,
    file_bytes: bytes,
    *,
    content_type: str,
) -> bytes:
    safe_name = file_name.replace('"', "_")
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{safe_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + file_bytes + b"\r\n"

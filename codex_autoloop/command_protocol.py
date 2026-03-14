from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    kind: str
    text: str = ""


def parse_control_text(*, text: str, plain_text_kind: str = "inject") -> ParsedCommand | None:
    content = (text or "").strip()
    if not content:
        return None
    if content.startswith("/inject "):
        return ParsedCommand(kind="inject", text=content[len("/inject ") :].strip())
    if content == "/inject":
        return None
    if content.startswith("/interrupt "):
        return ParsedCommand(kind="inject", text=content[len("/interrupt ") :].strip())
    if content.startswith("/run "):
        return ParsedCommand(kind="run", text=content[len("/run ") :].strip())
    if content == "/run":
        return None
    if content in {"/stop", "/halt"}:
        return ParsedCommand(kind="stop", text="")
    if content in {"/daemon-stop", "/shutdown-daemon", "/disable"}:
        return ParsedCommand(kind="daemon-stop", text="")
    if content in {"/status", "/stat"}:
        return ParsedCommand(kind="status", text="")
    if content in {"/fresh", "/fresh-session", "/new-session"}:
        return ParsedCommand(kind="fresh-session", text="")
    if content in {"/new"}:
        return ParsedCommand(kind="new", text="")
    if content in {"/help", "/commands"}:
        return ParsedCommand(kind="help", text="")
    if content in {"/mode"}:
        return ParsedCommand(kind="mode-menu", text="")
    if content.startswith("/mode "):
        raw = content[len("/mode ") :].strip().lower()
        mapping = {"1": "off", "2": "auto", "3": "record"}
        normalized = mapping.get(raw, raw)
        if normalized in {"off", "auto", "record"}:
            return ParsedCommand(kind="mode", text=normalized)
        return ParsedCommand(kind="mode-invalid", text=raw)
    if content.startswith("/btw "):
        return ParsedCommand(kind="btw", text=content[len("/btw ") :].strip())
    if content == "/btw":
        return None
    if content.startswith("/plan "):
        return ParsedCommand(kind="plan", text=content[len("/plan ") :].strip())
    if content == "/plan":
        return None
    if content.startswith("/review "):
        return ParsedCommand(kind="review", text=content[len("/review ") :].strip())
    if content == "/review":
        return None
    if content in {"/show-main-prompt"}:
        return ParsedCommand(kind="show-main-prompt", text="")
    if content in {"/show-plan"}:
        return ParsedCommand(kind="show-plan", text="")
    if content in {"/show-plan-context"}:
        return ParsedCommand(kind="show-plan-context", text="")
    if content == "/show-review":
        return ParsedCommand(kind="show-review", text="")
    if content.startswith("/show-review "):
        return ParsedCommand(kind="show-review", text=content[len("/show-review ") :].strip())
    if content in {"/show-review-context"}:
        return ParsedCommand(kind="show-review-context", text="")
    if content.startswith("/"):
        return None
    return ParsedCommand(kind=plain_text_kind, text=content)

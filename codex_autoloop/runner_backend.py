from __future__ import annotations

from typing import Literal


RunnerBackend = Literal["codex", "claude"]

BACKEND_CODEX: RunnerBackend = "codex"
BACKEND_CLAUDE: RunnerBackend = "claude"
RUNNER_BACKEND_CHOICES: tuple[RunnerBackend, RunnerBackend] = (BACKEND_CODEX, BACKEND_CLAUDE)
DEFAULT_RUNNER_BACKEND: RunnerBackend = BACKEND_CODEX


def normalize_runner_backend(raw: str | None) -> RunnerBackend:
    value = str(raw or "").strip().lower()
    if value == BACKEND_CLAUDE:
        return BACKEND_CLAUDE
    return BACKEND_CODEX


def default_runner_bin(backend: RunnerBackend) -> str:
    if backend == BACKEND_CLAUDE:
        return "claude"
    return "codex"


def backend_label(backend: RunnerBackend) -> str:
    if backend == BACKEND_CLAUDE:
        return "Claude Code"
    return "Codex CLI"


def backend_supports_copilot_proxy(backend: RunnerBackend) -> bool:
    return backend == BACKEND_CODEX

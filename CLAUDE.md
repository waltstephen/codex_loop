# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is ArgusBot

ArgusBot is a Python supervisor plugin that wraps Codex CLI and Claude Code CLI with an automatic loop. A main agent executes tasks, a reviewer sub-agent gates completion (`done`/`continue`/`blocked`), and a planner sub-agent maintains a live framework view. The loop only stops when the reviewer says `done` and all acceptance checks pass.

## Build & Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .          # editable install
pip install pytest        # for running tests
```

## Testing

```bash
pytest -q                         # run all tests
pytest tests/test_loop_engine.py  # run a single test file
pytest -k test_loop_engine_stops  # run a specific test by name
```

Tests live in `tests/` and use lightweight stub classes (no external services needed). CI runs pytest across Python 3.10–3.13.

## CLI Entry Points (defined in pyproject.toml)

| Command | Module | Purpose |
|---|---|---|
| `argusbot` | `codex_autoloop.codexloop:main` | One-word entrypoint: first-run setup, later attach monitor |
| `argusbot-run` | `codex_autoloop.cli:main` | Direct run with full CLI flags |
| `argusbot-daemon` | `codex_autoloop.telegram_daemon:main` | Always-on daemon for Telegram/Feishu idle control |
| `argusbot-daemon-ctl` | `codex_autoloop.daemon_ctl:main` | Terminal control for a running daemon |
| `argusbot-setup` | `codex_autoloop.setup_wizard:main` | Interactive first-run wizard |
| `argusbot-models` | `codex_autoloop.model_catalog:main` | List model presets |

## Architecture (three layers)

```
codex_autoloop/
  core/                    # Pure loop runtime, no I/O integration
    engine.py              # LoopEngine: run main → checks → reviewer → planner → repeat
    ports.py               # Protocol contracts: EventSink, ControlChannel, NotificationSink
    state_store.py         # Mutable runtime state, operator messages, injections, stop requests

  adapters/                # Turn external sources into core abstractions
    control_channels.py    # Telegram/Feishu/bus → ControlCommand
    event_sinks.py         # Core events → terminal/dashboard/Telegram/Feishu output

  apps/                    # Executable shells that wire layers together
    cli_app.py             # argusbot-run wiring
    daemon_app.py          # argusbot-daemon wiring
    shell_utils.py         # Shared shell-facing helpers
```

Top-level modules (`orchestrator.py`, `control_state.py`, `codexloop.py`, `cli.py`) are compatibility wrappers that delegate to the three-layer internals.

### Key domain types (`models.py`)

- `CodexRunResult` — output from a single runner invocation
- `ReviewDecision` — structured reviewer verdict (status/confidence/reason/next_action)
- `PlanDecision` — planner output (follow_up_required, instructions, overview markdown)
- `RoundSummary` — per-round aggregate of main result + checks + review + plan
- `PlanMode` — `Literal["off", "auto", "record"]`

### Runner backends (`runner_backend.py`, `codex_runner.py`)

Two backends: `codex` (Codex CLI) and `claude` (Claude Code CLI). `CodexRunner` handles subprocess management, JSONL event parsing, stall watchdog, and session resume for both. Claude maps `xhigh` effort to `high`.

### Loop lifecycle (`core/engine.py`)

Each round: run main agent → run `--check` commands → run reviewer → optionally run planner → decide stop or continue. Stop conditions: reviewer `done` + checks pass, reviewer `blocked`, max rounds, or repeated no-progress.

### Event flow

Structured events (`loop.started`, `round.started`, `round.main.completed`, `round.checks.completed`, `round.review.completed`, `plan.completed`, `loop.completed`) flow through `EventSink` to terminal, dashboard, Telegram, and Feishu adapters.

### Daemon architecture

The daemon (`apps/daemon_app.py`) polls for commands via `JsonlCommandBus` (`daemon_bus.py`) and Telegram/Feishu adapters, spawns child `argusbot-run` processes, and manages lifecycle. `token_lock.py` enforces one active daemon per Telegram token.

## Per-project runtime state

When ArgusBot operates on a target project, it creates `.argusbot/` in that project with:
- `daemon_config.json` — persisted setup config
- `bus/` — JSONL command bus for daemon↔terminal IPC
- `logs/` — operator messages, run archive JSONL, daemon events

## Copilot proxy

Optional for Codex backend only. Routes through a local `copilot-proxy` checkout for GitHub Copilot-backed quota. Auto-detected from `~/copilot-proxy`, `~/copilot-codex-proxy`, or `~/.argusbot/tools/copilot-proxy`.

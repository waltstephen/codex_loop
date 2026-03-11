# codex-autoloop Architecture

## Goals

This refactor reshapes the project into three layers inspired by OpenClaw:

1. `core/` - pure loop runtime and state
2. `adapters/` - integrations for control/input/output surfaces
3. `apps/` - executable shells that wire everything together

The top-level legacy modules remain as compatibility wrappers so existing CLI commands
and most imports continue to work.

## Layout

```text
codex_autoloop/
  core/
    engine.py
    ports.py
    state_store.py
  adapters/
    control_channels.py
    event_sinks.py
  apps/
    cli_app.py
    daemon_app.py
    shell_utils.py

  cli.py                 # thin CLI wrapper
  telegram_daemon.py     # thin daemon wrapper
  orchestrator.py        # compatibility wrapper over core.engine
  control_state.py       # compatibility wrapper over core.state_store

  codex_runner.py        # low-level Codex subprocess adapter
  reviewer.py            # low-level reviewer adapter
  dashboard.py           # web dashboard implementation
  telegram_control.py    # Telegram polling + Whisper command parsing
  telegram_notifier.py   # Telegram notifications
  live_updates.py        # batched Telegram stream updates
  daemon_bus.py          # JSONL bus
  token_lock.py          # cross-platform daemon token lock
```

## Responsibilities

### Core

- `core.engine` owns the loop lifecycle:
  - run main agent
  - run checks
  - run reviewer
  - decide continue/done/blocked
  - emit structured events

- `core.state_store` owns mutable runtime state:
  - operator message history
  - injected instructions
  - stop requests
  - state file persistence
  - runtime status snapshot

- `core.ports` defines the contracts used by the shell layer:
  - control channels
  - notification sinks
  - event sinks

### Adapters

- `adapters.control_channels` turns external command sources into `ControlCommand`:
  - Telegram long-poll commands
  - local JSONL bus commands

- `adapters.event_sinks` turns core events/stream lines into outputs:
  - terminal rendering
  - dashboard updates
  - Telegram notifications + live batched updates

### Apps

- `apps.cli_app` wires:
  - parser args
  - state store
  - selected adapters
  - `CodexRunner`
  - `Reviewer`
  - `LoopEngine`

- `apps.daemon_app` wires:
  - Telegram daemon lifecycle
  - child process launching
  - daemon command routing
  - daemon status/logging

- `apps.shell_utils` contains shell-facing helpers shared by wrappers/tests.

## End-to-end data flow

### CLI mode

```text
CLI args
  -> apps.cli_app
  -> core.state_store
  -> adapters (telegram/dashboard/local bus as needed)
  -> core.engine
  -> codex_runner / reviewer
  -> emitted events
  -> event sinks (terminal / dashboard / Telegram)
```

### Daemon mode

```text
Telegram or terminal command
  -> adapters.control_channels
  -> apps.daemon_app
  -> child codex-autoloop process
  -> child status/log/state files
  -> Telegram notifier / daemon status file
```

## Why this is better

- Core loop logic is no longer mixed with Telegram/dashboard setup.
- New control channels or outputs can be added without touching loop logic.
- CLI and daemon are now composition shells instead of behavior owners.
- Legacy imports still work while the internal structure becomes cleaner.

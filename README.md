# codex-autoloop

`codex-autoloop` is a Python supervisor plugin for Codex CLI:

- Main agent executes the task (`codex exec` or `codex exec resume`)
- Reviewer sub-agent evaluates completion (`done` / `continue` / `blocked`)
- Planner sub-agent maintains a live framework view and proposes next-session objectives
- Loop only stops when reviewer says `done` and all acceptance checks pass

This solves the common "agent stopped early and asked for next instruction" problem.

Current defaults:

- `max_rounds` defaults to `50`.
- Daemon child model preset defaults to `quality` (`gpt-5.4` + `high`) unless overridden.
- Daemon-launched idle runs try to resume from the last saved `session_id` before starting a fresh thread.

## Current Feature Snapshot

- Persistent main-agent loop with reviewer gating (`done/continue/blocked`).
- Planner/manager agent with live plan snapshots, workstream table, and follow-up objective proposal.
- Planner TODO board (`plan_todo.md`) and explorer backlog maintained across planning sweeps.
- Stall watchdog with soft diagnosis and hard restart safety window.
- Live visibility: terminal streaming, dashboard, Telegram push, typing heartbeat.
- Telegram inbound control during active run: `/inject`, `/status`, `/stop`, voice/audio transcription.
- Always-on daemon mode for idle startup: `/run` can launch new runs when no loop is active.
- Daemon follow-up prompt: after a run ends, Telegram can offer the planner's next suggested objective as a one-click continuation.
- Planner modes: `off`, `auto`, `record`; setup defaults to `auto`.
- Dual control channels for daemon: Telegram and terminal (`codex-autoloop-daemon-ctl`).
- Token-exclusive daemon lock: one active daemon per Telegram token.
- Operator message history persisted to markdown and fed to reviewer decisions.
- Utility scripts: start/kill/watch daemon logs, plus sanitized cross-project setup examples.

## Why this is a plugin, not a native flag

Current Codex CLI does not expose a built-in `--autoloop` flag, so this repo adds a wrapper layer around `codex exec`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
codex-autoloop \
  --max-rounds 10 \
  --check "pytest -q" \
  "Implement feature X and keep iterating until tests pass"
```

Common options:

- `--session-id <id>`: continue an existing Codex session
- `--main-model` / `--reviewer-model`: set model(s)
- `--planner-model`: override the manager/planner model (defaults to reviewer settings when omitted)
- `python -m codex_autoloop.model_catalog`: list common models and presets
- `--yolo`: pass dangerous no-sandbox mode to Codex
- `--full-auto`: pass full-auto mode to Codex
- `--state-file <file>`: write round-by-round state JSON
- `--plan-report-file <file>`: write the latest planner markdown snapshot
- `--plan-todo-file <file>`: write the latest planner TODO board markdown
- `--plan-update-interval-seconds 1800`: run background planning sweeps every 30 minutes
- `--verbose-events`: print raw JSONL stream
- `--dashboard`: launch a live local web dashboard
- `--dashboard-host 0.0.0.0 --dashboard-port 8787`: expose dashboard to other devices in LAN
- `--telegram-bot-token` + `--telegram-chat-id`: send progress to Telegram (recommended for cross-network access)
- `--telegram-events`: choose which events are pushed (comma-separated)
- `--telegram-live-interval-seconds 30`: push live agent message deltas every 30s (only when changed)
- `--no-live-terminal`: disable realtime terminal prints (default is on)
- `--stall-soft-idle-seconds 1200`: after 20m no new output, run stall sub-agent diagnosis (do not force kill)
- `--stall-hard-idle-seconds 10800`: after 3h no new output, force restart as hard safety valve
- `--telegram-control`: allow Telegram inbound control (`/inject`, `/stop`, `/status`) while loop is running
- `--telegram-control-whisper`: enable Telegram voice/audio transcription for control messages (default on)

Example with live dashboard:

```bash
codex-autoloop \
  --dashboard \
  --dashboard-host 0.0.0.0 \
  --dashboard-port 8787 \
  --check "pytest -q" \
  "帮我在这个文件夹写一下pipeline"
```

Then open `http://<your-machine-ip>:8787` on phone or browser.

## Safer cross-network monitoring (Telegram)

If phone and server are not in the same network, do not expose dashboard publicly by default.
Use Telegram push notifications instead:

```bash
codex-autoloop \
  --max-rounds 12 \
  --check "pytest -q" \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-events "loop.started,round.review.completed,loop.completed" \
  "帮我在这个文件夹写一下pipeline"
```

`--telegram-chat-id` defaults to `auto` and will be resolved from `getUpdates`.
If auto resolve fails, send `/start` to bot and run again, or pass explicit chat id.

Live visibility defaults:

- Terminal prints main/reviewer agent messages in realtime.
- Telegram sends live message deltas every 30 seconds only if there are new changes.

Telegram control channel defaults:

- `/inject <text>` or plain text message: interrupt current main-agent run and apply new instruction next round.
- Voice/audio message: auto-transcribed via Whisper and treated like text input (for example spoken `/inject ...`).
- `/status`: return current loop state.
- `/stop`: interrupt current run and stop the loop.
- `/help`: print command summary.

Whisper-related options:

- `--telegram-control-whisper-api-key`: OpenAI API key (defaults to `OPENAI_API_KEY`).
- `--telegram-control-whisper-model`: transcription model (default `whisper-1`).
- `--telegram-control-whisper-base-url`: OpenAI-compatible API base URL.
- `--telegram-control-whisper-timeout-seconds`: transcription request timeout.

Stall watchdog defaults:

- If no new output for 20 minutes, sub-agent inspects the latest message/tails and decides whether restart is needed.
- If no new output reaches 3 hours, process is force-restarted regardless.

Typing heartbeat is enabled by default during execution. Disable with:

```bash
--telegram-no-typing
```

Security notes:

- Keep dashboard on `127.0.0.1` unless you have VPN/auth in front.
- Never commit bot token to git.
- Prefer sending round summaries, not every raw log line.

Troubleshooting:

- Bot token must be full format: `<digits>:<secret>`, not only the secret part.
- If no message arrives, run once with `--verbose-events` and check stderr lines prefixed with `[telegram]`.
- If control commands are ignored, verify command comes from the same chat id resolved for notifications.

## Always-on Telegram daemon (start jobs even when idle)

If you want Telegram to trigger runs when no loop process is active, run:

```bash
codex-autoloop-telegram-daemon \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-chat-id auto \
  --run-check "pytest -q"
```

Daemon commands from Telegram:

- `/run <objective>`: start a new `codex-autoloop` run
- `/status`: daemon/child status
- `/stop`: stop active run
- `/help`
- After a child run finishes, the daemon can offer a Telegram button to execute the planner's next suggested objective.
- If the user does nothing, daemon auto-executes the planned next session after the follow-up countdown (default: 10 minutes).
- Before executing that follow-up, daemon creates a git checkpoint commit when the workspace is dirty.
- Telegram follow-up options are: direct execute, reject plan, or modify then execute while inheriting the planner objective. That follow-up starts as a fresh session.

For background mode:

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./scripts/start_telegram_daemon.sh
```

Recommendation: prefer `systemd` or supervisor over raw `nohup` for production reliability.

## Interactive first-run setup (recommended)

Run once:

```bash
codex-autoloop-setup --run-cd .
```

If command is not found in your environment, use:

```bash
python -m codex_autoloop.setup_wizard --run-cd .
```

The wizard will:

1. Check `codex` CLI availability and basic auth probe.
2. Prompt for Telegram bot token/chat id.
3. Prompt optional default check command (empty means no forced check command).
4. Prompt for planner mode after model selection.
5. Start daemon in background and save config under `.codex_daemon/`.

Default behavior for daemon-launched runs:

- `--yolo` is enabled by default.
- No default `--check` is enforced unless you set one.
- Daemon defaults to the `cheap` model preset unless you override it.
- When the daemon is idle, a new `/run` or terminal `run` command will reuse the last saved `session_id` if available.
- One Telegram token can only be owned by one active daemon process (second daemon returns an error).
- Operator messages (initial objective + terminal/Telegram injects) are written to per-run markdown files in the daemon logs directory.
- Re-running setup or start script will stop the previous daemon under the same `home-dir` before launching the new one.

After setup, use terminal control:

```bash
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus run "帮我在这个文件夹写一下pipeline"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus inject "先修测试再继续"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus status
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus stop
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus daemon-stop
```

One-click kill script:

```bash
./scripts/kill_telegram_daemon.sh
```

Realtime log mirror:

```bash
./scripts/watch_daemon_logs.sh .codex_daemon
```

This mirrors:

- `.codex_daemon/daemon.out`
- `.codex_daemon/logs/daemon-events.jsonl` (Telegram/terminal control interactions)

If `codex-autoloop-daemon-ctl` is not found, replace it with:

```bash
python -m codex_autoloop.daemon_ctl
```

## Model presets

Show local model presets and common names:

```bash
python -m codex_autoloop.model_catalog
```

Current presets:

- `quality`: `main=gpt-5.4/high`, `reviewer=gpt-5.4/high`
- `quality-xhigh`: `main=gpt-5.4/xhigh`, `reviewer=gpt-5.4/xhigh`
- `balanced`: `main=gpt-5.3-codex/high`, `reviewer=gpt-5.1-codex/medium`
- `codex-xhigh`: `main=gpt-5.3-codex/xhigh`, `reviewer=gpt-5.3-codex/xhigh`
- `cheap`: `main=gpt-5.1-codex-mini/medium`, `reviewer=gpt-5-codex-mini/low`
- `max`: `main=gpt-5.1-codex-max/xhigh`, `reviewer=gpt-5.3-codex/high`

Note:

- `gpt-5.4` is the model name.
- `high` is the reasoning effort level, not part of the model name.

Daemon overrides:

```bash
python -m codex_autoloop.setup_wizard --run-cd .
```

The wizard now lets you choose either:

- a preset for both agents, or
- separate `main` / `reviewer` model names

## Example: Use in another project (`newproject`) with sanitized paths

Use this pattern when `codex_loop` is cloned under a different workspace and you want the daemon to run tasks in `newproject`.

```bash
# Replace with your own locations (public-safe placeholders)
export WORKSPACE_ROOT="/path/to/workspace"
export LOOP_REPO="$WORKSPACE_ROOT/codex_loop"
export TARGET_REPO="$WORKSPACE_ROOT/newproject"

cd "$TARGET_REPO"
python -m pip install -e "$LOOP_REPO"

# First-time setup (interactive)
python -m codex_autoloop.setup_wizard \
  --run-cd "$TARGET_REPO" \
  --home-dir "$TARGET_REPO/.codex_daemon"
```

After setup:

```bash
# Terminal control (same running daemon)
python -m codex_autoloop.daemon_ctl --bus-dir "$TARGET_REPO/.codex_daemon/bus" status
python -m codex_autoloop.daemon_ctl --bus-dir "$TARGET_REPO/.codex_daemon/bus" run "run 100-step smoke and validate checkpoint+infer"
python -m codex_autoloop.daemon_ctl --bus-dir "$TARGET_REPO/.codex_daemon/bus" inject "fix test failures first, then continue"
```

Telegram control in parallel:

- `/run <objective>`
- `/inject <instruction>`
- `/status`
- `/stop`

## `codex --autoloop` style shim

You can add a shell function so `codex --autoloop ...` routes to this plugin.

```bash
codex() {
  if [[ " $* " == *" --autoloop "* ]]; then
    /data/yijia/codexloop/scripts/codex_autoloop_shim.sh "$@"
  else
    command codex "$@"
  fi
}
```

Put it in `~/.bashrc` or `~/.zshrc`, then reload shell.

## Loop policy

Per round:

1. Run main agent in the same Codex thread (`exec` then `exec resume`)
2. Run acceptance checks (`--check`, repeatable)
3. Run reviewer sub-agent with structured JSON schema output
4. Stop only if reviewer says `done` and all checks pass
5. Otherwise build a new continue prompt and run next round

Safety stop conditions:

- `max_rounds` reached
- repeated no-progress rounds
- reviewer returns `blocked`

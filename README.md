# codex-autoloop

`codex-autoloop` is a Python supervisor plugin for Codex CLI:

- Main agent executes the task (`codex exec` or `codex exec resume`)
- Reviewer sub-agent evaluates completion (`done` / `continue` / `blocked`)
- Loop only stops when reviewer says `done` and all acceptance checks pass

This solves the common "agent stopped early and asked for next instruction" problem.

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
- `--yolo`: pass dangerous no-sandbox mode to Codex
- `--full-auto`: pass full-auto mode to Codex
- `--state-file <file>`: write round-by-round state JSON
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
3. Start daemon in background and save config under `.codex_daemon/`.

After setup, use terminal control:

```bash
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus run "帮我在这个文件夹写一下pipeline"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus inject "先修测试再继续"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus status
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus stop
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus daemon-stop
```

If `codex-autoloop-daemon-ctl` is not found, replace it with:

```bash
python -m codex_autoloop.daemon_ctl
```

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

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

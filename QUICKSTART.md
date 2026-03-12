# codex-autoloop Quickstart

## 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) One-word entrypoint (recommended)

```bash
codexloop
```

Show supported features/commands:

```bash
codexloop help
```

Behavior:
- First run: prompts for Telegram token/chat id, uses current shell directory as run working directory, writes `.codex_daemon/daemon_config.json`, starts daemon.
- Later runs: auto-reuse previous config, auto-start daemon if needed, and attach to live logs.
- `codexloop init`: stop all current codexloop daemons, prompt token/chat id/model preset/play mode, start a fresh daemon in background, and exit.
- After `init`, run `codexloop` to attach monitor.
- In attach console, terminal control works directly:
  - `/run <objective>`
  - `/inject <instruction>`
  - `/status`, `/stop`, `/disable` (same as `/daemon-stop`), `/daemon-stop`
  - plain text: running => inject, idle => run

Play Mode:
- `execute-only`: only execute user commands, no plan agent.
- `fully-plan` (default): 10 minutes after run completion, daemon proposes next request; if not overridden within another 10 minutes, it auto-runs.
- `record-only`: plan agent only writes markdown table records; reviewer remains unchanged.

Daemon-launched runs use `--yolo` by default.

Disable daemon quickly:

```bash
codexloop disable
```

## 3) Run (basic)

```bash
codex-autoloop \
  --max-rounds 500 \
  "帮我在这个文件夹写一下pipeline"
```

## 4) Run with Telegram (secure remote visibility)

```bash
export TELEGRAM_BOT_TOKEN='123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

codex-autoloop \
  --max-rounds 500 \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-events "loop.started,round.review.completed,loop.completed" \
  "帮我在这个文件夹写一下pipeline"
```

Notes:
- `chat_id` defaults to `auto` and is resolved from Telegram updates.
- Live terminal streaming is on by default.
- Telegram live deltas are sent every 30s only when content changes.
- Telegram control commands are enabled by default (`/inject`, `/status`, `/stop`).
- Daemon defaults to the `codex-xhigh` model preset (`gpt-5.3-codex` + `xhigh`) unless you override it.

Control examples from Telegram Web:

- `/inject 先停止当前实验，改成只跑100 step并保存checkpoint`
- `/status`
- `/stop`

## 6) Keep Telegram online even when no run is active

```bash
codex-autoloop-telegram-daemon \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-chat-id auto
```

Then from Telegram Web:

- `/run 帮我在这个文件夹写一下pipeline`
- `/status`
- `/stop`

## 7) Interactive setup + background daemon

```bash
codex-autoloop-setup --run-cd .
```

If the command is missing, use:

```bash
python -m codex_autoloop.setup_wizard --run-cd .
```

Setup now asks for planner mode after model selection:

- `1` No Planner
- `2` Auto Planner (default)
- `3` Record-Only Planner

Auto Planner follow-up countdown defaults to 10 minutes.

Then terminal control (same daemon, no restart needed):

```bash
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus run "实现一个长程目标"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus inject "切换到更保守的方案并先跑测试"
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus status
codex-autoloop-daemon-ctl --bus-dir .codex_daemon/bus stop
```

Defaults:
- Daemon-launched run uses `--yolo` by default.
- Default check command is optional (leave empty for no forced check).
- Idle daemon tries to resume from the last saved `session_id`.
- One Telegram token can only be used by one active daemon.
- Operator messages are recorded into per-run markdown files in `.codex_daemon/logs/`.
- Daemon child model preset defaults to `codex-xhigh`.
- Re-running setup/start will stop the previous daemon for the same `.codex_daemon` before starting a new one.

One-click kill:

```bash
./scripts/kill_telegram_daemon.sh
```

Realtime log mirror:

```bash
./scripts/watch_daemon_logs.sh .codex_daemon
```

If command is missing, use:

```bash
python -m codex_autoloop.daemon_ctl --bus-dir .codex_daemon/bus status
```

## 4) Optional dashboard

```bash
codex-autoloop \
  --dashboard \
  --dashboard-host 127.0.0.1 \
  --dashboard-port 8787 \
  --max-rounds 500 \
  "your objective"
```

## 5) Privacy / de-sensitization checklist

- Never hardcode token/chat id in source files.
- Use env vars for secrets (`TELEGRAM_BOT_TOKEN` etc.).
- Rotate bot token immediately if it appears in terminal history or screenshots.
- Before publish, scan repository for secrets:

```bash
rg -n "([0-9]{8,}:[A-Za-z0-9_-]{20,}|TELEGRAM_BOT_TOKEN|chat_id|token)" -S
```

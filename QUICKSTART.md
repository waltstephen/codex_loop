# ArgusBot Quickstart

## 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) One-word entrypoint (recommended)

```bash
argusbot
```

Show supported features/commands:

```bash
argusbot help
```

Behavior:
- First run: prompts you to choose control channel (`1. Telegram`, `2. Feishu (适合CN网络环境)`, `3. Teams`, default Telegram), then collects selected channel credentials, writes `.argusbot/daemon_config.json`, and starts daemon.
- Later runs: auto-reuse previous config, auto-start daemon if needed, and attach to live logs.
- `argusbot init`: stop current workspace daemon, prompt control channel + credentials/model preset/play mode, start a fresh daemon in background, and exit.
- After `init`, run `argusbot` to attach monitor.
- In attach console, terminal control works directly:
  - `/run <objective>`
  - `/new`
  - `/inject <instruction>`
  - `/mode <off|auto|record>`
  - `/btw <question>`
  - `/plan <direction>`
  - `/review <criteria>`
  - `/show-main-prompt`
  - `/show-plan`
  - `/show-plan-context`
  - `/show-review [round]`
  - `/show-review-context`
  - `/status`, `/stop`, `/daemon-stop`
  - plain text: running => inject, idle => run

Planner Mode:
- `off`: disable plan agent behavior for daemon-launched runs.
- `auto` (default): planner stays enabled and daemon may propose or auto-run the next request.
- `record`: planner records markdown only without automatic follow-up execution.

Daemon-launched runs use `--yolo` by default.

Disable daemon quickly:

```bash
argusbot daemon-stop
```

## 3) Run (basic)

```bash
argusbot-run \
  --max-rounds 500 \
  "帮我在这个文件夹写一下pipeline"
```

## 4) Run with Telegram (secure remote visibility)

```bash
export TELEGRAM_BOT_TOKEN='123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

argusbot-run \
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
argusbot-daemon \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-chat-id auto
```

Then from Telegram Web:

- `/run 帮我在这个文件夹写一下pipeline`
- `/status`
- `/stop`

## 7) Interactive setup + background daemon

```bash
argusbot-setup --run-cd .
```

If the command is missing, use:

```bash
  .\.venv\Scripts\Activate.ps1                                                                                   
         Get-Process | Where-Object { $_.ProcessName -like 'argusbot*' } | Stop-Process -Force                          
python -m codex_autoloop.setup_wizard --run-cd .
```

Setup now asks for planner mode after model selection:

- `1` No Planner
- `2` Auto Planner (default)
- `3` Record-Only Planner

Auto Planner follow-up countdown defaults to 10 minutes.

Then terminal control (same daemon, no restart needed):

```bash
argusbot-daemon-ctl --bus-dir .argusbot/bus run "实现一个长程目标"
argusbot-daemon-ctl --bus-dir .argusbot/bus inject "切换到更保守的方案并先跑测试"
argusbot-daemon-ctl --bus-dir .argusbot/bus status
argusbot-daemon-ctl --bus-dir .argusbot/bus stop
```

Defaults:
- Daemon-launched run uses `--yolo` by default.
- Default check command is optional (leave empty for no forced check).
- Idle daemon tries to resume from the last saved `session_id`.
- One Telegram token can only be used by one active daemon.
- Operator messages are recorded into per-run markdown files in `.argusbot/logs/`.
- Daemon child model preset defaults to `codex-xhigh`.
- Re-running setup/start will stop the previous daemon for the same `.argusbot` before starting a new one.

One-click kill:

```bash
./scripts/kill_telegram_daemon.sh
```

Realtime log mirror:

```bash
./scripts/watch_argusbot_logs.sh .argusbot
```

If command is missing, use:

```bash
python -m codex_autoloop.daemon_ctl --bus-dir .argusbot/bus status
```

## 4) Optional dashboard

```bash
argusbot-run \
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

# codex-autoloop Quickstart

## 1) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Run (basic)

```bash
codex-autoloop \
  --max-rounds 12 \
  --check "pytest -q" \
  "帮我在这个文件夹写一下pipeline"
```

## 3) Run with Telegram (secure remote visibility)

```bash
export TELEGRAM_BOT_TOKEN='123456789:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

codex-autoloop \
  --max-rounds 12 \
  --check "pytest -q" \
  --telegram-bot-token "$TELEGRAM_BOT_TOKEN" \
  --telegram-events "loop.started,round.review.completed,loop.completed" \
  "帮我在这个文件夹写一下pipeline"
```

Notes:
- `chat_id` defaults to `auto` and is resolved from Telegram updates.
- Live terminal streaming is on by default.
- Telegram live deltas are sent every 30s only when content changes.

## 4) Optional dashboard

```bash
codex-autoloop \
  --dashboard \
  --dashboard-host 127.0.0.1 \
  --dashboard-port 8787 \
  --max-rounds 12 \
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

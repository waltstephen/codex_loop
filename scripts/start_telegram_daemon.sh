#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required." >&2
  exit 2
fi

LOG_DIR="${CODEX_DAEMON_LOG_DIR:-.codex_daemon}"
mkdir -p "${LOG_DIR}"

nohup codex-autoloop-telegram-daemon \
  --telegram-bot-token "${TELEGRAM_BOT_TOKEN}" \
  --telegram-chat-id "${TELEGRAM_CHAT_ID:-auto}" \
  --run-check "${CODEX_DAEMON_CHECK:-pytest -q}" \
  >"${LOG_DIR}/daemon.out" 2>&1 &

echo "Started codex-autoloop-telegram-daemon in background."
echo "PID: $!"
echo "Log: ${LOG_DIR}/daemon.out"

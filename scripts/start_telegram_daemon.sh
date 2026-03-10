#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required." >&2
  exit 2
fi

LOG_DIR="${CODEX_DAEMON_LOG_DIR:-.codex_daemon}"
BUS_DIR="${CODEX_DAEMON_BUS_DIR:-${LOG_DIR}/bus}"
RUN_CD="${CODEX_DAEMON_RUN_CD:-$PWD}"
mkdir -p "${LOG_DIR}"
mkdir -p "${BUS_DIR}"

if command -v codex-autoloop-telegram-daemon >/dev/null 2>&1; then
  DAEMON_CMD=(codex-autoloop-telegram-daemon)
else
  DAEMON_CMD=(python -m codex_autoloop.telegram_daemon)
fi

EXTRA_ARGS=()
if [[ -n "${CODEX_DAEMON_CHECK:-}" ]]; then
  EXTRA_ARGS+=(--run-check "${CODEX_DAEMON_CHECK}")
fi
if [[ "${CODEX_DAEMON_YOLO:-1}" == "1" || "${CODEX_DAEMON_YOLO:-1}" == "true" ]]; then
  EXTRA_ARGS+=(--run-yolo)
else
  EXTRA_ARGS+=(--no-run-yolo)
fi

nohup "${DAEMON_CMD[@]}" \
  --telegram-bot-token "${TELEGRAM_BOT_TOKEN}" \
  --telegram-chat-id "${TELEGRAM_CHAT_ID:-auto}" \
  --run-cd "${RUN_CD}" \
  --bus-dir "${BUS_DIR}" \
  --logs-dir "${LOG_DIR}/logs" \
  "${EXTRA_ARGS[@]}" \
  >"${LOG_DIR}/daemon.out" 2>&1 &

echo "Started codex-autoloop-telegram-daemon in background."
echo "PID: $!"
echo "Log: ${LOG_DIR}/daemon.out"
echo "Bus dir: ${BUS_DIR}"
echo "Use terminal control:"
echo "  codex-autoloop-daemon-ctl --bus-dir ${BUS_DIR} status"

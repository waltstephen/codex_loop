#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required." >&2
  exit 2
fi

LOG_DIR="${CODEX_DAEMON_LOG_DIR:-.codex_daemon}"
BUS_DIR="${CODEX_DAEMON_BUS_DIR:-${LOG_DIR}/bus}"
RUN_CD="${CODEX_DAEMON_RUN_CD:-$PWD}"
TOKEN_LOCK_DIR="${CODEX_DAEMON_TOKEN_LOCK_DIR:-/tmp/codex-autoloop-token-locks}"
HOME_DIR="${CODEX_DAEMON_HOME_DIR:-${LOG_DIR}}"
mkdir -p "${LOG_DIR}"
mkdir -p "${BUS_DIR}"

PID_FILE="${HOME_DIR}/daemon.pid"
if [[ -f "${PID_FILE}" ]]; then
  if command -v codex-autoloop-daemon-ctl >/dev/null 2>&1; then
    codex-autoloop-daemon-ctl --bus-dir "${BUS_DIR}" daemon-stop >/dev/null 2>&1 || true
  else
    python -m codex_autoloop.daemon_ctl --bus-dir "${BUS_DIR}" daemon-stop >/dev/null 2>&1 || true
  fi
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "${PID}" 2>/dev/null; then
      kill -9 "${PID}" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "${PID_FILE}"
fi

if command -v codex-autoloop-telegram-daemon >/dev/null 2>&1; then
  DAEMON_CMD=(codex-autoloop-telegram-daemon)
else
  DAEMON_CMD=(python -m codex_autoloop.telegram_daemon)
fi

EXTRA_ARGS=()
if [[ -n "${CODEX_DAEMON_CHECK:-}" ]]; then
  EXTRA_ARGS+=(--run-check "${CODEX_DAEMON_CHECK}")
fi
if [[ -n "${CODEX_DAEMON_MODEL_PRESET:-}" ]]; then
  EXTRA_ARGS+=(--run-model-preset "${CODEX_DAEMON_MODEL_PRESET}")
fi
if [[ -n "${CODEX_DAEMON_MAIN_MODEL:-}" ]]; then
  EXTRA_ARGS+=(--run-main-model "${CODEX_DAEMON_MAIN_MODEL}")
fi
if [[ -n "${CODEX_DAEMON_REVIEWER_MODEL:-}" ]]; then
  EXTRA_ARGS+=(--run-reviewer-model "${CODEX_DAEMON_REVIEWER_MODEL}")
fi
if [[ "${CODEX_DAEMON_YOLO:-1}" == "1" || "${CODEX_DAEMON_YOLO:-1}" == "true" ]]; then
  EXTRA_ARGS+=(--run-yolo)
else
  EXTRA_ARGS+=(--no-run-yolo)
fi
if [[ "${CODEX_DAEMON_RESUME_LAST_SESSION:-1}" == "1" || "${CODEX_DAEMON_RESUME_LAST_SESSION:-1}" == "true" ]]; then
  EXTRA_ARGS+=(--run-resume-last-session)
else
  EXTRA_ARGS+=(--no-run-resume-last-session)
fi

nohup "${DAEMON_CMD[@]}" \
  --telegram-bot-token "${TELEGRAM_BOT_TOKEN}" \
  --telegram-chat-id "${TELEGRAM_CHAT_ID:-auto}" \
  --run-cd "${RUN_CD}" \
  --bus-dir "${BUS_DIR}" \
  --logs-dir "${LOG_DIR}/logs" \
  --token-lock-dir "${TOKEN_LOCK_DIR}" \
  "${EXTRA_ARGS[@]}" \
  >"${LOG_DIR}/daemon.out" 2>&1 &

echo "$!" > "${PID_FILE}"

echo "Started codex-autoloop-telegram-daemon in background."
echo "PID: $!"
echo "Log: ${LOG_DIR}/daemon.out"
echo "Bus dir: ${BUS_DIR}"
echo "Use terminal control:"
echo "  codex-autoloop-daemon-ctl --bus-dir ${BUS_DIR} status"
echo "Live logs:"
echo "  ./scripts/watch_daemon_logs.sh ${LOG_DIR%/logs}"

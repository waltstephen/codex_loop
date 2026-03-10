#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${CODEX_DAEMON_HOME_DIR:-.codex_daemon}"
PID_FILE="${HOME_DIR}/daemon.pid"
BUS_DIR="${CODEX_DAEMON_BUS_DIR:-${HOME_DIR}/bus}"

if command -v codex-autoloop-daemon-ctl >/dev/null 2>&1; then
  codex-autoloop-daemon-ctl --bus-dir "${BUS_DIR}" daemon-stop >/dev/null 2>&1 || true
else
  python -m codex_autoloop.daemon_ctl --bus-dir "${BUS_DIR}" daemon-stop >/dev/null 2>&1 || true
fi

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" || true
    sleep 1
    if kill -0 "${PID}" 2>/dev/null; then
      kill -9 "${PID}" || true
    fi
  fi
  rm -f "${PID_FILE}"
fi

echo "Daemon stop requested. Check status:"
if command -v codex-autoloop-daemon-ctl >/dev/null 2>&1; then
  codex-autoloop-daemon-ctl --bus-dir "${BUS_DIR}" status || true
else
  python -m codex_autoloop.daemon_ctl --bus-dir "${BUS_DIR}" status || true
fi

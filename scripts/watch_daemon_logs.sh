#!/usr/bin/env bash
set -euo pipefail

HOME_DIR="${1:-${CODEX_DAEMON_HOME_DIR:-.codex_daemon}}"
LOG_DIR="${CODEX_DAEMON_LOG_DIR:-${HOME_DIR}/logs}"
MAIN_LOG="${HOME_DIR}/daemon.out"
EVENTS_LOG="${LOG_DIR}/daemon-events.jsonl"

touch "${MAIN_LOG}" "${EVENTS_LOG}"

echo "Watching daemon logs..."
echo "  main:   ${MAIN_LOG}"
echo "  events: ${EVENTS_LOG}"
echo "Press Ctrl+C to stop."
echo

tail -F "${MAIN_LOG}" "${EVENTS_LOG}"

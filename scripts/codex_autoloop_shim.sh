#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   codex_autoloop_shim.sh --autoloop "<objective>"
#   codex_autoloop_shim.sh --autoloop --yolo -- "<objective>"
# Without --autoloop, it delegates to the original codex binary.

if [[ $# -eq 0 ]]; then
  exec codex
fi

ORIGINAL_ARGS=("$@")
AUTOLOOP=0
YOLO=0
SKIP_GIT_CHECK=0
FULL_AUTO=0
MODEL=""
OBJECTIVE=()
AUTOLOOP_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --autoloop)
      AUTOLOOP=1
      shift
      ;;
    --yolo)
      YOLO=1
      shift
      ;;
    --skip-git-repo-check)
      SKIP_GIT_CHECK=1
      shift
      ;;
    --full-auto)
      FULL_AUTO=1
      shift
      ;;
    --dashboard)
      AUTOLOOP_ARGS+=(--dashboard)
      shift
      ;;
    --dashboard-host)
      AUTOLOOP_ARGS+=(--dashboard-host "$2")
      shift 2
      ;;
    --dashboard-port)
      AUTOLOOP_ARGS+=(--dashboard-port "$2")
      shift 2
      ;;
    --check)
      AUTOLOOP_ARGS+=(--check "$2")
      shift 2
      ;;
    --telegram-bot-token)
      AUTOLOOP_ARGS+=(--telegram-bot-token "$2")
      shift 2
      ;;
    --telegram-chat-id)
      AUTOLOOP_ARGS+=(--telegram-chat-id "$2")
      shift 2
      ;;
    --telegram-events)
      AUTOLOOP_ARGS+=(--telegram-events "$2")
      shift 2
      ;;
    --telegram-timeout-seconds)
      AUTOLOOP_ARGS+=(--telegram-timeout-seconds "$2")
      shift 2
      ;;
    --telegram-chat-id-resolve-timeout-seconds)
      AUTOLOOP_ARGS+=(--telegram-chat-id-resolve-timeout-seconds "$2")
      shift 2
      ;;
    --telegram-no-typing)
      AUTOLOOP_ARGS+=(--telegram-no-typing)
      shift
      ;;
    --telegram-typing-interval-seconds)
      AUTOLOOP_ARGS+=(--telegram-typing-interval-seconds "$2")
      shift 2
      ;;
    --telegram-live-interval-seconds)
      AUTOLOOP_ARGS+=(--telegram-live-interval-seconds "$2")
      shift 2
      ;;
    --no-telegram-live-updates)
      AUTOLOOP_ARGS+=(--no-telegram-live-updates)
      shift
      ;;
    --no-live-terminal)
      AUTOLOOP_ARGS+=(--no-live-terminal)
      shift
      ;;
    --max-rounds)
      AUTOLOOP_ARGS+=(--max-rounds "$2")
      shift 2
      ;;
    --session-id)
      AUTOLOOP_ARGS+=(--session-id "$2")
      shift 2
      ;;
    -m|--model)
      MODEL="$2"
      shift 2
      ;;
    --)
      shift
      OBJECTIVE+=("$@")
      break
      ;;
    *)
      OBJECTIVE+=("$1")
      shift
      ;;
  esac
done

if [[ "${AUTOLOOP}" -eq 0 ]]; then
  exec codex "${ORIGINAL_ARGS[@]}"
fi

if [[ "${#OBJECTIVE[@]}" -eq 0 ]]; then
  echo "autoloop objective missing. Example: codex --autoloop \"fix flaky tests\"" >&2
  exit 2
fi

CMD=(codex-autoloop)
if [[ -n "${MODEL}" ]]; then
  CMD+=(--main-model "${MODEL}" --reviewer-model "${MODEL}")
fi
if [[ "${#AUTOLOOP_ARGS[@]}" -gt 0 ]]; then
  CMD+=("${AUTOLOOP_ARGS[@]}")
fi
if [[ "${YOLO}" -eq 1 ]]; then
  CMD+=(--yolo)
fi
if [[ "${SKIP_GIT_CHECK}" -eq 1 ]]; then
  CMD+=(--skip-git-repo-check)
fi
if [[ "${FULL_AUTO}" -eq 1 ]]; then
  CMD+=(--full-auto)
fi
CMD+=("${OBJECTIVE[@]}")

exec "${CMD[@]}"

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="logs/daily_reconcile.log"
mkdir -p "$(dirname "$LOG")"

notify() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send -u critical "cycling-coach: reconcile falhou" "$1"
  fi
}

step() {
  echo "=== $(date '+%F %T') ===" >> "$LOG"
  if ! "$@" >> "$LOG" 2>&1; then
    notify "comando falhou: $* (ver logs/daily_reconcile.log)"
    exit 1
  fi
}

step python3 src/training_plan.py reconcile --show
step python3 src/training_plan.py push --start "$(date +%F)"
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="logs/daily_reconcile.log"
mkdir -p "$(dirname "$LOG")"

{
  echo "=== $(date '+%F %T') ==="
  python3 src/training_plan.py reconcile --show
  python3 src/training_plan.py push --start "$(date +%F)"
} >> "$LOG" 2>&1
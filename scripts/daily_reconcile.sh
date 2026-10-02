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

# A readiness do dia (#58 Passo A) roda AQUI, antes de reconciliar e publicar.
# A sessao de hoje e publicada por este script (`push --start $(date +%F)`),
# entao a janela em que a leitura de hoje ainda pode mudar o plano e exatamente
# esta. Sem esta etapa, `check` era um comando que ninguem chamava e a leitura
# de prontidao nunca alterava nada (ver SPEC-passo-A-readiness.md secao 15).
#
# `check --apply` grava SO no plan.json local. Publicar continua sendo o passo
# seguinte (`push`), que ja era a unica etapa que fala com o calendario.
#
# Se a leitura de hoje ainda nao sincronizou do dispositivo, `check` registra
# isso e segue sem alterar nada — e o comportamento correto, porque uma leitura
# de ontem nao descreve a sessao de hoje.
step python3 src/training_plan.py check --apply
step python3 src/training_plan.py reconcile --show
step python3 src/training_plan.py push --start "$(date +%F)"

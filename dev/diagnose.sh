#!/usr/bin/env bash
# dev/diagnose.sh — coleta o estado da aplicacao num unico snapshot.
# Rodar ANTES de investigar/re-executar qualquer coisa apos uma falha.
# Seguro: nunca imprime a API key (sanitiza o .env).
set -uo pipefail
cd "$(dirname "$0")/.."

echo "=== dev/diagnose.sh $(date '+%F %T') ==="
echo

echo "--- Versao ---"
cat VERSION 2>/dev/null || echo "(sem VERSION)"
git log --oneline -3 2>/dev/null || true
echo

echo "--- Timer/servico systemd ---"
systemctl --user status cycling-coach-daily.timer --no-pager 2>&1 | grep -E 'Loaded|Active|Trigger' || echo "(timer nao encontrado)"
systemctl --user status cycling-coach-daily.service --no-pager 2>&1 | grep -E 'Loaded|Active|Main PID|status=' || echo "(servico nao encontrado)"
echo

echo "--- Ultimas linhas do log diario ---"
tail -n 15 logs/daily_reconcile.log 2>/dev/null || echo "(log inexistente)"
echo

echo "--- plan.json (config do plano) ---"
python3 -c "import json; d=json.load(open('plan.json')); print(json.dumps({k: d[k] for k in ('goal','race_date','ftp_test_date','weekly_hours','long_day') if k in d}, indent=2, ensure_ascii=False)); print('workouts no plano:', len(d.get('workouts', [])))" 2>&1 || echo "(plan.json ausente/invalido)"
echo

echo "--- .env (sanitizado, sem valores) ---"
if [ -f .env ]; then
  grep -oE '^[A-Z_]+' .env | sed 's/^/  /'
else
  echo "  (.env ausente)"
fi
echo

echo "--- Health check via info (TSB/CTL/ATL) ---"
timeout 60 python3 src/training_plan.py info 2>&1 | tail -n 12 || echo "(falha no info — ver saida acima)"
echo

echo "--- Suites de teste ---"
timeout 300 python3 -m unittest discover -s tests 2>&1 | tail -n 3 || echo "(falha nos testes — ver saida acima)"
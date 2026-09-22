# Diagnóstico de falhas — Hermes Coach

Fluxo para investigar quando a aplicação quebra. Comece pelo elo mais provável
e só reexecute depois de entender a causa (regra transversal do projeto).

## 0. Coletar estado (sempre primeiro)

```bash
./dev/diagnose.sh
```

Isso captura: versão, timer/serviço systemd, último log, estado do `plan.json`,
config do `.env` **sem expor a API key**, conectividade com o Intervals e a
suíte de testes. Cole a saída no issue/nota de investigação.

## 1. A falha veio do timer diário?

O systemd user `cycling-coach-daily` roda `reconcile + push` à meia-noite e
notifica via `notify-send` se algo falhar.

```bash
systemctl --user status cycling-coach-daily.{timer,service} --no-pager
journalctl --user -u cycling-coach-daily.service -n 50 --no-pager
tail -n 40 logs/daily_reconcile.log
```

- **Timer inativo/desabilitado** → reativar: `systemctl --user enable --now cycling-coach-daily.timer`.
- **Serviço falhou (exit != 0)** → o log guarda o passo que falhou
  (`step python3 src/training_plan.py ...`). Vá para o passo 2.
- **Serviço OK mas sem evento no calendário** → o Intervals pode ter rejeitado
  o upsert (HTTP != 200 no log). Confira o passo 3.

## 2. A falha foi no CLI (`training_plan.py`)?

Reproduza o passo que falhou manualmente (o log mostra o comando exato):

```bash
python3 src/training_plan.py info                # conexao + TSB/CTL/ATL
python3 src/training_plan.py reconcile --show   # detecta treinos perdidos
python3 src/training_plan.py push --start "$(date +%F)"
```

Erros comuns e direção:

| Sintoma | Causa provável | Ação |
|---|---|---|
| `401`/`403` | API key inválida/expirada no `.env` | Regenerar em Settings → Developer Settings; validar com `info` |
| `ConnectionError`/timeout | Rede/Intervals fora do ar | Aguardar e repetir; não é bug do agente |
| `KeyError` em `plan.json` | `.env` mudou (`TRAINING_DAYS`/`GOAL`) sem rebuild | Rodar `build` (preserva treino de hoje) antes do `push` |
| `parse_training_days` inválido | `.env` com dias fora de `seg..dom`/`mon..sun` | Corrigir `TRAINING_DAYS` |
| Trackback no `reconcile` ao reescrever | Treino de hoje com modo FC (`hr_mode`) e `FTHR` ausente | Definir `FTHR` no `.env` (ou `build` em modo potência) |

## 3. O Intervals rejeitou o evento?

- O log do `push` mostra o HTTP status do `POST /events/bulk?upsert=true`.
- **HTTP != 200** → a resposta costuma trazer o motivo (campo inválido, data no
  passado, `description` com cue fora das limitações). O parser do Intervals
  trunca texto em `%`/durações abreviadas no cue — mensagens explicativas usam
  "por cento"/"minutos" por extenso.
- Conferir o calendário no app: o treino está lá com o nome `YYYY-MM-DD - ...`?

## 4. O plano está incoerente (`plan.json`)

```bash
python3 -c "import json; print(json.load(open('plan.json'))['meta'])"
```

Confira `goal`, `race_date`, `days_plan`, `budget`. Se o usuário trocou de
objetivo no meio do plano, `build` é obrigatório antes do `push` — treinos
futuros são reescritos, o de hoje é preservado.

## 5. Nada disso explica → testes

```bash
python3 -m unittest discover -s tests -v
```

Se a suíte quebrar, é regressão do código (não do ambiente): compare com o
último release no `CHANGELOG.md` e reporte.

## 6. Escalar

- Falha de ambiente/produção não reproduzível localmente → registrar no
  `docs/KNOWN_ISSUES.md` com o passo 0 anexado.
- Bugs do comportamento do Intervals (ex.: "fantasma" MANUAL, issue #1) →
  mitigar no app; não vale caçar no agente.
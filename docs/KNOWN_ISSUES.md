# Issues conhecidas — Hermes Coach

Lista de bugs conhecidos e pendências técnicas registradas, com rastreio no
GitHub. Formato: cada issue tem status, impacto, mitigação atual e direção de
solução.

---

## #1 — Intervals cria atividade MANUAL "fantasma" a partir do evento planejado

**GitHub:** [valdelin/Hermes-coach#1](https://github.com/valdelin/Hermes-coach/issues/1)
**Status:** aberto (aceito; não bloqueia o fluxo) · **Severidade:** cosmética/baixa
· **Prioridade:** baixa (`priority: low`, decisão 2026-09-21 — cosmético, comportamento
do Intervals, não do agente)

### Sintoma

Ao sincronizar a atividade real (ex.: Zwift) e pareá-la com um evento
`hermes-plan-YYYY-MM-DD`, o Intervals também materializa **o próprio evento
como uma atividade** no feed:

- `source: MANUAL`, `fit_file: null`, sem `external_id`/`event_id`/`paired_event_id`;
- `start_date_local` = horário agendado do evento (`START_TIME = "07:30:00"` em `src/plan.py`);
- duração e load = valores **planejados** (não os reais).

### Impacto

- Entrada duplicada ("fantasma") no feed de atividades do dia.
- Se a atividade real for **maior** que o planejado (mais TSS/duração), a
  fantasma mantém valores planejados → o dia pode parecer mais carregado que o
  real em painéis de `icu_training_load` (dupla contagem **cosmética**).
- **Não** afeta CTL/ATL/TSB (a fantasma tem `tss: null`) nem o `reconcile`
  (a fantasma não tem `paired_event_id` → invisível para `_done_and_extra`).

### Mitigação atual

1. No app do Intervals, arrastar a entrada do treino sobre a atividade real
   **pareia** atividade ↔ evento (não há merge na API);
2. Apagar a fantasma no app ou via `DELETE /api/v1/activity/{id}` — seguro,
   pois é um registro órfão.

### Restrição de API

Não existe endpoint de **merge** de atividades na API pública do Intervals
(apenas GET/PUT/DELETE `/activity/{id}`, upload e criação manual).

### Direção de solução (futura)

Etapa de **limpeza de fantasmas** no fluxo `reconcile`/`push` (ou no
`scripts/daily_reconcile.sh`):

1. Detectar atividades `MANUAL` sem `fit_file` e sem vínculo, cujo **nome
   coincide com evento `hermes-plan*`** e **duração = duração planejada**;
2. Confirmar que a atividade real pareada existe;
3. Excluir via `DELETE /api/v1/activity/{id}`;
4. `--dry-run` antes de excluir + testes (regra do projeto:
   `python3 -m unittest discover -s tests -v`).

### Registro

- 2026-09-18: verificado com dados reais — evento `137086170`
  (`hermes-plan-2026-09-18`) pareado com `i188054492` (Zwift, UPLOAD, load 18)
  e fantasma `i188054507` (Ride 07:30, MANUAL, load 23, 2400s).
- 2026-09-18: registrado como issue #1 no GitHub.
- 2026-09-21: **prioridade reduzida** pelo atleta — é cosmético e é bug do
  Intervals, não do agente; label `priority: low`; deixa de ser o primeiro item
  da sessão de testes de 22/09 (segue como melhoria de qualidade de dados,
  podendo entrar junto da Fase 1/notificações ou quando houver folga).

---

## Build — preservar o treino de hoje descarta WEEKLY_HOURS/LONG_DAY

**GitHub:** valdelin/Hermes-coach#7
**Status:** **corrigido** (implementado 2026-09-22, aguardando commit/release) ·
**Severidade:** funcional (configuração ignorada silenciosamente)
· **Encontrado em:** 2026-09-22 (roteiro de testes, S5)

### Sintoma

Quando o `plan.json` já contém um treino para **hoje** (caso normal: o `build`
é regerado em dia de treino), o scaling de disponibilidade **não é aplicado**:
com `WEEKLY_HOURS=2` a linha `Disponibilidade: 2h/semana` é impressa, mas as
durações ficam idênticas ao plano sem `WEEKLY_HOURS`. O mesmo vale para
`LONG_DAY` (o ciclo não é rotacionado). Com `plan.json` sem treino de hoje, o
scaling funciona normalmente (validado: durações reduzidas, mínimo 150s).

### Causa

`src/plan.py::build_plan` (linhas 368-376): o caminho que **preserva o treino
de hoje** chama `build_plan` recursivamente **sem repassar `weekly_hours` e
`long_day`**:

```python
return plan + build_plan(events, tsb, ftp=ftp, days=days,
                         start=start, training_days=training_days,
                         goal=goal, race_date=race_date,
                         ftp_test_date=ftp_test_date)
                         # faltam: weekly_hours=..., long_day=...
```

### Impacto

- Usuário configura `WEEKLY_HOURS`/`LONG_DAY` no onboarding e o `build` diário
  (sempre com treino de hoje existente) **ignora** a configuração sem aviso —
  a linha `Disponibilidade` dá a falsa impressão de que o ajuste foi aplicado.
- Funcional (não crasha), mas anula o valor da feature de disponibilidade
  (v0.0.11) no fluxo real de uso.

### Direção de solução

Repassar `weekly_hours=weekly_hours, long_day=long_day` na chamada recursiva
(e manter o treino de hoje fora do scaling — ele já existe e não deve ser
mudado). Testes: cenário `WEEKLY_HOURS=2` **com** plano contendo hoje (regressão).

### Correção (implementada)

`build_plan` repassa `weekly_hours=weekly_hours, long_day=long_day` na chamada
recursiva do caminho de preservação do treino de hoje. O treino de hoje
preservado **não** é escalado (fica exatamente como estava). Testes de
regressão: `PreserveTodayWithAvailabilityTest` em `tests/test_availability.py`
(WEEKLY_HOURS e LONG_DAY com plano contendo hoje). Validado também no fluxo
real: com `plan.json` contendo 22/09, `WEEKLY_HOURS=2` → futuros escalados
(241 vs 373 TSS) e hoje preservado (on_sec 360).

### Nota operacional (2026-09-22)

Durante a sessão de testes, `rm -f plan.json` + `build` (que começa em
**amanhã**, `start = today + 1`) gerou planos **sem o treino de hoje**; a
execução do `scripts/daily_reconcile.sh` (S10) fez `push --start $(date +%F)`
= `--start 2026-09-22` e a limpeza de órfãos **apagou o evento de hoje** do
calendário (`Orfaos removidos (HTTP 200): 1`). Restaurado manualmente via
upsert do payload original (`id 138109180`, `hermes-plan-2026-09-22`) e o
`plan.json` re-inseriu o dia.

Prevenção (relacionada ao bug acima): o caminho de **preservar o treino de
hoje** no `build` é o que protege o evento — nunca regenerar o plano a partir
do zero em produção sem incluir hoje antes do `push`; o `push --start hoje`
trata qualquer dia ausente do plano como órfão por design.

### Registro

- 2026-09-22: encontrado na S5 do `docs/ROTEIRO-TESTES.md`; causa raiz
  identificada; issue aberta no GitHub (#7).

---

## `reconcile` grava `plan.json` sem a meta (goal/race_date/ftp_test_date)

**GitHub:** valdelin/Hermes-coach#8
**Status:** **corrigido** (implementado 2026-09-22, aguardando commit/release) ·
**Severidade:** baixa hoje (auditável; baixo impacto) —
**vai ficar funcional com a #6** (`ftp_candidates` vive na meta) · **Encontrado em:** 2026-09-22 (roteiro de testes, S2/S6)

### Sintoma

O `build` salva `plan.json` no formato novo `{'goal', 'race_date',
'ftp_test_date', 'workouts'}`. O `reconcile` em seguida regrava o mesmo arquivo
**como lista pura** e a meta é perdida (`load_plan_meta` → todos `None`).

### Causa

`src/training_plan.py::cmd_reconcile` (linha 317) chama
`save_plan(plan, PLAN_FILE)` **sem os argumentos de meta** — `save_plan` só
gera o formato dict quando `goal is not None`.

### Impacto

- Hoje: baixo — `load_plan_meta` só é importado, não consumido (GOAL/RACE_DATE
  vêm do `.env` em cada comando).
- **Com a #6:** os `ftp_candidates` serão gravados na meta e o `reconcile`
  (rodado todo dia no timer) os apagaria todo dia. Tratar antes do #6.

### Direção de solução

`cmd_reconcile` carrega a meta (`load_plan_meta`) e a regrava junto
(`save_plan(plan, PLAN_FILE, **meta)`). Teste: build → reconcile → meta igual.

### Correção (implementada)

`cmd_reconcile` carrega a meta (`load_plan_meta(PLAN_FILE)`) e a regrava junto
(`save_plan(plan, PLAN_FILE, goal=..., race_date=..., ftp_test_date=...)`).
Sem GOAL (formato antigo), continua lista pura — compatível. Testes:
`ReconcileMetaTest` em `tests/test_training_plan.py` (build → reconcile → meta
preservada; formato antigo continua lista). Validado no fluxo real: build →
reconcile → meta `{'goal': 'ftp-builder', 'race_date': None,
'ftp_test_date': '2026-10-22'}` intacta.

### Registro

- 2026-09-22: encontrado na S2/S6 do `docs/ROTEIRO-TESTES.md`; issue aberta no
  GitHub (#8).

---

## Nota defensiva: `workout_text`/`event_payload` com `lang` inválida

**Status:** nota (sem issue própria) · **Severidade:** defensiva — **não
alcançável pela CLI** · **Encontrado em:** 2026-09-22 (S7)

`event_payload(..., lang="zz")`/`workout_text(..., lang="zz")` levanta
`KeyError: 'zz'` em `FOCUS_ZONE_HINT[focus][lang]`. Na CLI isso não acontece:
`cmd_push` usa `get_cue_lang()`, que normaliza para `pt` com aviso. Risco
apenas se um futuro código chamar as funções de texto com `CUE_LANG` cru.
Direção: normalizar dentro de `workout_text` (defesa em profundidade) quando
houver revisão do módulo.
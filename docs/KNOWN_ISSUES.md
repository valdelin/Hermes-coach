# Issues conhecidas — Hermes Coach

Lista de bugs conhecidos e pendências técnicas registradas, com rastreio no
GitHub. Formato: cada issue tem status, impacto, mitigação atual e direção de
solução.

---

## #1 — Intervals cria atividade MANUAL "fantasma" a partir do evento planejado

**GitHub:** [valdelin/Hermes-coach#1](https://github.com/valdelin/Hermes-coach/issues/1)
**Status:** aberto (aceito; não bloqueia o fluxo) · **Severidade:** cosmética/baixa

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
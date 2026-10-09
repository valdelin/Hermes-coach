# UI-2 — Identidade local (`HermesWorkoutId`) e lifecycle do treino

> Dono: **repo** (`docs/UI-2-LIFECYCLE.md`). Espelho de leitura no vault Obsidian.
> Escopo: UI-2 da UI Foundation. Não substitui `docs/ROADMAP.md` (fonte de prioridade).

## 1. Problema

Antes do UI-2, o treino local era identificado por `external_id`
(`hermes-plan-YYYY-MM-DD`), que acumulava três papéis:

1. **identidade** (chave do livro-razão `absorbed_ids`);
2. **vínculo com o provider** (o Intervals usa `external_id` no `bulk-delete`/upsert);
3. **heurística de conclusão** (`paired_activity_id` presente ⇒ "feito").

Isso acoplava a noção de "qual treino é este" ao Intervals. O UI-2 separa os
eixos: **identidade local** e **lifecycle local** passam a ser explícitos;
provider continua como *linkage* e *evidência*, não como ontologia.

## 2. `HermesWorkoutId`

Identidade local e estável, em `src/workout_identity.py`, campo `id` do workout.

**Formato:** UUIDv5 (RFC 4122) com namespace fixo do Hermes, derivado do `day`
ISO do treino (`uuid5(uuid5(NAMESPACE_URL, "https://hermes-coach.local/workout"), day)`).

Critério da escolha (não por novidade):

| Requisito | Como atende |
|---|---|
| gerado pelo Hermes | namespace e algoritmo são nossos |
| estável entre leituras/escritas | derivado só do `day`; determinístico |
| independente do provider | não usa `external_id` nem id de evento |
| serializável | string UUID canônica |
| testável | puro, sem rede |
| não derivado de posição em lista | chave do domínio é o dia, não índice |
| não depende de `external_id` | idem |

**Por que não UUIDv4 aleatório?** O plano tem no máximo **um treino por dia**
(`build_plan` substitui o dia ao inserir prova/recuperação/FTP-test), então o dia
é chave natural. Um id aleatório exigiria reconciliar identidade a cada rebuild e
não teria migração determinística de planos antigos.

**Fallback:** plano legado degenerado sem `day` deriva de `external_id`. É último
recurso, documentado, e não ocorre em planos reais.

## 3. Compatibilidade com planos antigos

- `Application.load_plan` enriquece em memória: `id` (UUIDv5 do dia) e
  `lifecycle` (default `planned`).
- **Determinístico:** o mesmo plano antigo recebe o mesmo `id` em toda leitura —
  não há id novo por load.
- `Application.save_plan` enriquece antes de gravar: a identidade **estabiliza
  na próxima persistência**. `cmd_build`, `cmd_reconcile`, `cmd_check` e
  `cmd_push` passam pela Application.
- O módulo de domínio `plan.py` continua agnóstico de identidade; `plan.json`
  antigo (lista pura ou `{meta, workouts}`) continua legível.

Sem versionamento de schema novo: os campos são **aditivos**. `load_plan` de
baixo nível não é alterado.

## 4. Lifecycle local (`src/lifecycle.py`)

Duas camadas, de propósito:

- **Declarado** — persistido em `workout["lifecycle"]`, default `planned`:
  intenção local, sem provider.
  `planned | postponed | substituted | cancelled | completed | missed`.
- **Observado** — resolvido em tempo de leitura por `lifecycle.derive`:
  `completed`/`missed` derivam de (data + evidência). Um declarado != `planned`
  vence a derivação (inclui `completed`/`missed` retro-atestados).

`derive(day, today, is_done, declared)`:
`declared != planned` → devolve `declared`; senão `day >= hoje` → `planned`;
senão `is_done` → `completed`, senão `missed`.

### Transições

| Origem | Destinos válidos | Causa | Depende de sync? |
|---|---|---|---|
| `planned` | completed, missed, postponed, substituted, cancelled | execução / dia venceu / decisão local | só `completed`/`missed` |
| `postponed` | planned, completed, missed, substituted, cancelled | sessão adiada resolve | conforme destino |
| `substituted` | planned, completed, missed, cancelled | troca resolve | conforme destino |
| `cancelled` | planned | reabrir sessão | não |
| `missed` | planned, completed, postponed, substituted, cancelled | remediação manual | conforme destino |
| `completed` | — (terminal) | observado; UI-4 define reversão por re-sync | — |

`validate_transition` levanta `ValueError` em transição inválida ou estado
desconhecido. Estados desconhecidos são normalizados para `planned` em `ensure`.

### `reconciled` não é lifecycle

No domínio atual, "reconciliado" descreve o **livro-razão de faltas já
absorvidas** (`absorbed_ids` no `plan.json`) — status de processamento, não
estado do treino. Forçá-lo como lifecycle misturaria os eixos. Fica separado.

### Lifecycle ≠ sync de provider

O estado de sincronização (`publicada` / `nao_publicada` / `concluida` /
`estado_desconhecido`) vive em `plan.session_execution_state` e é **outro eixo**.
`completed` no lifecycle significa "há evidência de execução"; ele é derivado
usando `session_execution_state` apenas como evidência. UI-4 unifica
completion/sync e completion local.

## 5. Application API (UI-2)

`Application` (UI-1) ganhou:

- `load_plan` / `save_plan` — enriquecem id + lifecycle.
- `get_workout(workout_id)` / `workout_lifecycle(workout_id)` — leitura local.
- `derive_workout_lifecycle(workout_id, events, today)` — lifecycle efetivo
  (usa provider só como evidência; não grava, não publica).
- `set_workout_lifecycle(workout_id, state)` — transição validada + persistência
  local. `KeyError` se o id não existe; `ValueError` se a transição é inválida.
- `postpone_workout` / `cancel_workout` — atalhos para estados declarados.

Nenhuma dessas operações toca no calendário do Intervals nem exige rede.

## 6. `external_id` / `paired_activity_id` — auditoria (classificação)

| Uso | Classificação | Ação no UI-2 |
|---|---|---|
| `plan.build_plan` / `_prep_workout` / `_race_workout` cria `hermes-plan-*` | provider linkage (id determinístico de publicação) | mantido; o id local agora é separado |
| `plan.orphan_external_ids`, `plan.manual_duplicate_ids`, `push` | provider linkage | mantido |
| `plan.reconcile` (`done_ids`, `absorbed_ids`) | heurística de conclusão + livro-razão | mantido (UI-4); a identidade local é 1:1 com o dia |
| `plan.session_execution_state`, `_done_and_extra` | heurística de conclusão | mantido como evidência; documentado |
| `plan.adherence_report` | heurística de conclusão | **migrado** para `lifecycle.derive` |
| `recovery.actual_daily_load`, `activity_summary`, `ftp_scan` | heurística de conclusão / linkage | fora de escopo (UI-4) |
| `readiness.py` | linkage de evento | inalterado |
| `plan_run.py` | feature de corrida separada | fora de escopo |

## 7. Fora de escopo (UI-3/UI-4)

`ProviderCapabilities`/`IntervalsAdapter`/DTOs (UI-3); completion local
persistida, snapshot normalizado, sync freshness e reconcile local-first (UI-4);
`ApplicationState`/`PlanView` (UI-5); heurísticas fisiológicas e PMC-1/POL-1/RDY-1.

## 8. Testes

- `tests/test_workout_identity.py` — id determinístico, idempotência, plano legado.
- `tests/test_lifecycle.py` — default, `derive`, transições.
- `tests/test_application.py` — identidade/lifecycle via Application sem rede;
  persistência; transição inválida; `derive` com evidência do provider.

Referência de diagrama: `docs/DIAGRAMAS.md` §6 (`Planejado`/`Feito`/`Perdido`).

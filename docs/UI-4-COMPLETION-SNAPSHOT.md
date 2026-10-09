# UI-4 — Completion local, snapshot normalizado e sync freshness

> Dono: **repo** (`docs/UI-4-COMPLETION-SNAPSHOT.md`). Espelho de leitura no vault.
> Escopo: UI-4 da UI Foundation. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §11).

## 1. Objetivo

Separar três eixos que antes se confundiam no payload cru do Intervals:

| eixo | onde vive | o que significa |
|---|---|---|
| **lifecycle local** | `workout["lifecycle"]` (UI-2) | intenção/estado do treino, persistido |
| **completion evidence** | `workout["completion"]` (UI-4) | que evidência externa concluiu o treino |
| **sync freshness** | `training_snapshot.json → freshness` (UI-4) | quando o provider foi observado |

O provider **não define** o estado ontológico do workout: ele fornece evidência.

## 2. Arquitetura

```text
Provider (Intervals.icu)
      ↓  IntervalsAdapter  (normaliza payload, UI-3)
records normalizados + provider_fields (leitura canônica)
      ↓
Application
   ├─ sync_provider_state()   → fetch + snapshot + reconcile_completion
   ├─ reconcile_completion()  → matching → HermesWorkoutId → lifecycle local
   ├─ completion_status()     → leitura LOCAL (sem provider)
   ├─ load_training_snapshot()/sync_freshness()
      ↓
CLI / futura UI
```

## 3. Completion local

`Application.mark_completed(workout_id, source=..., observed_at=..., ...)`:

- transição de lifecycle validada (`planned → completed`; `cancelled → completed`
  é `ValueError` — nunca sobrescreve estado declarado em silêncio);
- grava `workout["completion"] = {"source", "observed_at",
  "provider_event_id", "activity_id"}`;
- persiste no `plan.json` (mesmo formato, campos aditivos; ver §8);
- não publica no calendário nem toca no provider.

Fontes (`lifecycle`): `local`, `provider_match`, `reconcile`. `completed`
permanece **terminal** (UI-2); UI-4 não introduz reversão implícita.

`Application.completion_status(workout_id)` responde "este treino está concluído
localmente?" lendo apenas o plano persistido — **sem provider**.

## 4. Evidência e matching

`match_events_to_workouts(plan, events)` casa evidência observada com treinos
locais usando `external_id` como **descoberta** (mecanismo atual, biunívoco no
sistema) e devolve um mapa chaveado por **`HermesWorkoutId`**. Só eventos
concluídos (`provider_fields.is_completed`) e com `external_id` entram.

```text
provider evidence → matching (external_id) → HermesWorkoutId → lifecycle local
```

`reconcile_completion()` aplica o mapa: `planned → completed` com metadado;
estado declarado `!= planned` gera **conflito** (preservado, reportado);
`completed` já existente é `unchanged` (idempotente).

## 5. Fronteira de leitura canônica (`provider_fields`)

O domínio passou a ler por **nome canônico** (`field(record, "training_load")`,
`is_completed(record)`), nunca por campo do provider. `provider_fields.py`
centraliza, **em um único lugar**, o mapa `icu_*`/`restingHR`/`paired_activity_id`
→ canônico. Records normalizados resolvem na hora; dicts brutos legados (planos
antigos, fakes de teste) continuam legíveis pelos aliases.

Trade-off explícito: preferimos uma **camada de compatibilidade única** a
reescrever 70+ fixtures de teste ou a aceitar `icu_*` espalhado no domínio. O
mapa é provider-specific e vive no boundary — junto do adapter, não do domínio.

## 6. Snapshot e freshness

`src/snapshot.py`:

| estrutura | campos | persistência |
|---|---|---|
| `TrainingSnapshot` | `events`, `wellness`, `activities`, `metrics`, `captured_at`, `provider`, `freshness` | arquivo `training_snapshot.json` |
| `SyncFreshness` | `synced_at`, `provider`, `stale_after_hours`, `status` | dentro do snapshot |

- Eventos/wellness/atividades são gravados **canônicos** (via
  `provider_fields.canonical`), então ler o snapshot não exige conhecer o
  provider nem rede.
- `FreshnessStatus`: `fresh` / `stale` / `unknown`. `unknown` quando nunca houve
  sync. O limiar é uma **política operacional explícita**
  (`DEFAULT_STALE_AFTER_HOURS = 36`, sobrescrevível) — não um threshold
  fisiológico nem prescritivo. Idade (`age_seconds`) também é exposta para quem
  preferir calcular no consumidor.
- **Não poluímos o `plan.json`**: plano e cache têm ciclos de vida diferentes;
  o snapshot vai para arquivo separado (sibling do `plan.json`).

## 7. Application API (UI-4)

| método | rede? | função |
|---|---|---|
| `mark_completed(id, source=...)` | não | marca conclusão local e persiste |
| `completion_status(id)` | não | lê completion local |
| `reconcile_completion(events=/snapshot=)` | não | evidência → lifecycle local |
| `load_training_snapshot()` / `sync_freshness()` | não | lê cache/freshness persistidos |
| `save_training_snapshot(snap)` | não | persiste cache |
| `sync_provider_state(...)` | sim | fetch → snapshot + reconcile |

`sync_provider_state` é a única operação de rede; falha do provider devolve
`SyncResult(ok=False, error=...)`, não corrompe estado e **não impede** as
leituras locais (§1 de `provider.py`).

## 8. Compatibilidade

- `plan.json` ganha apenas campos aditivos por workout (`completion`,
  `lifecycle`, `id`); planos antigos seguem legíveis (defaults determinísticos).
- `absorbed_ids` continua por `external_id` (ledger histórico, eixo separado):
  migração para `HermesWorkoutId` não é segura sem quebrar planos antigos →
  **mantida compatibilidade**, documentada.
- Snapshot ausente/corrompido → snapshot vazio, sem erro.
- Eventos legados com `icu_*`/`paired_activity_id` continuam funcionando (§5).

## 9. Migração dos consumidores de `icu_*`

| arquivo | antes | depois |
|---|---|---|
| `coach.py` `_raw_metrics` | `item.get("icu_ctl"/"icu_atl"/"icu_ftp"/"icu_training_load")` | `field(item, "ctl"/"atl"/"ftp"/"training_load")` |
| `recovery.py` `actual_daily_load`/`fetch_full_history` | `e.get("paired_activity_id")`, `icu_training_load`, `id/uid` | `is_completed(e)`, `field(...)` |
| `impulse_response.py` `daily_load_by_date`/`_day` | `icu_training_load`, `start_*_local` | `field(item, "training_load"/"start_date")` |
| `activity_summary.py` `done_activities` | `activity_id/paired_activity_id`, `icu_average_watts`, … | `field(...)` canônico |
| `plan.py` `session_execution_state`/`_done_and_extra`/`avg_load`/`_day` | `paired_activity_id`, `icu_training_load`, `external_id` cru | `is_completed`, `field(...)` |

Comportamento preservado: 892 testes anteriores seguem verdes sem alteração.
Nenhum valor de PMC é recalculado; `form_pct` **não** implementado (PMC-1).

## 10. Vazamentos restantes (classificação)

| ocorrência | classificação |
|---|---|
| `provider_fields.py` (mapa de aliases) | **boundary** de compatibilidade |
| `intervals_adapter.py` (`icu_*`, builders) | adapter/provider boundary |
| `plan.py`, `coach.py`, `recovery.py`, `impulse_response.py`, `activity_summary.py`, `training_plan.py`, `plan_run.py` | **somente prosa** (docstrings/comentários/mensagens) |
| `ftp_scan.py` (`paired_activity_id`, `external_id`) | provider-specific (diagnóstico de FTP) |
| `external_id` no domínio | linkage/metadado de matching (permitido) |
| `provider.py` (`TrainingEvent.is_completed`) | contrato normalizado (boundary) |

`grep -R "icu_ctl|icu_atl|icu_tsb|icu_training_load" src` não retorna **nenhuma
leitura de código** fora de `provider_fields.py`/`intervals_adapter.py`.

## 11. Critérios UI-4 = DONE

1. completion local persistido — sim (`lifecycle` + `completion`);
2. não depende ontologicamente de `paired_activity_id` — sim (estado é lifecycle);
3. evidência atualiza por `HermesWorkoutId` — sim;
4. reconcile usa a identidade local após matching — sim;
5. snapshot normalizado existe e é usado — sim (`sync_provider_state` /
   `reconcile_completion`);
6. domínio não consome payload cru nos caminhos migrados — sim;
7. freshness/timestamp explícito — sim;
8. leitura local sem provider — sim;
9. sync/reconcile idempotente — sim;
10. backward compatibility — sim;
11. testes verdes — sim (920, 3 skips).

UI-3 vira **DONE** como consequência: `icu_*` restritos ao boundary; Application
sem `icu_*`; DTOs/snapshot normalizados efetivamente usados.

## 12. Testes

- `tests/test_provider_fields.py` — leitura canônica, aliases, `is_completed`, `canonical`.
- `tests/test_snapshot.py` — freshness, roundtrip, arquivo ausente/corrompido.
- `tests/test_completion.py` — completion local, persistência/reload, leitura sem
  provider, idempotência, sem-match, conflito, terminal, snapshot/freshness,
  provider indisponível, `plan.json` limpo, backward compatibility.

# UI-3 — Provider boundary: capabilities, `IntervalsAdapter` e records normalizados

> Dono: **repo** (`docs/UI-3-PROVIDER-BOUNDARY.md`). Espelho de leitura no vault.
> Escopo: UI-3 da UI Foundation. `docs/ROADMAP.md` é a fonte de prioridade.

## 1. Objetivo e status

Transformar a integração com o Intervals.icu em um adapter explícito atrás de
contratos de provider, para que a Application consuma records normalizados sem
conhecer `icu_*`.

**Status: DONE** (fechado por UI-4, 04/10/2026). O boundary de provider e a
Application estão completos (leitura/escrita normalizadas, capabilities, erros,
composição). O *event model* do domínio determinístico (`plan`, `recovery`,
`impulse_response`, `activity_summary`, `coach`) migrou para o acesso canônico em
UI-4 (`src/provider_fields.py`): `grep -R "icu_ctl|icu_atl|icu_tsb|icu_training_load" src`
não retorna nenhuma **leitura de código** fora de `provider_fields.py` (boundary) e
`intervals_adapter.py` (adapter); as demais ocorrências são prosa. Ver §10.

## 2. Arquitetura

```text
CLI / futura UI
      ↓
Application (application.py)      # não conhece icu_* (teste de regressão)
      ↓
provider.py                       # contratos, capabilities, records, erros
      ↓
IntervalsAdapter (intervals_adapter.py)  # único que conhece icu_*/HTTP
      ↓
IntervalsClient → API Intervals.icu
```

## 3. Contratos criados

| contract | responsabilidade | consumidores |
|---|---|---|
| `TrainingMetricsProvider` (Protocol) | `events(oldest,newest)`, `wellness(oldest,newest)` | `build_workouts`, `reconcile_workouts`, `recovery_outlook`, `assess_daily_readiness` |
| `ActivityProvider` (Protocol) | `activity(id)` | `summarize_period` (via `activity_summary.done_activities`) |
| `WorkoutSyncProvider` (Protocol) | `create_events`, `delete_events`, `delete_event` | `push_workouts` |
| `NormalizedRecord` (Mapping) | payload original + acessores normalizados | todos os records |
| `TrainingEvent` | evento/treino normalizado + `is_completed` | fluxos acima |
| `WellnessSnapshot` | wellness observado | readiness/build/check |
| `ActivitySnapshot` | atividade realizada | resumo |
| `provider_capabilities(provider)` | lê `provider.capabilities` | `Application.provider_capabilities` |

`TrainingMetricsProvider` continua sendo o mesmo contrato do UI-1, agora definido
em `provider.py` e reexportado por `application.py` (sem duplicar Protocol).

## 4. Capabilities

`ProviderCapability(str, Enum)`, declaradas por `IntervalsAdapter.capabilities`:

| capability | significado | Intervals |
|---|---|---|
| `READ_EVENTS` | ler eventos/treinos | sim |
| `READ_WELLNESS` | ler wellness diário | sim |
| `READ_ACTIVITIES` | ler detalhe de atividade | sim |
| `WRITE_WORKOUTS` | criar treinos | sim |
| `UPDATE_WORKOUTS` | upsert de treinos | sim |
| `DELETE_WORKOUTS` | remover treinos/duplicatas | sim |
| `COMPLETION_LINKS` | expõe vínculo de execução | sim |

Permite decidir capacidade sem `if provider_name == "intervals"`.

## 5. `IntervalsAdapter`

`src/intervals_adapter.py`. Único ponto com nomes de campo do Intervals.

- **Leitura:** `events`, `wellness`, `activity` → records normalizados.
- **Escrita:** `create_events(payloads, upsert=True)`, `delete_events`,
  `delete_event` — delegam ao client. `upsert=True` (default do client) não é
  repassado como kwarg, preservando fakes existentes.
- **Utilitários específicos** (ftp-scan): `activity_streams`, `sport_settings`,
  `put_sport_settings` — passthrough explícito dentro do boundary.
- **Erros:** `IntervalsApiError` (com `status`) e `requests.RequestException`
  são traduzidos para `ProviderError`: 401/403 → `ProviderAuthError`;
  429/5xx/sem status → `ProviderUnavailable`; demais 4xx → `ProviderOperationError`.
  Nada de `requests`/HTTP vaza para a Application. `IntervalsApiError` ganhou
  `.status` (aditivo; mensagens inalteradas).
- **Comportamento:** nenhuma mudança semântica em read/push; retry/backoff do
  client permanece no client.

## 6. Records normalizados

| DTO | campos principais | origem (Intervals) | consumidores |
|---|---|---|---|
| `TrainingEvent` | `provider_event_id`, `start_date`, `category`, `type`, `name`, `training_load`, `tss`, `ctl`, `atl`, `tsb`, `ftp`, `external_id`, `paired_activity_id`, `activity_id` | `id`/`uid`, `start_date_local`, `category`, `type`, `name`, `icu_training_load`, `tss`, `icu_ctl`, `icu_atl`, `icu_tsb`, `icu_ftp`, … | Application use cases / domínio |
| `WellnessSnapshot` | `day`, `resting_hr`, `hrv`, `hrv_sdnn`, `sleep_secs`, `steps`, `stress`, `weight` | `id`/`date`, `restingHR`, `hrv`, `hrvSDNN`, `sleepSecs`, `steps`, `stress`, `weight` | readiness |
| `ActivitySnapshot` | `provider_activity_id`, `day`, `name`, `type`, `training_load`, `moving_time`, `distance`, `elevation_gain`, `avg_power`, `np`, `avg_hr` | `id`, `start_date_local`, `icu_training_load`/`tss`, `icu_average_watts`, `icu_weighted_avg_watts`, `average_heartrate` | resumo |

Semântica do `Mapping` (compatibilidade):

- chave presente no payload original → devolve o valor bruto (consumidores
  legados idênticos);
- chave só normalizada e não-`None` → devolve o normalizado (ex.: `get("ctl")`);
- ausente/`None` → `None` em `.get` e `KeyError` em `[]` (preserva defaults);
- `dict(record)` continua sendo o payload original.

`TrainingMetricsSnapshot` não foi criado: o projeto já tem `coach.Metrics` como
DTO de métricas. `ProviderWorkoutRef` não foi necessário: push usa payloads do
próprio domínio e orfãos/duplicatas já trafegam como records.

## 7. PMC

`icu_ctl → ctl`, `icu_atl → atl`, `icu_tsb → tsb`, `icu_training_load →
training_load`. **Observados do Intervals; não recalculados.** `form_pct`, PMC
View e threshold −30% **não** implementados (PMC-1/POL-1).

## 8. Identidade × linkage

`HermesWorkoutId` continua a identidade local (UI-2). `external_id`,
`provider_event_id`, `paired_activity_id` e `activity_id` são **linkage
metadata**, expostos como campos do record — nunca chave do domínio local.

## 9. Composition root

`training_plan.get_provider()` constrói `IntervalsAdapter(get_client())`;
`_make_app()` injeta esse provider por padrão. Handlers de build/reconcile/push/
summary/recovery/check recebem o adapter; `get_client()` cru permanece apenas em
handlers de diagnóstico que já operam no client (`info`, `ftp-scan`, `model`,
`periodization`). Testes continuam injetando um client fake via
`tp.get_client`, agora envolvido pelo adapter.

## 10. Auditoria de vazamento (pós-UI-3)

| ocorrência | classificação |
|---|---|
| `intervals_adapter.py` (parse `icu_*`, erros) | adapter/provider boundary |
| `provider.py` (nominal de linkage `external_id`/`paired_activity_id`) | legítimo (contrato normalizado) |
| `provider_fields.py` (mapa de aliases `icu_*`→canônico) | boundary de compatibilidade de leitura (UI-4) |
| `plan.py`, `recovery.py`, `impulse_response.py`, `activity_summary.py`, `coach.py` | resolvido em UI-4: leem por `field(...)`/`is_completed(...)`; `icu_*` restante é só prosa |
| `training_plan.py`, `plan_run.py` | só prosa (docstrings/mensagens/comentários), sem código |
| `workout_identity.py`, `lifecycle.py` | comentários mencionando `external_id` como linkage |
| `ftp_scan.py` (`paired_activity_id`/`external_id`) | feature provider-specific (diagnóstico de FTP) — fora do escopo UI-4 |

`grep -n "icu_" src/application.py` → vazio (coberto por
`tests/test_application.py::ProviderBoundaryTest.test_application_nao_conhece_campos_icu`).

**Fechado como DONE por UI-4 (04/10/2026):** o event model do domínio passou a usar
os nomes canônicos via `provider_fields`; nenhuma leitura de código de `icu_*`
resta fora do boundary (`provider_fields.py`/`intervals_adapter.py`).

## 11. Testes

- `tests/test_provider.py` — mecânica dos records, `None`/ausentes, capabilities, erros.
- `tests/test_intervals_adapter.py` — tradução event/wellness/activity, capabilities, push, erros HTTP→ProviderError.
- `tests/test_application.py::ProviderBoundaryTest` — Application consumindo records normalizados, capabilities, `_event_is_done`, ausência de `icu_*` na Application.
- `tests/test_training_plan.py` — fluxos CLI via adapter (sem rede).

Sem rede em nenhum teste da fronteira.

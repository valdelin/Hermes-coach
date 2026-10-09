# UI-5 — ApplicationState / PlanView: contrato de leitura para UI

> Dono: **repo** (`docs/UI-5-APPLICATION-STATE.md`). Espelho de leitura no vault.
> Escopo: UI-5 da UI Foundation. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §9).

## 1. Objetivo

Uma CLI, uma futura UI gráfica e uma futura API precisam ler o estado do Hermes
do **mesmo jeito**, sem saber que existe `plan.json`, `IntervalsAdapter`,
`icu_*`, `paired_activity_id` ou `external_id`.

```text
Providers / persistence
        ↓
Application
        ↓
ApplicationState / PlanView      ← ui_state.py (imutável, sem I/O)
        ↓
CLI / futura UI / API
```

Views **representam estado**. Não sincronizam, não chamam provider, não alteram
lifecycle, não recalculam PMC nem prescrevem treino. RDY-1 acrescenta uma query
separada que expõe o resultado da **heurística já existente** sobre o snapshot
local; ela não chama policy nem altera estado. Modificar estado continua sendo
responsabilidade dos commands/use cases.

## 2. Contratos

Todos em `src/ui_state.py`, `@dataclass(frozen=True)` + `to_dict()`:

| DTO | responsabilidade | fonte |
|---|---|---|
| `ApplicationState` | container de leitura do estado atual | `plan` + `snapshot` |
| `PlanView` | plano local + agregados de apresentação | `plan.json` + lifecycle + completion |
| `WorkoutView` | um treino, visto por consumidor | id local, declared/efetivo, completion, linkage |
| `PlanMetaView` | `goal`/`race_date`/`ftp_test_date` | meta do plano |
| `CompletionView` | completion **local** (UI-4) | `workout["completion"]` |
| `ProviderLinkView` | linkage com o provider (nunca identidade) | `external_id` + evidência |
| `SnapshotView` | cache normalizado em leitura | `training_snapshot.json` (UI-4) |
| `FreshnessView` | idade/estado da última sync | `SyncFreshness` (UI-4) |
| `ReadinessView` | observações + trace heurístico existente, sem policy | query RDY-1 sobre `SnapshotView` |
| `CtlRampView` | tendência de CTL observada, sem policy | query HR-1 sobre histórico do `SnapshotView` |

**Um conceito, uma representação.** Não existe `SyncView`: a idade da última
sincronização já está em `SnapshotView.freshness`. Não existe `SnapshotDTO` /
`TrainingSnapshotView` em paralelo ao `TrainingSnapshot` — a View apenas
expõe o que já está normalizado e persistido. A PMC lida pelo contrato é
`SnapshotView.pmc` (`PmcView`), que **substituiu** o dict `metrics` sem tipagem
introduzido aqui (PMC-1).

## 3. Query pura

```python
state = app.get_application_state(today=..., now=...)
view  = app.plan_view(today=...)
```

Garantias (cobertas por `tests/test_ui_state.py::SideEffectFreeTest`):

- não escreve `plan.json` (nem muda mtime);
- não escreve nem altera `training_snapshot.json`;
- não chama provider (o teste injeta `client_factory` que **levanta**);
- não altera lifecycle nem freshness;
- não muda `lifecycle` declarado;
- é determinística: duas consultas seguidas devolvem o mesmo `to_dict()`.

Offline por construção: provider indisponível, token inválido ou sem rede
mantêm a leitura servindo o último estado persistido. O caminho de escrita é
`Application.sync_provider_state` (UI-4) — deliberadamente separado.

## 4. Declared vs effective

`WorkoutView` expõe os dois e nunca esconde a diferença:

- `lifecycle_declared`: o que está **persistido** (`planned` por default);
- `lifecycle_effective`: o que o usuário vê — `lifecycle.derive` (UI-2) com
  `today` injetado. Estado declarado ≠ `planned` sempre vence.
- `lifecycle`: atalho para o efetivo.
- `completed`: derivado do efetivo, nunca de campo do provider.

A evidência `is_done` do `derive` vem do **completion local** (UI-4), não do
provider — por isso a View resolve offline e sem rede.

`conflict=True` marca a situação que uma UI precisa enxergar: existe evidência
de provider (`activity_id`/`provider_event_id`/fonte `provider_match`) com estado
declarado incompativel (ex.: cancelado localmente). A View não resolve o
conflito — ela o **exibe**. A resolução é do `reconcile_completion`.

## 5. Próximo treino

`PlanView.next_workout` é **derivado**, não prescritivo: primeiro treino com
lifecycle efetivo em `{planned, postponed, substituted}` e `day >= today`.
Nenhuma periodização, heurística ou regra nova foi introduzida.

Agregados expostos (todos contagens diretas, sem insight): `has_plan`,
`start_date`, `end_date`, `workout_count`, `completed_count`, `missed_count`,
`next_workout`. É leitura, não analytics.

## 6. Serialização

`to_dict()` em toda View. Datas/timestamps em ISO-8601 (`str`), enums de
lifecycle/freshness em texto (`planned`, `fresh`), `None` preservado, estrutura
determinística e sem qualquer objeto de provider/cliente dentro da View
(garantido por `SerializationTest`). Suficiente para UI/API; **nenhum** HTTP,
web server ou REST foi construído.

## 7. Relação com UI-1..UI-4

| etapa | o que UI-5 consome |
|---|---|
| UI-1 | `Application` como seam e injeção de dependências |
| UI-2 | `HermesWorkoutId` + `lifecycle` declared/derive |
| UI-3 | `SyncFreshness`/records normalizados (nada de `icu_*` chega aqui) |
| UI-4 | `TrainingSnapshot`, `SyncFreshness`, completion local |

`ui_state.py` não importa `application`, `provider` nem `provider_fields`: usa
`lifecycle` e importa `readiness` tardiamente apenas para a query RDY-1
reutilizar a heurística pura existente. Verificado por teste que tokeniza a
fonte e ignora comentários.

## 8. CLI consumindo View

`cmd_adherence` passou a usar `app.get_application_state()` para decidir a
existência do plano e `app.load_plan()` para o cruzamento com o provider.
`stdout` foi mantido idêntico (verificado nos dois caminhos: sem plano e com
plano). Única mudança de comportamento, deliberada e documentada: um
`plan.json` **existente porém vazio** agora responde `sem plan.json: rode
build primeiro` em vez de imprimir um relatório vazio — que é a orientação
correta. Nenhum outro handler foi tocado (evita churn).

## 9. Critérios UI-5 = DONE

| # | critério | evidência |
|---|---|---|
| 1 | contrato de estado independente de UI | `ui_state.py` não importa `application`/`provider` |
| 2 | representação de plano/workouts | `PlanView`/`WorkoutView` |
| 3 | identidade local exposta | `WorkoutView.id` (`HermesWorkoutId`) |
| 4 | lifecycle/completion sem inferência provider-specific | `declared`/`effective` + `CompletionView` local |
| 5 | freshness acessível | `SnapshotView.freshness` (`FreshnessView`) |
| 6 | estado sem provider | `ApplicationStateTest` com `client_factory` que levanta |
| 7 | query sem side effects | `SideEffectFreeTest` (plan.json/snapshot/lifecycle intactos) |
| 8 | consumidor não lê `plan.json` cru | Views são o contrato; `cmd_adherence` migra |
| 9 | DTOs testáveis e estáveis | 27 testes em `tests/test_ui_state.py` |
| 10 | suíte verde | nenhuma falha nova (ver §11) |

## 10. Fora do escopo (deliberado)

Policy `-30%` (POL-1), heurísticas HR-1..HR-4, UI gráfica, web server, REST
API, banco, novo provider. RDY-1 passou a expor observações e a heurística
existente sem criar placeholder, policy ou prescrição.

## 11. Suíte

- **947 testes**: 943 passed, 3 skipped, **1 failed (pré-existente)**.
- A falha é `tests/test_readiness_step_a.py::IntegracaoCliTest::test_saida_avisa_quando_a_leitura_nao_foi_aplicada`.
- Verificada no worktree limpo em `931fe16` (anterior a UI-1): **já falhava**
  (`811 testes, 1 failure`). Não é regressão desta etapa.
- Causa provável (afrota, fora do escopo UI-5): o fixture cria registros de
  wellness de ontem até **amanhã**, então a decisão de prontidão aplica-se ao
  primeiro dia do plano (amanhã) em vez de ser rejeitada como "leitura de
  ontem". O teste assume uma premissa que o próprio fixture contradiz.
  Corrigir isso toca em comportamento de readiness e merece tarefa própria.

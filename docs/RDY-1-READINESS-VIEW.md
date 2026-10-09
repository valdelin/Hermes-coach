# RDY-1 — Readiness View: dados, heurística e policy separados

> Dono: **repo** (`docs/RDY-1-READINESS-VIEW.md`). Espelho de leitura no vault.
> Escopo: RDY-1. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §10).

## 1. Objetivo

`ReadinessView` dá à futura UI uma resposta local para: **quais sinais de
readiness existem agora e o que a heurística atual classificou?** Sem provider,
CLI, `argparse`, payload cru, policy ou prescrição.

```text
TrainingSnapshot normalizado (UI-4) + PmcView (PMC-1)
                         ↓
            ReadinessView (RDY-1, imutável)
                         ↓
                UI / API futura / CLI futura
```

API de leitura:

```python
view = app.get_readiness_view(today=..., now=...)
```

É query separada de `get_application_state()`: readiness possui um `target_day`
explícito e roda a heurística existente sobre o cache local. `ApplicationState`
permanece barato e não ganha um acoplamento temporal adicional.

## 2. Auditoria do estado anterior

`readiness.py` continha três responsabilidades no mesmo módulo:

| camada | implementação existente | comportamento em RDY-1 |
|---|---|---|
| observação | wellness: RHR, HRV/HRV SDNN, sono, readiness composto | normalizado e exposto em `WellnessView` |
| heurística | `assess_readiness_assessment` → `ReadinessAssessment`/`ReadinessTrace` → GREEN/YELLOW/RED | reutilizada sem mudar thresholds |
| policy/prescrição | `readiness_decision` → `ReadinessAction.NONE/REDUCE/REPLACE`, depois `build`/`check --apply` | **não chamada** pela View; fluxo existente preservado |

O módulo também possui o legado `assess_readiness`/`suggest_swap`. RDY-1 não o
redesenha. A única adaptação de entrada é `_normalized_wellness_records`: aceita
o snapshot canônico UI-4 e preserva as chaves legadas internamente, de modo que
o algoritmo, thresholds e saída de CLI não mudam. `today=` opcional em
`assess_readiness_assessment` torna `stale_days` determinístico para a query e
testes; a chamada antiga mantém `date.today()` como default.

## 3. Contrato

Todos os DTOs vivem em `src/ui_state.py`, são `@dataclass(frozen=True)` e têm
`to_dict()`:

| campo | categoria | origem | semântica |
|---|---|---|---|
| `target_day` | contexto | chamador | dia para o qual a leitura é consultada |
| `reference_day` | observado/contexto | último wellness | dia que os sinais realmente descrevem |
| `wellness.resting_hr`, `hrv`, `hrv_sdnn`, `sleep_secs`, `sleep_score`, `readiness_score`, `stress` | observado | snapshot normalizado/provider | valor observado, unidade preservada, ausência = `None` |
| `pmc.ctl`, `atl`, `tsb` | observado | `PmcView`/provider | PMC observado, não recalculado |
| `pmc.form_pct` | derivado | `PmcView`/Hermes | PMC-1; reutilizado, nunca recalculado aqui |
| `freshness`, `captured_at` | proveniência temporal | UI-4 | idade/origem da captura |
| `heuristic_level`, `heuristic_score`, `heuristic_confidence` | heurístico | `ReadinessAssessment` existente | GREEN/YELLOW/RED, média e cobertura existentes |
| `heuristic_observations`, `heuristic_signals`, `illness_alert`, `composite_low` | heurístico | `ReadinessTrace` existente | trace dos sinais já avaliados |
| `axis_states` | cobertura | modelo + produtor | um item por eixo, com `implemented`, `available` e score observado |
| `model_axis_count`, `implemented_axis_count`, `available_axis_count` | cobertura | `axis_states` | respectivamente 7 eixos do modelo, 3 eixos com produtor atual e 0..3 eixos válidos na leitura |

`HeuristicObservationView.source` usa nomes canônicos de apresentação
(`wellness.hrv`, `wellness.resting_hr`, `wellness.sleep_secs`), não chaves
cruas do provider.

## 4. Ausência e datas

- Sem snapshot: `available=False`, wellness/PMC/freshness/status são `None`;
  não se cria objeto artificial só para retornar score zero.
- Dados parciais: os campos ausentes ficam `None`; não viram zero, score neutro,
  score saudável ou diagnóstico. Um eixo implementado só está `available` quando
  o sinal atual é válido; os demais ficam fora da média e da cobertura diária.
- `target_day` não é inferido do relógio no novo caminho: o chamador injeta
  `today`. `reference_day` não é forçado a coincidir com ele. Isso torna visível
  leitura de D+1 consultada em D, sem transferir nem aplicar nada.

Essa separação é deliberada e **não corrige TEST-1**: o fixture date-fragile e
o comportamento legado continuam fora do escopo.

## 5. PMC e freshness

RDY-1 recebe o mesmo objeto `PmcView` já derivado por PMC-1. Não há segunda
fórmula de `form_pct`, EWMA, CTL, ATL ou TSB. Provenance:

```text
ctl / atl / tsb  -> provider observed
form_pct         -> Hermes derived (PMC-1)
wellness         -> provider observed, snapshot canônico
heuristic_*      -> Hermes system heuristic existente
```

Snapshot stale continua servindo dados e classificação; `freshness.status`
informa que a captura envelheceu. Staleness não bloqueia readiness, não produz
policy e não muda o valor dos sinais.

## 6. Heurística, advice e prescrição

`heuristic_level` não é fato científico nem diagnóstico. É resultado do modelo
existente de sete eixos. Hoje há produtor para HRV/RHR/sono, portanto 3/7 é a
capacidade máxima da implementação, não a cobertura da leitura do dia:
`available_axis_count` pode ser de 0 a 3. Os quatro eixos sem produtor e os
sinais ausentes no dia permanecem `None`; RDY-1 não inventa normalização nem
threshold novo.

`ReadinessView` não expõe `ReadinessAction`, reason de decisão, advice,
`reduce`, `replace`, deload, cancelamento ou alteração de plano. Ela também não
chama `readiness_decision`. O fluxo prescritivo atual (`assess_daily_readiness`,
`build`, `check --apply`) fica intacto. POL-1 é advisory paralelo e não altera
essa separação.

## 7. Offline e side effects

`get_readiness_view`:

- lê somente `training_snapshot.json` já persistido;
- não chama `client()`/provider/rede;
- não escreve plano nem snapshot;
- não altera lifecycle, completion ou freshness;
- não faz reconcile nem escreve stdout.

`tests/test_readiness_view.py` injeta `client_factory` que levanta, compara os
arquivos antes/depois e captura stdout vazio.

## 8. Guardrails

- `ui_state.py` não conhece `icu_*`, `paired_activity_id`, `IntervalsAdapter`,
  `requests` ou `provider_fields`.
- A View não chama `readiness_decision`, `assess_daily_readiness`,
  `ReadinessAction`, `mark_completed` nem `save_plan` (teste tokeniza código).
- Não há regra `form_pct <= -30`, label de risco, deload ou advice novo.

## 9. Testes

`tests/test_readiness_view.py` (16 testes): sem snapshot; wellness completo e
parcial; target/reference day explícitos; PMC presente/ausente e `form_pct`
preservado; freshness stale; GREEN/YELLOW e trace existente; prova de que
`readiness_decision` não é chamado; offline/side effects/stdout; serialização;

## 10. Critérios RDY-1 = DONE

1. `ReadinessView` explícita — sim;
2. independente de provider — sim;
3. offline/local — sim;
4. PMC/`form_pct` reutilizados — sim;
5. wellness observado sem policy nova — sim;
6. heurística distinta de observações — sim;
7. policy/prescrição ausentes — sim;
8. query side-effect free — sim;
9. datas determinísticas em testes — sim;
10. serialização estável — sim;
11. nenhuma regressão nova — sim (somente TEST-1 pré-existente).

POL-1 é policy advisory paralela, concluída sem prescrição.

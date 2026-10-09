# HR-1 — CTL Ramp Rate: métrica observada e advisory opt-in

> Dono: **repo** (`docs/HR-1-CTL-RAMP-RATE.md`). Espelho de leitura no vault.
> Escopo: HR-1. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §9).

## 1. Decisão após auditoria

O snapshot UI-4 já persiste eventos normalizados da janela de sync (default: 60
CTL quando também possui `day`. É histórico local/offline, mas **não é uma série

Por isso HR-1 usa diferença exata, sem inventar dados:

```text
ramp_rate_7d = CTL(D) - CTL(D - 7 dias)
```

Unidade: **pontos de CTL por 7 dias**. Não são watts.

Nem regressão linear, nem EWMA extra, nem interpolação foram introduzidos. CTL
continua **observado** do provider; Hermes apenas compara dois valores
observados. A janela é configurável (`window_days`, default 7), mas a definição
continua sempre diferença de dois pontos exatos.

## 2. Gaps e dados insuficientes

| condição | resultado |
|---|---|
| CTL em D e D-7 observados | `ramp_rate = CTL(D) - CTL(D-7)` |
| CTL atual ausente | `None` |
| CTL D-7 ausente | `None` |
| história vazia/parcial/gap | `None` |
| CTL numérico negativo | preservado e calculado, sem correção inventada |

Não há nearest-prior, interpolação, zero implícito ou recomputação local de
CTL. Para duplicatas do mesmo dia, a última observação na ordem do snapshot
vence, igual à semântica de `coach.real_pmc_by_day`; um `PmcView` datado é a
última observação e vence também.

## 3. Contrato de leitura

`src/ui_state.py`:

```python
derive_ctl_ramp_rate(history, target_day=..., window_days=7)
CtlRampView(
    target_day, window_days, baseline_day,
    target_ctl, baseline_ctl, ramp_rate,
    observed_days, freshness, captured_at,
)
```

`PmcView` permanece estado **pontual** (CTL/ATL/TSB/form relativo).
`CtlRampView` é tendência temporal **separada**; não misturamos os dois.

Application:

```python
app.get_ctl_ramp_view(target_day=..., window_days=7, now=...)
```

`target_day` é obrigatório; a query não consulta `date.today()` internamente.
`freshness`/`captured_at` são reutilizados do snapshot para o consumidor saber a
idade da série. Snapshot stale ainda calcula a métrica quando os dois pontos
existem: freshness informa qualidade temporal, não bloqueia a matemática.

## 4. Advisory

Não há `5`, `7` ou outro limite default de ramp rate: o backlog e a
documentação existente não sustentam um valor absoluto universal. A janela de
**7 dias** é definição temporal; não é threshold fisiológico.

`src/ctl_ramp_advisory.py` fornece policy opt-in:

```python
evaluate_ctl_ramp_advisory(ramp_rate, max_ramp_points=...)
app.get_ctl_ramp_advisory(
    target_day=..., max_ramp_points=..., window_days=7,
)
```

O limite deve ser injetado pelo consumidor/contexto e ser finito/não-negativo.
Estados:

| status | condição |
|---|---|
| `unavailable` | métrica ausente/inválida |
| `within_advisory_range` | `ramp_rate < max_ramp_points` |
| `high_ramp` | `ramp_rate >= max_ramp_points` |

É **heurística operacional/advisory**, não regra fisiológica, diagnóstico ou
prescrição. Não executa deload, reduce, replace, cancel, postpone ou mudança de
plano. `FormAdvisory` (POL-1) e `CtlRampAdvisory` coexistem sem policy composta.

## 5. Limitações explícitas

- Um delta absoluto de +6 pontos em CTL 30 não tem necessariamente o mesmo
  significado prático que +6 em CTL 100.
- HR-1 não introduz versão relativa nem normalizada por fitness.
- A métrica pode ficar indisponível em snapshots esparsos, por desenho
  conservador; uma infraestrutura de série diária observada seria evolução
  separada se essa disponibilidade se tornar problema de produto.
- Não há conclusão sobre risco ou treino a partir do resultado isolado.

## 6. Provenance e offline

```text
CTL history      -> provider observed, snapshot normalizado (UI-4)
ramp_rate        -> Hermes derived, diferença de dois pontos (HR-1)
ramp advisory    -> Hermes operational policy opt-in (HR-1)
```

Queries são locais/read-only: não chamam provider, não escrevem plano/snapshot,
stdout. Testes usam `client_factory` que levanta.

## 7. Fora do escopo

HR-2 (Pw:HR), HR-3/HR-4, série diária sintetizada, threshold default de CTL,
policy composta com form/readiness, `ReadinessAction`, `check --apply`, CLI e
qualquer prescrição automática.

## 8. Testes

`tests/test_ctl_ramp.py` (19): +5/-5/0, floats, negativos observados, gaps,

## 9. Critérios HR-1 = DONE

1. definição explícita — sim;
2. histórico local coerente — sim, com disponibilidade explícita;
3. cálculo puro — sim;
4. CTL não recalculado — sim;
5. gaps tratados sem inferência — sim;
6. View separada — `CtlRampView`;
7. advisory separado — `ctl_ramp_advisory.py`;
8. threshold não tratado como lei — sem default e §4;
9. offline — sim;
10. sem prescrição — sim;
11. sem falha nova — somente TEST-1;
12. documentação atualizada — sim.

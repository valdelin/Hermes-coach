# PMC-1 — `form_pct`: Form relativo derivado (view-only)

> Dono: **repo** (`docs/PMC-1-FORM-PCT.md`). Espelho de leitura no vault.
> Escopo: PMC-1. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §8).

## 1. O que é

**Form relativo (%) = TSB / CTL × 100**

`form_pct` é uma **representação derivada** do Hermes sobre PMC **observada**.
Ele não é uma regra fisiológica, não é limiar de deload e não tem efeito
prescritivo. Interpretar o valor e decidir sobre ele é tarefa de **policy**
(POL-1), não deste contrato.

Semântica preservada explicitamente:

| valor | significado | origem |
|---|---|---|
| `ctl` | Fitness observado | provider (UI-3) |
| `atl` | Fatigue observada | provider (UI-3) |
| `tsb` | **Form absoluto** observado (unidade de carga, não watt) | provider (UI-3) |
| `form_pct` | **Form relativo** derivado | **Hermes** (PMC-1) |

`form_pct` não vem do provider, não substitui TSB, não recalcula PMC e não
altera CTL/ATL/TSB. O Hermes faz **uma** divisão — e a política de stale/age é a
de UI-4, reaproveitada.

## 2. Localização

`src/ui_state.py` (camada de leitura/derivação):

```python
def derive_form_pct(ctl, tsb) -> Optional[float]:   # derivação pura
@dataclass(frozen=True) class PmcView:              # contrato de leitura
def build_pmc_view(metrics) -> Optional[PmcView]   # snapshot -> View
```

Por que aí e não em outro lugar:

- **não** em `IntervalsAdapter` — `form_pct` não é dado do provider;
- **não** em `provider.py` — mesma razão (é Hermiano, não do Intervals);
- **não** em `snapshot.py` — o snapshot é o cache do que foi **observado**;
  derivação pertence à derivação de leitura;
- **não** em `coach.py` — `coach` calcula PMC para o motor; `ui_state` expõe o
  que a UI lê;
- **não** na CLI — a CLI formata; o contrato é o produto.

Reuso, não duplicação: `SnapshotView` (UI-5) já era o contrato que expõe o
cache. `PmcView` **substituiu** o dict `metrics` sem tipagem — um conceito, uma
representação. Não existem `PmcSnapshot`/`PmcState`/`PmcMetrics`.

## 3. Fórmula e `None`

```python
form_pct = (tsb / ctl) * 100.0
```

Devolve `None` — **nunca 0** — quando a razão não é definida:

| condição | resultado | por quê |
|---|---|---|
| `ctl is None` | `None` | fitness não observada |
| `tsb is None` | `None` | form não observado |
| `ctl <= 0` | `None` | divisão indefinida (zero ou negativo) |
| `ctl > 0`, `tsb = 0` | `0.0` | zero é valor legítimo |
| `ctl > 0` | float | float full, sem arredondamento |

Sem clamp arbitrário e sem arredondamento interno: `CTL=3, TSB=-1` devolve
`-33.33333333333333`. Format visual (`-25.3%`) é do consumidor.

## 4. Contrato de leitura

```
ApplicationState
└── snapshot: SnapshotView | None
    └── pmc: PmcView | None
        ├── ctl:      float | None   (observed)
        ├── atl:      float | None   (observed)
        ├── tsb:      float | None   (observed)
        ├── form_pct: float | None   (derived)
        ├── tss / ftp / day          (observed, contexto)
    └── freshness: FreshnessView | None
```

O consumidor **não** recalcula `tsb / ctl`. Serialização:

```json
{"ctl": 100.0, "atl": 125.0, "tsb": -25.0, "form_pct": -25.0}
```

`to_dict()` determinístico; `None` vira `null` no JSON; nenhum objeto de
provider dentro da View.

## 5. Ausência

- Sem sync: `state.snapshot is None` → não existe `form_pct`. **Não** foi criado
  objeto artificial só para expor `form_pct=None`.
- Snapshot com eventos mas sem PMC: `state.snapshot.pmc is None`.
- A query continua **local e side-effect free**: não dispara provider.

## 6. Freshness

`form_pct` continua calculado a partir de snapshot **stale**, e a freshness
continua reportando `stale`. Valor e qualidade temporal da fonte são eixos
separados: freshness informa a idade, não bloqueia a derivação. Não foi
introduzida regra do tipo "stale ⇒ `form_pct = None`" — ela não existe no
sistema e seria policy escondida.

## 7. Guardrail

- Nenhuma policy embutida: sem `if form_pct <= -30`, sem labels
  (`NORMAL`/`CAUTION`/`HIGH_NEGATIVE_FORM`), sem deload, sem alteração de treino.
  Coberto por teste que faz grep do código de `ui_state.py`.
- `derive_form_pct` não muta argumentos nem DTOs; `build_pmc_view` copia os
  observados (teste compara o dict original antes/depois).
- `form_pct` não aparece em `IntervalsAdapter` nem em `provider.py` (teste).

## 8. Critérios PMC-1 = DONE

| # | critério | evidência |
|---|---|---|
| 1 | `form_pct` no contrato de leitura | `PmcView.form_pct` em `SnapshotView` |
| 2 | fórmula correta | `tests/test_pmc_form.py::FormulaTest` |
| 3 | `ctl <= 0` → `None` | `UndefinedTest` |
| 4 | dados ausentes → `None` | `UndefinedTest` |
| 5 | cálculo local | `derive_form_pct` puro, sem I/O |
| 6 | não chama provider | `client_factory` que levanta |
| 7 | CTL/ATL/TSB não recalculados | `DerivationIsPureTest` |
| 8 | serialization inclui o valor | `SerializationTest` |
| 9 | casos principais e limites cobertos | 30 testes |
| 10 | nenhuma policy embutida | `GuardrailTest` |
| 11 | nenhuma regressão nova | suíte: 1 falha pré-existente, 0 novas |

## 9. Fora do escopo

POL-1 (advisory `form_pct <= -30%`), RDY-1 (Readiness View), HR-1..HR-4, UI
gráfica, HTTP/API. A CLI **não** foi alterada: `cmd_info`/`cmd_model` leem PMC
ao vivo do provider e imprimir `form_pct` lá duplicaria o contrato em vez de
demonstrá-lo — o requisito aqui é o contrato `Application`/View.

## 10. Testes

`tests/test_pmc_form.py` (30): fórmula (6 casos principais), `None` (CTL 0,
CTL ausente, TSB ausente, ambos, CTL negativo, valor não numérico), precisão
(sem arredondamento; formatação é do consumidor), pureza (não muta; observados
preservados; sem PMC → sem objeto), `ApplicationState` (leitura local, provider
independence, snapshot stale ainda calcula, fresh, ausência, snapshot sem PMC),
serialização (inclui `form_pct`, `null`, determinístico) e guardrails (sem
policy, fora do adapter/provider, sem I/O, TSB preservado).

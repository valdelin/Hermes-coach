# POL-1 — Form advisory configurável, advisory-only

> Dono: **repo** (`docs/POL-1-FORM-ADVISORY.md`). Espelho de leitura no vault.
> Escopo: POL-1. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §8).

## 1. Objetivo

POL-1 interpreta `form_pct` já derivado por PMC-1 e devolve um **advisory**.
Não recalcula PMC, não altera `ReadinessView`, não aconselha uma ação concreta e
nunca modifica um treino.

```text
PmcView.form_pct / ReadinessView.pmc.form_pct
                    ↓
evaluate_form_advisory(form_pct, threshold)
                    ↓
FormAdvisory
                    ↓
CLI / UI futura decide como apresentar
```

## 2. Localização e API

`src/form_advisory.py` é módulo de policy isolado:

```python
evaluate_form_advisory(form_pct, threshold=-30.0) -> FormAdvisory
```

`Application.get_form_advisory(threshold=..., now=...)` é o adapter local: lê
o `PmcView` persistido e passa somente `pmc.form_pct` à policy. O módulo de
policy não conhece provider, snapshot, CTL/ATL/TSB, readiness, plano ou CLI.

## 3. Threshold

`DEFAULT_FORM_ADVISORY_THRESHOLD = -30.0` vive **uma vez** em
`form_advisory.py`. É injetável por argumento; a policy não lê `.env`.

`-30%` é um **default operacional/advisory**, não uma verdade fisiológica
universal, critério diagnóstico ou regra obrigatória de deload. Para evitar
configuração semanticamente invertida, o threshold deve ser número finito e
estritamente negativo. `None`, string, boolean, `NaN`, infinito, zero ou
positivo levantam `ValueError` em vez de produzir resultado absurdo silencioso.

## 4. Estados

| status | condição | significado |
|---|---|---|
| `unavailable` | `form_pct` ausente, não numérico ou não finito | advisory não avaliado; não é normal nem alerta |
| `normal` | `form_pct > threshold` | limiar advisory não atingido |
| `high_negative_form` | `form_pct <= threshold` | limiar advisory configurado atingido |

A igualdade entra no advisory: `-30.0 <= -30.0`.

`FormAdvisory` é frozen e serializa `status`, `form_pct`, `threshold` e
`message`. A mensagem é neutra: "Form relativo atingiu o limiar advisory
configurado." Não diz para reduzir, trocar, cancelar ou fazer deload.

## 5. Separação de camadas

| camada | dono | exemplo |
|---|---|---|
| observado | provider/snapshot | CTL, ATL, TSB |
| derivado | PMC-1 | `form_pct = TSB / CTL × 100` |
| heurística de readiness | RDY-1 | `heuristic_level = green` |
| policy advisory | POL-1 | `high_negative_form` |
| advice/prescrição | fora de escopo | reduzir/trocar/deload |

Por isso `ReadinessView.heuristic_level == green` e
`FormAdvisory.status == high_negative_form` podem coexistir. POL-1 não resolve
o conflito: uma policy composta ou apresentação futura decide como mostrar os

## 6. Offline, freshness e side effects

- funciona sem provider/rede, sobre snapshot local;
- sem PMC/form → `unavailable`, nunca `normal`;
- snapshot stale ainda produz advisory; freshness continua disponível no
  `ReadinessView` para o consumidor comunicar a idade;
- não escreve `plan.json`/`training_snapshot.json`, não muda lifecycle,
  completion ou freshness, não reconcilia e não escreve stdout.

## 7. Fora do escopo

Não há `ReadinessAction`, `REDUCE`, `REPLACE`, deload, cancelamento, push,
reconcile, `check --apply`, alteração de `readiness_decision`, regra HR-1..4
nem novas faixas (-10/-20/-40). A única regra é binária + indisponível.

## 8. Critérios POL-1 = DONE

1. policy explícita — `form_advisory.py`;
2. threshold configurável — argumento injetável;
3. default `-30%` documentado como advisory — §3;
4. `form_pct` reutilizado, não recalculado — guardrail de arquitetura;
5. ausência → `unavailable` — §4;
6. read-only — §6;
7. sem ação prescritiva — §7;
8. View sem threshold — teste;
9. offline — teste com `client_factory` que levanta;
10. boundary/exato/custom cobertos — 15 testes;
11. heuristic vs prescription documentados — §5;
12. nenhuma regressão nova — somente TEST-1 pré-existente.

## 9. Testes

`tests/test_form_advisory.py` (15): regra base, igualdade, custom threshold,
validação, valores ausentes/não finitos, mensagem, serialização, integração
offline com `Application`, snapshot stale, coexistência com readiness GREEN,
side effects/stdout e guardrails de import/cálculo/prescrição.

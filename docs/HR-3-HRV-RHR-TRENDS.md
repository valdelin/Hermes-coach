# HR-3 — HRV / RHR observados, baseline individual e tendência

> Dono: **repo** (`docs/HR-3-HRV-RHR-TRENDS.md`). Espelho de leitura no vault.
> Escopo: HR-3. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **DONE** (ver §9). `FCR` resolvido como alias PT-BR de RHR (§8).
> Limitação aberta: a unidade de `hrv` segue não documentada (§3) — não
> inferida, e por isso `hrv` e `hrv_sdnn` não são equivalentes científicos.

## 1. Objetivo

Camada explícita, **local e offline**, para observar e resumir sinais de HRV e
RHR: valor observado, baseline individual, delta absoluto, delta percentual e
proveniência. É leitura de dados, não decisão.

Termina em `observado → baseline → tendência → view descritiva`. Não avança
para policy nem prescrição (§3).

## 2. O que já existia (auditoria)

| onde | o quê | relação com HR-3 |
|---|---|---|
| `src/readiness.py::_low_hrv` | heurística `hrv_low` | **não reimplementada** pela View; baseline corrigido em PROMPT 28 (§11) |
| `src/readiness.py:99` `_rising_rhr` | heurística `rhr_rising` | **preservada intacta** |
| `src/readiness_assessment.py` | score/level/confiança | **preservado** |
| `src/ui_state.py` `WellnessView` | último wellness, campos pontuais | base observada, sem tendência |
| `src/ui_state.py` `ReadinessView` | observações + heurística | **não embutida** em HR-3 |
| `src/provider_fields.py:45-47` | `resting_hr`, `hrv`, `hrv_sdnn` | campos canônicos usados |

Os thresholds existentes (`RHR_RISE_BPM = 3.0`, `HRV_LOW_RATIO = 0.80`) são
**heurística do sistema**, não verdade fisiológica. HR-3 não os renomeia, não
os move e não os altera.

## 3. Campos observados e unidades

| campo canônico | origem (`provider_fields`) | unidade | status |
|---|---|---|---|
| `resting_hr` | `restingHR` | bpm | observado |
| `hrv` | `hrv` | **desconhecida** — o provider não declara | observado |
| `hrv_sdnn` | `hrvSDNN` | ms por convenção do campo | observado, **fallback** |

A unidade de `hrv` **não está documentada em lugar nenhum do repositório**. Não
foi inventada: `HeartRateMetricTrend.unit` fica `None` para HRV. Confirmar com
o provider antes de comparar `hrv` com `hrv_sdnn` — ver §6.

## 4. Regras de dado

**Missing ≠ zero.** Ausência é sempre `None`. Zero observado é **inválido** em
HRV e RHR: FC de repouso 0 bpm é leitura quebrada de sensor, não observação.

Validação (`_hr_metric`) rejeita: `bool` (`True` não é 1.0 bpm), string não
numérica, `NaN`, `±inf`, zero. Diferente de `_f` do próprio `ui_state.py`, que
aceita `bool` e propaga `NaN` — por isso `_hr_metric` é separado e não reutiliza
`_f`.

Nada é interpolado. Dia sem valor válido simplesmente não existe na série.

## 5. Baseline e janela

`baseline = média dos valores observados na janela`, janela **inclusiva**
terminando em `reference_day`, default `DEFAULT_HR_TREND_WINDOW_DAYS = 7`.

O default vem do projeto: é a mesma janela usada por `_rising_rhr` e `_low_hrv`
(`days=7`). Nenhum corte fisiológico novo foi introduzido.

Não existe "mínimo de amostras" mínimo para calcular: a média de 1 observação é
matematicamente válida, e `sample_count` fica exposto para o consumidor decidir
se aceita uma base fraca. A View não inventa corte — reportar §10.

`reference_day` é o **último dia com wellness de qualquer tipo**, não o
`target_day` e não o último dia de uma série específica. Wellness de ontem
ainda produz leitura, com o dia explícito.

## 6. HRV: `hrv` e `hrv_sdnn` não se misturam

`hrv` e `hrv_sdnn` são métricas diferentes (o nome do segundo indica SDNN; o
primeiro não declara método — tipicamente RMSSD, mas isso **não está no
código**). Combiná-las produziria uma série sem unidade.

Regra implementada:

1. usa `hrv` se existe **qualquer** observação na janela;
2. só cai para `hrv_sdnn` quando `hrv` está completamente ausente;
3. registra a escolha em `hrv_field`, visível na view.

Um dia com `hrv` e outro com `hrv_sdnn` **não** viram uma série só: o dia com
só `hrv_sdnn` fica de fora quando `hrv` existe.

## 7. Freshness

Reportado, nunca bloqueante. Dado `stale` **continua produzindo** baseline e
delta; `freshness.status` permanece visível ao consumidor. Proveniência é
política do snapshot, não da View.

## 8. `FCR` — alias de RHR, não um terceiro sinal

**Decisão do responsável pelo backlog (PROMPT 29):**

```
FCR = frequência cardíaca de repouso = RHR (Resting Heart Rate)
```

`FCR` é o termo **português** de RHR. Não é *heart-rate recovery*. Não é uma
métrica fisiológica nova.

Por isso a View **não tem campo `fcr`**. `HeartRateTrendView` expõe dois sinais
reais — `hrv` e `rhr` — e o valor que "FCR" nomeia é `rhr.current`. Dar um campo
próprio repetiria o mesmo número sob dois nomes, que é duplicação semântica, não
modelagem.

O código fala em `rhr` / `resting_hr` (inglês, igual ao resto dos campos do
provider). A equivalência é terminológica e vive na documentação: `README`,
`GLOSSARIO.md` (na entrada `RHR`), `ROADMAP.md` e este documento.

**O que foi removido:** o campo provisório `fcr_heart_rate_recovery` e o status
`HR_TREND_UNSUPPORTED_FIELD`, que existiam só para marcar `FCR` como não
implementado. Nenhum consumidor real além da própria View — auditado antes da
remoção (`grep` por `fcr_heart_rate_recovery` e por `to_payload`).

**Heart-rate recovery está fora de escopo.** Recuperação de FC em 1 min, slope
pós-exercício, segmentação de cooldown e análise de atividade são conceitos
distintos, que exigiriam metodologia e dados que o boundary não expõe. Não há
backlog para isso, e a View não os infere de uma série de atividade.

## 9. Status

**DONE.** HRV, RHR, baseline, delta, proveniência, freshness e a view
local/offline estão completos e testados. A única pendência do item — o
significado de `FCR` — foi resolvida como alias de RHR (§8). O bug de baseline
contaminado em `_low_hrv` foi corrigido à parte (§11).

## 10. Limitações

1. **Unidade de `hrv` desconhecida.** Bloqueia comparação numérica entre
   `hrv` e `hrv_sdnn`. Requer confirmação do provider.
2. **Zero rejeitado como valor observado.** Se algum provider legítimo reportar
   0, a regra ignora. Para FC de repouso isso parece correto, mas não é
   verificado contra o provider real.
3. **Janela de 7 dias é convenção do código**, não protocolo de coleta.
   O `ROTEIRO-TREINADOR.md:1.2.5` pergunta ao treinador qual janela ele usa —
   essa resposta ainda não existe.
4. **Sem número mínimo de amostras.** `sample_count` é informativo.
5. **RHR/HRV não são observados na mesma hora garantida.** O provider entrega
   o que entregou; a View não registra horário de coleta. O ROTEIRO pergunta
   isso (§1.2.5, pergunta 6) e continua sem resposta.
6. **Baseline da View usa janela inclusiva; `_low_hrv` do readiness usa só os
   valores anteriores ao corrente** — ver §11. Intencionalmente diferentes:
   a View exibe observação (o valor corrente faz parte do contexto), o
   readiness compara o corrente contra um baseline que não o contém.

## 11. Defeito corrigido: baseline de `_low_hrv` era contaminado

`src/readiness.py::_low_hrv` calculava a base **incluindo o último valor na
própria média**:

```python
last_hrv = _last("hrv", rows) or _last("hrvSDNN", rows)
base = _avg("hrv", rows, days=days) or _avg("hrvSDNN", rows, days=days)
```

Com série HRV `[60, 59, 58, 57, 56, 45, 44]`, a média de 7 dias vira `54.14`, e
`44 < 54.14 × 0.80` é falso — uma queda de 27% **não disparava** `hrv_low`. O
próprio dado baixava a média, erguia o threshold e mascarava o sinal.

**Correção (PROMPT 28, bug computacional — não é threshold fisiológico):**
`rows[:-1]` nas duas médias, alinhando com `_rising_rhr`, que já documentava
"para não contaminar a base". `HRV_LOW_RATIO = 0.80` e a janela de 7 dias
permanecem; muda apenas o conjunto de amostras do baseline.

Com a mesma série, a base passa a `55.83` (média de `[60,59,58,57,56]`),
threshold `44.67`, e `44 < 44.67` é **true**. Regressão coberta em
`tests/test_readiness.py::LowHrvBaselineContaminationTest` (15 testes), que
inclui o caso normal (base 58, current 55 → sem sinal), a igualdade (`<`
preservado: current == threshold não dispara) e a propagação para
`signals`, `_reason`, `suggest_swap` e o eixo `hrv_score`.

**Propagação observada:** `hrv_low` agora dispara onde antes não disparava, e
isso se propaga para `Readiness.reason`, `suggest_swap` e
`ReadinessAssessment.hrv_score` (que passa a `FLAGGED_SCORE`), puxando
`overall_readiness` para baixo. `_illness` **não** muda: tem lógica própria
(`hrv_last < hrv_prev`), sem baseline. `composite_low` **não** muda: deriva de
`readiness_low`, não de `hrv_low`.

Nota adicional (não corrigida, fora de escopo): `_low_hrv` usa `or` entre
`_last("hrv")` e `_last("hrvSDNN")`, combinando campos de métricas diferentes
numa mesma comparação. A regra de não-mistura documentada em §6 é da View; o
readiness
ainda não a segue.

## 12. Onde está implementado

| item | arquivo |
|---|---|
| view e derivadas puras | `src/ui_state.py` (`HeartRateTrendView`, `HeartRateMetricTrend`, `_hr_metric`, `_hr_series`, `derive_hr_baseline`, `derive_hr_delta`, `derive_hr_delta_pct`, `build_heart_rate_trend_view`) |
| seam local/offline | `src/application.py` (`get_heart_rate_trend_view`) |
| testes | `tests/test_hr3_hr_trends.py` (47 testes) |

Nenhum outro módulo foi alterado. `readiness.py`, `readiness_assessment.py`,
`provider.py`, `snapshot.py` e `intervals_adapter.py` intactos.

## 13. O que HR-3 deliberadamente não faz

- nenhum advisory novo (HRV, RHR, recuperação);
- nenhuma policy, `ReadinessAction` ou prescrição;
- nenhum auto-deload;
- nenhum threshold fisiológico universal novo;
- nenhuma integração com `FormAdvisory` (POL-1) ou `PwHrDecouplingView`
  (HR-2);
- nenhuma chamada a provider, sync ou escrita.
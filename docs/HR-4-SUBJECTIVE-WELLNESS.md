# HR-4 — Wellness observado: sono, stress e readiness do provider

> Dono: **repo** (`docs/HR-4-SUBJECTIVE-WELLNESS.md`). Espelho de leitura no vault.
> Escopo: HR-4. `docs/ROADMAP.md` é a fonte de prioridade.
> Status: **PARTIAL** (ver §9). Três conceitos do workstream não existem no
> provider; a lacuna é o resultado, não um campo faltando.

## 1. O que este documento é

Uma camada de **leitura** para os sinais de wellness que o Intervals.icu
realmente entrega. Ela para em:

```
observado  ->  contexto (baseline / delta)
```

e nunca em:

```
score composto  ->  decisão  ->  prescrição
```

Não há `ReadinessAction`, nem deload, nem troca de treino, nem score global.
Os limiares que já existiam continuam em `readiness.py` com o mesmo
significado; esta View expõe os valores que eles leem.

## 2. Auditoria do inventário (§3 do prompt)

O inventário foi feito antes de qualquer edição, em `src/`, `tests/` e `docs/`.
"Campo real" significa chave que existe no boundary ou no cache local.

| conceito | campo real (canônico) | origem | unidade / escala | disponível | usado hoje |
|---|---|---|---|---|---|
| sleep duration | `sleep_secs` ← `sleepSecs` | `/wellness` | **segundos**; escala dimensional | sim | `readiness._short_sleep` |
| sleep score | `sleep_score` ← `sleepScore` | `/wellness` | pontos; **escala `unknown`** | sim | exposto em `WellnessView`, não usado |
| stress | `stress` | `/wellness` | **unidade `unknown`, escala `unknown`** | sim | exposto, nunca usado |
| soreness | — | — | — | **não** | não |
| motivation | — | — | — | **não** | não |
| fatigue | — | — | — | **não** | `subjective_fatigue_score` é sempre `None` |
| readiness | `readiness` | `/wellness` | composto **do provider**; escala `unknown` | sim | sinal `composite_low` |

Achados da auditoria que mudaram a implementação:

- `soreness`, `motivation` e `fatigue` **não existem** em `src/` — nem no
  boundary, nem no snapshot, nem em alias. `mood` também não.
- `sleep_score` e `readiness` estão na tabela de aliases
  (`provider_fields._ALIASES`) mas **não** no dict normalizado de
  `_wellness_snapshot`. Eles chegam ao `WellnessSnapshot` pelo payload bruto e
  persistem no snapshot por `canonical()`. Verificado por teste; **não exigiu
  mudança no adapter** (§40).
- `subjective_fatigue_score` existe como eixo do modelo de readiness, mas o
  comentário em `readiness.py:300` já registra que RPE é digitado no treino
  realizado e não chega em `/wellness`. Ele permanece `None`.

## 3. Nome: por que não `SubjectiveWellnessView`

O workstream se chama "subjective wellness", mas o contrato dentro dele se chama
`ObservedWellnessView`. "Subjetivo" seria factualmente errado: `sleep_secs`,
`sleep_score`, `stress` e `readiness` vêm do provider/wearable, não de
auto-relato. Os itens genuinamente subjetivos — soreness, motivation, fatigue —
são exatamente os que o provider **não** expõe (§10).

`ObservedWellnessView` diz o que há dentro: valor observado do provider mais
contexto derivado. `ui_state.py` mantém o mesmo padrão de HR-3
(`HeartRateTrendView`).

## 4. Sono: três coisas, não uma

Duração, score e qualidade **não** são intercambiáveis e a View não os troca:

| | campo | unidade | o que é |
|---|---|---|---|
| duração | `sleep_secs` | segundos | tempo total de sono observado |
| score | `sleep_score` | pontos | escore do provider |

A unidade da duração foi confirmada, não inferida:

1. a chave do provider é `sleepSecs`;
2. `readiness._short_sleep` divide por `3600` e compara com
   `SLEEP_SHORT_HOURS`;
3. a documentação do fórum do Intervals.icu afirma que números de sono enviados
   ao Intervals são **em segundos**.

A View não converte score em horas nem horas em score: são campos separados, com
`unit` distinto (`seconds` vs `points`), e cada um pode estar ausente enquanto o
outro existe.

## 5. Stress, soreness e motivation: o que se pode e o que não se pode dizer

**Nenhuma** métrica de HR-4 carrega direção. O contrato do repositório não
documenta se stress alto é bom ou ruim, e não há fonte primária que fixe a
escala — a documentação pública do Intervals.icu acessível não descreve o campo
`stress`. Portanto:

- `stress` expõe o valor observado, `unit="unknown"` e `scale="unknown"`;
- não é chamado de "stress fisiológico" em lugar nenhum;
- não existe `direction` no dataclass, porque um campo sempre `None` seria
  ruído — a ausência de direção está escrita, não codificada.

`soreness` e `motivation` não têm origem: viram `unsupported_field`, com o
contrato declarando "sem chave em `/wellness`". Não se procura campo parecido
(`muscle_soreness`, `motivation_score`) nem se inventa alias. Um `soreness` que
apareça no registro cru **não** vira sinal observado.

## 6. Schema da View

```python
@dataclass(frozen=True)
class WellnessMetricView:
    concept: str            # "sleep_duration" | "stress" | "soreness" | ...
    field: Optional[str]    # chave canônica; None se unsupported_field
    status: str             # observed | missing_current | unsupported_field
    source: str             # de onde vem, incluindo a chave do provider
    current: Optional[float]
    baseline: Optional[float]
    delta: Optional[float]
    delta_pct: Optional[float]
    sample_count: int
    unit: Optional[str]
    scale: Optional[str]

@dataclass(frozen=True)
class ObservedWellnessView:
    target_day: str
    window_days: int
    reference_day: Optional[str]
    sleep_duration: Optional[WellnessMetricView]
    sleep_score: Optional[WellnessMetricView]
    stress: Optional[WellnessMetricView]
    soreness: Optional[WellnessMetricView]
    motivation: Optional[WellnessMetricView]
    fatigue: Optional[WellnessMetricView]
    provider_readiness: Optional[WellnessMetricView]
    freshness: Optional[FreshnessView]
    captured_at: Optional[str]
    provider: Optional[str]
```

Os sete conceitos estão sempre presentes. Quem não tem chave volta
`unsupported_field`; quem tem chave mas não tem valor no dia de referência volta
`missing_current`. Omitir o conceito seria esconder a lacuna.

## 7. Baseline: onde é defensável e onde não é

| métrica | baseline | porquê |
|---|---|---|
| `sleep_duration` | sim | série real, unidade estável (segundos), média não exige normalização |
| `sleep_score` | sim | idem, dentro da mesma escala do provider |
| `stress` | sim | a média é a média da mesma grandeza, mesmo com escala `unknown`; interpretar continua fora |
| `provider_readiness` | **não** | é um composto cujo cálculo interno é do provider e não é contrato estável: uma média entre dias pode misturar versões diferentes do score |
| `soreness` / `motivation` / `fatigue` | n/a | não há dado |

`baseline` é a média das observações numa janela **inclusiva** de
`window_days` terminando em `reference_day`. O default
(`DEFAULT_WELLNESS_WINDOW_DAYS = 7`) é o default técnico já usado por
`DEFAULT_HR_TREND_WINDOW_DAYS` e por `readiness._low_hrv`; HR-4 não introduz
janela fisiológica nova.

### `delta` exige duas observações

Com uma única observação, a média da janela **é** o próprio `current`, então
`delta = 0.0` e `delta_pct = 0.0` seriam tautologias: a View afirmaria "sem
mudança" sem mudança observável. Por isso `delta`/`delta_pct` ficam `None` quando
`sample_count < 2`. `baseline` continua exposto, com `sample_count` ao lado — o
que não se emite é a **afirmação de tendência**, não o dado.

`delta_pct` também é `None` quando `baseline == 0`: divisão por zero não é
feita e o sinal não vira 0%.

## 8. Missing, inválidos e freshness

- **Ausência é `None`.** Nunca `0`, nunca string vazia. Um conceito com chave e
  sem valor no dia é `missing_current`, não zero.
- **Rejeitados:** `bool` (`True` não é 1.0), `NaN`, `inf`, `-inf`, string não
  numérica, string vazia, e **negativo** — nenhuma grandeza de wellness aqui é
  negativa, então negativo é leitura quebrada.
- **Zero é aceito** em todos os campos de HR-4, decisão registrada caso a caso:
  `sleep_secs = 0` é semanticamente possível (dia sem sono registrado) e a View
  não consegue distinguir isso de sync falho; para os demais a escala não é
  contrato documentado, então o range 0..N não pode ser assumido. HR-3 rejeita
  zero em HRV/RHR porque ali o zero e fisiologicamente impossivel — critérios
  diferentes porque os campos são diferentes.
- **Freshness é provenance, não filtro.** Dado stale continua expondo `current`,
  `baseline` e `sample_count`, e `freshness` permanece visível na View.

## 9. Relação com readiness (e por que readiness não mudou)

`readiness.py` continua sendo o dono da leitura do wellness bruto e dos limiares.
HR-4 **não** duplica nenhum threshold:

- `SLEEP_SHORT_HOURS = 6.0`, `SLEEP_BELOW_AVG_HOURS = 2.0`,
  `READINESS_LOW = 60`, `HRV_LOW_RATIO = 0.80`, `RHR_RISE_BPM = 3.0` — intocados.
- `composite_low` continua lendo `readiness` do provider como sinal separado,
  pelo mesmo limiar, sem virar eixo.
- A View expõe `readiness` do provider como **`provider_readiness`**, em campo
  próprio, para não se confundir com um `ReadinessView` do Hermes. `ReadinessView`
  continua sendo o lugar de `GREEN`/`YELLOW`/`RED`, score, confidence e sinais.
- Dos sete eixos do `ReadinessAssessment`, só HRV, RHR e duração de sono têm
  produtor hoje. Esse é o limite de implementação (3/7), distinto da
  disponibilidade diária: HRV/RHR/sono ausentes no registro atual permanecem
  `None`, não recebem score saudável e não entram na média.

`tests/test_hr4_subjective_wellness.py::ReadinessUnchangedTest` fixa o resultado
esperado (`YELLOW`, `sleep_short`, `readiness_low`, `composite_low`) e prova que
rodar HR-4 antes não muda nada.

## 10. Limitações

1. **Três conceitos não existem.** `soreness`, `motivation` e `fatigue` não têm
   chave no provider. HR-4 entrega a lacuna, não um campo.
2. **`stress` é opaco.** Valor observado, sem unidade e sem escala. Não é
   interpretável dentro do Hermes, e a View não finge que é.
3. **`sleep_score` tem escala `unknown`.** Só o valor bruto; nenhum corte é
   aplicado.
4. **Provider readiness não tem baseline**, por ser composto de versão não
   estável.
5. **Nenhuma direção documentada** para nenhum sinal de HR-4.
6. **`delta` exige n ≥ 2**, então o primeiro dia de sync não produz tendência.

## 11. Pendências de contrato semântico

HR-4 está **PARTIAL** por decisão pendente, não por autorização para preencher
campos por aproximação. A sequência é obrigatória:

```text
1. treinador decide se quer usar o sinal e para quê
2. provider é pesquisado somente para os sinais aprovados
3. contrato (nome, tipo, unidade, escala, direção, nullable e origem) é registrado
4. só então uma tarefa separada pode implementar leitura/policy
```

### 11.1 Matriz de decisão — aguardando entrevista

Nenhuma célula de decisão abaixo foi preenchida por inferência. `confirmed`
significa apenas o contrato que já é verificável no código; não significa que o
treinador quer usar o sinal.

| sinal | treinador usa? | tipo/origem atual | escala/direção | baseline/trend? | nível 0–5 | provider | evidência | status |
|---|---|---|---|---|---|---|---|---|
| sleep duration | pendente | observado: `sleepSecs` | segundos; direção não interpretada | disponível; decisão de uso pendente | pendente | campo confirmado | não para exibir; incerto para decisão quantitativa | `confirmed` |
| sleep score | pendente | observado: `sleepScore` | `unknown` / direção desconhecida | disponível; decisão de uso pendente | pendente | campo confirmado | incerto | `unknown` |
| stress | pendente | observado: `stress` | unidade, escala e direção `unknown` | disponível; interpretação pendente | pendente | campo confirmado | incerto | `research pending` |
| soreness | pendente | subjetivo desejável ou não: pendente | pendente | pendente | pendente | nenhuma chave confirmada | sim se virar decisão quantitativa | `provider unsupported` |
| motivation | pendente | subjetivo desejável ou não: pendente | pendente | pendente | pendente | nenhuma chave confirmada | sim se virar decisão quantitativa | `provider unsupported` |
| fatigue | pendente | conceito independente ou duplicado: pendente | pendente | pendente | pendente | nenhuma chave confirmada | sim se virar decisão quantitativa | `provider unsupported` |
| provider readiness | pendente | observado: composto proprietário | `unknown` / direção desconhecida | baseline não exposto por design | pendente | campo confirmado | incerto | `unknown` |

`not used` só pode aparecer depois de decisão explícita do treinador. Se ele
optar por não usar, a ausência deixa de bloquear HR-4; se optar por usar e o
provider continuar sem campo/contrato, registra-se dependência futura de
source/provider. Assim, HR-4 poderá ser **DONE** quando cada sinal desejado tiver
contrato implementável ou decisão explícita `not used`/`provider unsupported` —
não quando todos os campos imagináveis existirem.

### 11.2 Protocolo de entrevista

Para cada sinal, capturar separadamente: uso pelo treinador, interpretação e
contexto, observado/subjetivo, escala, direção, fonte, frequência de coleta,
missing/zero, baseline, trend, nível de uso e necessidade de evidência. Perguntar
primeiro **“como você decide?”**; só depois **“usa algum limite numérico?”** e,
se houver, se é fixo, individual, literatura ou experiência. Threshold novo
presume validação bibliográfica **SIM** até haver fonte verificável.

Os cenários de conflito da entrevista são insumo para revisão humana, não regras
pré-autorizadas: sleep ruim + motivation alta; stress alto + HRV normal;
soreness alta + provider readiness boa; fatigue alta + RHR normal; sleep score
alto + duração curta. HRV/RHR ficam fora desta decisão: HR-3 já está DONE.

### 11.3 Pesquisa de provider depois da decisão

Somente para um sinal que o treinador aprovar, investigar nesta ordem: API
docs/OpenAPI oficiais, documentação oficial, fórum/maintainer oficial e, se isso
for insuficiente, fixture real sanitizada. Confirmar campo, tipo, unidade, escala,
direção, nullable e origem. JSON bruto não vira contrato; nomes como
`muscle_soreness`, `motivation` ou `fatigue` não serão normalizados sem esses
dados. Fixture sanitizada remove athlete/activity ids, tokens, nomes e timestamps
sensíveis, preservando apenas a estrutura necessária.

## 12. Onde ficar

| | |
|---|---|
| Contrato | `src/ui_state.py` (`WellnessMetricSpec`, `WellnessMetricView`, `ObservedWellnessView`, `build_observed_wellness_view`) |
| Seam | `src/application.py::Application.get_observed_wellness_view` |
| Testes | `tests/test_hr4_subjective_wellness.py` (71) |

A View é local e offline: lê o snapshot em disco, não chama provider, não
sincroniza, não escreve e não imprime. `today` e `window_days` são explícitos —
nenhum `date.today()` escondido.

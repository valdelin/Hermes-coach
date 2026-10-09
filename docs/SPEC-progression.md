# SPEC — PROG-1: Contrato de progressão semanal (ProgressionEvidence → ProgressionDecision)

Status: **contract/documentation DONE** — implementação ainda **NÃO iniciada** (2026-10-08).
Escopo: formalizar o contrato de **prog-ressão semanal** do Hermes: evidência, decisão,
ação, alvo, razões, precedência e determinismo. **Não** implementa código, não altera
prescrição e não cria threshold novo. A implementação é um release futuro, em separado.

Rastreabilidade: trilha PROG-1..PROG-6 em `docs/ROADMAP.md`; gates do treinador (Q1-Q4) em
`docs/ROTEIRO-TREINADOR.md` §1.8 e no formulário derivado
(`docs/ROTEIRO-TREINADOR-TALLY.md` §12.2, IDs `PROG_Q1`–`PROG_Q4`).
Problema endereçado: auditoria PROMPT 67 confirmou que **não existe** política de
progressão semanal produtiva — o plano coerencia por budget/TSS/focus
(`src/plan.py`), `src/progression.py` e `src/training_decision.py` são órfãos, e as
evidências de execução/adesão/prontidão/fase já existem mas não alimentam nenhuma
decisão explícita de progressão.

---

## 1. Escopo

Formaliza:

- `ProgressionEvidence` (entrada);
- `ProgressionDecision` (saída explicável/read-only);
- `ProgressionAction` (PROGRESS / MAINTAIN / RECOVER / REGRESS / TAPER / INSUFFICIENT_DATA);
- `ProgressionTarget` (VOLUME / INTERVAL_DURATION / REPETITIONS / LONG_RIDE_DURATION /
  FREQUENCY / INTENSITY / NOTHING);
- `ProgressionReason` (conjunto mínimo inicial);
- hierarquia de precedência;
- comportamentos de missing data;
- determinismo;
- boundary `Application`/domínio;
- relação futura com `PrescriptionProgression`.

Fora de escopo: `src/` e `tests/` (não alterar), thresholds numéricos, mutação de plano,
publicação no provider.

## 2. Arquitetura oficial

```
Application
  ├─ reúne Views/estado observado (WorkoutExecutionView, adherence, readiness, phase, ramp…)
  └─ monta ──▶ ProgressionEvidence

ProgressionPolicy        função pura, determinística (sem I/O, sem dt.now, sem provider)
  └─ avalia ──▶ ProgressionDecision   resultado explicável, read-only (nunca mutação)

PrescriptionProgression  use-case separado, FUTURO (mutação de prescrição; nunca junto)
```

- **Nenhuma mutation dentro de `ProgressionPolicy`.** A policy recebe evidência e
  devolve uma decisão; quem escreve plano é outro use-case, posterior e separado.
- `ProgressionDecision` é **View/Policy output** — pode ser impressa no relatório
  diário/semanal ("MAINTAIN — baixa adesão + sessão-chave incompleta"), nunca aplicada
  dentro desta camada.

## 3. ProgressionAction

Enum de seis ações, mutuamente exclusivas por decisão, cada uma com definição
inambígua (seções 4-9). Uma decisão tem exatamente **uma** action, um `target`
(mesmo que NOTHING) e um conjunto de `reasons`.

## 4. PROGRESS

**Significa:** evidência suficiente de tolerância/execução adequada **e** nenhum
blocker superior **e** contexto permite aumento de estímulo específico.

**Não significa:** `+X%` automático; aumentar intensidade automaticamente; escalar
múltiplas dimensões na mesma janela (ver §25).

Aumentar o estímulo é **gradual** e em **uma** dimensão principal por janela,
escolhida pelo contrato de `ProgressionTarget` (§10-11) e pela resposta de Q3 (§37).

## 5. MAINTAIN

**Significa:** consolidar o nível atual — repetir a carga da janela, sem aumento de
estímulo.

Casos típicos:
- sinais mistos (ex.: boa adesão coexistindo com prontidão degradada);
- adesão adequada, mas recuperação não consolidada;
- missing relevante que impede justificar aumento;
- nenhuma justificativa suficiente para produtivos.

MAINTAIN é um estado **ativo** (repetir/consolidar), não "não decidir".

## 6. RECOVER

**Significa:** reduzir estresse deliberadamente para favorecer recuperação.

**Não significa:** diagnóstico médico; equivalência automática com readiness RED
(ver §21: readiness é contexto, não soberana); deload universal de toda janela.

## 7. REGRESS

**Significa:** reduzir explicitamente **uma** dimensão porque o nível atual mostrou-se
**não factível/tolerável** (sessões falhando de forma consistente, execução cronicamente
abaixo do prescrito).

**Distinguir de RECOVER:** REGRESS reage a **intolerância observada** (execução);
RECOVER responde a **contexto de recuperação** (carga/fadiga/illness/readiness).
A razão das duas não se mistura: REGRESS usa `INCOMPLETE_WORKOUTS`/`LOW_ADHERENCE`;
RECOVER usa `RECOVERY_CONTEXT`/`ILLNESS_SIGNAL`/`READINESS_RED`.

## 8. TAPER

**Significa:** redução deliberada relacionada a competição/fase.

Possui **precedência** sobre a progressão normal quando o contexto de prova assim
determinar (§27). Não é derivado de readiness isoladamente.

## 9. INSUFFICIENT_DATA — semântica única

Escolha deliberada: **semântica B** — MAINTAIN é o fallback conservador e
`MISSING_DATA` explica a causa.

- **Evidência parcial ou ausente mas contexto classificável** → `MAINTAIN` + reason
  `MISSING_DATA`. Isto é a regra (§35 gate do treinador não muda este default).
- `INSUFFICIENT_DATA` fica **reservado** como action própria para o caso de ausência
  **total** de evidência de execução/adesão (ex.: nunca houve plano observado, snapshot
  nunca sincronizado) — situação em que nem o nível atual é estabelecível. Não é usado
  quando qualquer evidência da janela existe.

Regra de decisão: tem alguma evidência de execução na janela? → classifica (default
MAINTAIN, nunca decide progressão) · não tem nenhuma? → `INSUFFICIENT_DATA`.

## 10. ProgressionTarget

| Target | Significado | Estado atual (não prometer além do real) |
|---|---|---|
| `VOLUME` | tempo total/dose de volume da sessão ou da semana | representável (`planned_duration`, `on_sec`) |
| `INTERVAL_DURATION` | tempo de trabalho por intervalo (on_sec) | representável (`on_sec`) |
| `REPETITIONS` | número de repetições do estímulo principal | **existe em `SEQUENCES` (`src/progression.py`), mas não no build produtivo** — representabilidade NÃO contratada ainda (§11) |
| `LONG_RIDE_DURATION` | duração do treino longo | **parcialmente representável** (`long_day` + template); sem modelo de evolução dedicado |
| `FREQUENCY` | número de sessões por semana | **implica agenda/config (`TRAINING_DAYS`)** — mudança é contrato de agenda, não mutation simples |
| `INTENSITY` | intensidade de zona do estímulo (`on_power` %FTP) | representável COM guardrail: reduzir antes volume, nunca abaixo do piso da zona (escada de `_reduce_one_step`) |
| `NOTHING` | nenhuma dimensão muda nesta janela | n/a (MAINTAIN/consolidar) |

## 11. Não prometer representabilidade inexistente

Registrado como contrato da spec, não como dívida a ignorar:

- **REPETITIONS** existe em `SEQUENCES` como biblioteca de escada, mas o build real
  não consome degraus de `SEQUENCES` (mecânica por TSS/duração em `src/plan.py`). O
  destino de `SEQUENCES` é **PROG-4** (§30); antes disso, `REPETITIONS` como target de
  prescrição é **não representável**.
- **FREQUENCY** não é mutation de um workout: muda a agenda (`TRAINING_DAYS`) e o
  orçamento semanal. Progredir frequência exige decisão de produto/atleta.
- **LONG_RIDE_DURATION** tem um slot (`long_day`) e um template, sem heurística de
  evolução semanal — representável parcialmente só.

## 12. ProgressionReason

Conjunto mínimo inicial (não adicionar razões sem fonte real):

- `LOW_ADHERENCE` — §17; limiar pendente de decisão treinador/produto;
- `GOOD_ADHERENCE` — adesão observada no nível da janela corrente;
- `MISSED_WORKOUTS` — dias de treino vencidos sem execução;
- `INCOMPLETE_WORKOUTS` — execução parcial/abaixo do plano (ver §18);
- `READINESS_RED` / `READINESS_YELLOW` — contexto de prontidão observado (§15);
- `ILLNESS_SIGNAL` — alerta heurístico de possível doença (§16);
- `RECOVERY_CONTEXT` — semana/leitura de recuperação ativa (§20);
- `TAPER_CONTEXT` — janela de prova ativa (§8, §27);
- `STALE_DATA` — evidência envelhecida além da janela de frescura (§13);
- `MISSING_DATA` — ausência parcial de eixos de evidência (§14).

Toda reason precisa de **fonte real** registrada na `ProgressionEvidence` (§13).
Razões são para explainability; a decisão vem da hierarquia (§21), não da contagem de
razões.

## 13. ProgressionEvidence

Entrada conceitual da policy. Cada campo carrega **três metadados**: `source`/
provenance, `availability`, `freshness` quando aplicável.

| Campo | Conteúdo | Provenance (fonte canônica atual) | Availability/Freshness |
|---|---|---|---|
| `adherence` | `done/missed/pending/pct` por semana ISO; classificação via lifecycle + evidência pareada | `adherence_report` (`src/plan.py`); `PlanView` | plano presente? senão `unavailable`; usa dia-ancla `today` |
| `completion/execution` | por workout: lifecycle declarado/efetivo, completion, observed_activity, streams | `WorkoutExecutionView` (`src/ui_state.py`) | snapshot/local; `snapshot_freshness` quando houver |
| `readiness` | eixos observados (`ReadinessAssessment`), trace (observations/missing/coverage), decisão | `assess_readiness_assessment` + `readiness_decision` (`src/readiness.py`) | `stale_days`/`coverage`/`reference_day` |
| `illness_signal` | `illness_alert` (RHR↑ 2+ noites E HRV↓), conjunção observada | `ReadinessTrace` | depende de RHR+HRV presentes |
| `recent_load` | CTL/ATL/TSB observados e taxa de mudança de CTL (ramp) | `latest_metrics` (provider); `derive_ctl_ramp_rate` (`src/ui_state.py`); `CtlRampAdvisory` | métricas na janela? senão `unavailable`; ramp com `window_days` 7 |
| `phase` | fase semantic advisory (GOAL + calendário) | `derive_plan_phase` (`src/plan.py`) | sempre derivável; `TrainingPhaseEngine` NÃO substitui |
| `race_context` | `race_date`, `days_to_race`, janela de taper | meta do plano (`plan.json`); `training_phase`/`_taper_focus` | ausente se sem prova |
| `recovery_context` | semana/marcadores de recuperação ativos (§20) | hoje: sinais via `readiness`/plano; entidade própria é dívida | conforme seam futuro (ver §20) |
| `ramp_advisory` | status da taxa de CTL (HIGH/WITHIN/UNAVAILABLE) | `CtlRampAdvisory` (`src/ctl_ramp_advisory.py`) | advisory; limite configurado injetado, sem default |

Regra: **a policy consome Views/estado observado; nunca consulta provider dentro do
domínio** (§22).

## 14. Missing data — contrato obrigatório

```
missing != zero
missing != healthy
missing != completed
```

- Ausência de eixo **não** é sinal bom nem ruim; nunca é neutralizado como "zero",
  "saudável" ou "concluído".
- A policy **tolera ausência parcial**: defaults conservadores (MAINTAIN), nunca
  PROGRESS derivado de lacuna.
- Implementação: mapear cada campo a `available/unavailable` + `None` no lugar do
  valor; nenhum campo ausente entra em média.

## 15. Readiness

`readiness` é **evidência de contexto/advisory**, nunca soberana (§21 nível 4).

Regras formais:
- **Não** criar `GREEN → PROGRESS` nem `RED → REGRESS` automaticamente.
- GREEN sem bloqueio não é, sozinho, justificativa de aumento (a oportunidade vem da
  execução/adesão + fase, §21 níveis 3/5).
- RED/YELLOW **contexte a dose** (já em `_adapt_session`: REDUCE/REPLACE do dia) e
  pesa na decisão semanal, mas não decide a action sozinho — cenário D da matriz (§33).

## 16. Illness

`illness_alert` é **heuristic safety signal**, não diagnóstico (§4 da SEÇÃO A e
`ReadinessTrace`).

Consequências formais:
- **pode bloquear PROGRESS** (safety blocker, nível 1 da hierarquia);
- a ação final (`RECOVER`/`MAINTAIN`) **continua dependendo do conjunto de evidências**;
- nunca vira elogio de tolerância (missing de HRV não é "sem doença" — §14).

## 17. Adherence

`LOW_ADHERENCE` existe **conceitualmente** (§12), mas seu limiar (nível percentual por
janela) **ainda depende de trainer/product decision** — **Q1** (§35). **Nenhum número
entra na spec/código antes disso.** `adherence_report` já fornece a contagem
done/missed/pending em granularidade por semana ISO (§13) — a evidência está pronta,
o gate não.

## 18. Incomplete workouts

Sessões **incompletas/parciais** podem bloquear progressão (nunca sustentam PROGRESS
sozinhas). A **quantidade/janela** que deflagra MAINTAIN vs REGRESS ainda não foi
decidida — **Q2** (§36). A semântica de `INCOMPLETE_WORKOUTS` não força contagem na
spec; o gate do treinador define o gatilho (e se parciais contam).

## 19. Key workout seam (dívida registrada)

- **Não existe** hoje um conceito canônico de "key workout" (sessão-chave de qualidade
  da semana).
- `dias_qualidade` (focos SWEETSPOT/THRESHOLD/VO2 no `build`) **não é** equivalente a
  key workout — é o conjunto das sessões de qualidade do plano, não uma classificação
  de prioridade/impacto por sessão.
- **PROG-3 deve resolver ou explicitar esse seam** antes de qualquer guardrail que
  dependa de "sessão-chave" (ex.: quebra de Q2). Nada neste contrato depende do seam
  ainda.

## 20. Recovery week (dívida registrada)

- O build normal **não possui recovery-week state canônico** (não há entidade
  persistida "semana de recuperação"); o deload periódico existe só na rampa de
  retorno (`recovery.py`: deload a cada 4 semanas) e na inserção pontual
  (`_insert_recovery`/"plano ajustado").
- **PROG-2/3 não pode depender de entidade inexistente sem seam futuro.** Enquanto
  não existir seam, `recovery_context` fica derivado de sinais (readiness/recent_load),
  com honestidade de provenance (§13) e sem inventar estado.
- PROMPT 67 registrou o mesmo achado na auditoria (§28 do relatório).

## 21. Evidence hierarchy

Ordem de precedência, de cima (mais forte) para baixo:

1. **safety blockers** — `ILLNESS_SIGNAL`; bloqueia PROGRESS obrigatoriamente;
2. **race/taper/recovery context** — `TAPER_CONTEXT`, `RECOVERY_CONTEXT`; suspende ou
   redireciona a progressão normal;
3. **execution/adherence** — `MISSED_WORKOUTS`, `INCOMPLETE_WORKOUTS`,
   `LOW_ADHERENCE`, `GOOD_ADHERENCE`;
4. **physiological/readiness context** — `READINESS_RED`, `READINESS_YELLOW`,
   `recent_load`/ramp (contexto e advisory, nunca comando);
5. **progression opportunity** — a possibilidade de aumentar estímulo, que só existe
   se 1-4 não bloquearem.

Regra formal: **evidência de nível inferior não pode sobrescrever silenciosamente um
blocker superior.** Em caso de conflito, a razão de indecisão vai para
`blocking_reasons` (§23), e a decisão observa o nível mais alto aplicável.

## 22. Determinismo

`ProgressionPolicy` deve ser **pure/deterministic**:

```
mesmos inputs → mesma decision
```

Proibido dentro da policy:
- `datetime.now()` (o "hoje" é injetado);
- provider call;
- file read/plan read;
- environment read;
- network;
- push / plan save / qualquer gravação.

Qualquer dependência externa chega como **parâmetro da evidência** (§13). Testes de
determinismo fazem parte da suíte de PROG-2/3 (mesma input → mesmo output; nenhum
estado escondido).

## 23. Explainability

`ProgressionDecision` sempre possui:
- `action`; `target`; `reasons`.

E, quando aplicável:
- `blocking_reasons` (o que venceu — ex.: `ILLNESS_SIGNAL`);
- `advisory_reasons` (aviso que não determinou a action — ex.: `READINESS_YELLOW`).

**Não** usar apenas score numérico opaco. A decisão deve ser apresentável como frase
legível ("MAINTAIN — boa adesão, mas prontidão amarela e HRV indisponível; sem
progressão esta semana").

## 24. Confidence

- **Não criar confidence arbitrária.** Sem contrato honesto de cobertura (quantos
  eixos de evidência realmente observados), `confidence = None` ou campo opcional.
- `coverage` de readiness já existe (`ReadinessTrace.coverage`); usá-lo como insumo,
  não como nota de "certeza" global.

## 25. Uma dimensão por vez

Registrado como **CANDIDATE_HEURISTIC** (preferência, evidência de projeto), **não**
lei científica universal:

> preferência de progressão principal de **uma** dimensão por janela (ex.: 3×8 → 3×10
> antes de 3×10 com intensidade maior).

Dentro da escada `SEQUENCES` já existe o padrão de escalar repetições antes de duração;
a spec preserva o princípio para o nível semanal. Classificação: `HEURISTIC` (§5.1 da
trilha: não apresentar como fisiologia).

## 26. Volume vs intensity

Guardrail candidato:

> não aumentar simultaneamente volume e intensidade sem regra explícita.

**Status: TRAINER/PRODUCT DECISION** (§37 Q3). Sem threshold. Enquanto não houver
decisão, o default é não escalar as duas dimensões na mesma janela.

## 27. Taper precedence

Existing system contract (já implementado em `_taper_focus`, `src/plan.py`):

> quando taper/race context estiver ativo, a progressão normal não sobrescreve.

A policy **representa** a precedência de TAPER (§21 nível 2) em vez de inventar uma
nova regra de prova. Nada neste contrato substitui `_taper_focus`.

## 28. Ramp

CTL ramp / ramp advisory (`derive_ctl_ramp_rate` + `CtlRampAdvisory`) é:

> **context/advisory** — nunca prescription command.

- Sem default de limite (`max_ramp_points` é injetado, ausente → advisory unavaliado).
- Além disso, classificado como **planning heuristic / provider metric** na camada
  observacional, não parâmetro de prescrição (§22 do relatório PROMPT 67).

## 29. Pw:HR

- **Não usar threshold automático até contrato específico** (o módulo atual
  `src/pw_hr_decoupling.py` só deriva a métrica com elegibilidade estrita de stream).
- **Não incluir "5%"** nem qualquer limiar numérico nesta spec.

## 30. destino funcional de `src/progression.py`

Sem modificar código agora; contrato de destino conceitual:

| Componente atual | Destino conceitual |
|---|---|
| `CompletionScore` (`classify`) | **evidência futura** de execução por bloco de estímulo (usar na `ProgressionEvidence.completion`, quando ligado ao plano) |
| `SEQUENCES` (escadas por família) | **biblioteca de progressão de estímulo** de PROG-4 (degraus repr→dur, com `SEQUENCES`); provê `REPETITIONS`/`INTERVAL_DURATION` quando o build consumir |
| `ProgressionEngine` (`next`) | **superseded/refactored futuramente** pela `ProgressionPolicy` — não evoluir como engine paralela |

Não duplicar `SEQUENCES` em outro lugar antes de PROG-4.

## 31. destino funcional de `src/training_decision.py`

- **Não evoluir como engine concorrente** (risco de 3º mecanismo com o build e a
  futura policy).
- Destino possível: `rationale`/`explainability` da decisão (a mensagem "prioriza X
  agora" vira texto da `ProgressionDecision`); **absorção pela ProgressionPolicy**.
- **Deprecação futura**, sem decidir remoção agora (não há remoção nesta task).

## 32. AdaptationState

- `AdaptationState` (`src/adaptation.py`) continua **BLOCKED** (sem histórico
  observado válido: sem timestamps, sem persistência, sem consumidor).
- **Não incluir como fonte de evidence** até existir histórico observado válido.
  A fonte de evidência de adaptação será a `WorkoutExecutionView` acumulada (PROG-3),
  não um `apply()` heurístico sem âncora temporal.

## 33. Matriz de teste normativa (abstrata)

Os cenários abaixo são normativos para PROG-2/3; **sem thresholds numéricos** (gates
Q1-Q4 decidem os limiares depois):

| # | Entrada abstrata | Action esperada |
|---|---|---|
| A | boa execução + boa adesão + sem blockers | PROGRESS candidato |
| B | baixa adesão + incompletos | não PROGRESS (MAINTAIN/REGRESS conforme contrato) |
| C | illness signal presente | não PROGRESS (bloqueio nível 1) |
| D | YELLOW isolado, resto ok | não força RECOVER (contexto, não comando) |
| E | taper/prova | TAPER (precedência nível 2) |
| F | recovery context ativo | progressão normal suspensa (não sobrescrever) |
| G | missing importante | comportamento conservador (MAINTAIN + MISSING_DATA; §9/§14) |

## 34. Caso real (lição abstrata — sem dados pessoais)

A validação real do PROMT-67 (caso local, nunca versionado) ensina, em termos
abstratos:

> "adesão boa + readiness degradada + missing data pode resultar em MAINTAIN".

Necessário e suficiente como lição: **sinais conflitantes não autorizam decidir por um
eixo sozinho** (nem readiness, nem TSB). Nenhuma data, CTL/ATL/TSB, HRV/RHR, FTP, ID ou
nome é registrado nesta spec — a lição é arquitetural (§34 do relatório), não
dataset.

## 35. Q1 (gate de PROG-2)

> Qual nível de adesão bloqueia a progressão semanal e em qual janela?

Sem resposta nesta task. Especificado: a evidência (`adherence_report`) existe; o
limiar (nível % e janela) é decisão do treinador antes de PROG-2.

## 36. Q2 (gate de PROG-2)

> Quantas sessões relevantes incompletas/parciais justificam MAINTAIN vs REGRESS?

Sem resposta nesta task. Verbete do §18: `INCOMPLETE_WORKOUTS` pode bloquear PROGRESS;
o gatilho de REGRESS é decisão do treinador (e depende do seam de key workout, §19).

## 37. Q3 (gate de PROG-2/4)

> Como priorizar volume vs tempo no estímulo vs repetições vs intensidade ao longo
> das semanas?

Sem resposta nesta task. Define o ranking entre `ProgressionTarget` e a regra de
"uma dimensão por vez" (§25) e o guardrail volume×intensidade (§26).

## 38. Q4 (gate de PROG-2/3)

> Quando antecipar/detectar recovery? Por execução, readiness, fase, densidade ou
> combinação?

Sem resposta nesta task. Define como `recovery_context` (§20) é povoado antes do seam
de recovery-week.

## 39. Perguntas científicas (separadas de produto)

Dependências científicas a serem pesquisadas com fonte verificável (nada desta spec
inventa regra):

- distribuição/densidade de sessões intensas por semana (fase e nível);
- progressão de volume entre semanas (taxa e janela);
- progressão de tempo no estímulo (métricas de intervalo);
- recovery/deload evidence (quando recuperar de fato melhora tolerância).

Estas são perguntas de pesquisa, não gates de PROG-1; distinta de Q1-Q4 (decisão de
produto/treinador, §35-38).

## 40. Ordem recomendada de implementação

```
PROG-1 contract  (esta spec)
→ trainer Q1-Q4
→ PROG-2 guardrails
→ PROG-3 evidence integration
→ PROG-4 stimulus progression (SEQUENCES/biblioteca)
→ PROG-6 historical validation
→ PROG-5 prescription mutation
```

PROG-5 (mutação de prescrição) permanece por último: nada do contrato pressupõe
escrever plano; a policy decide (View) e PROG-5/`PrescriptionProgression` aplica,
num release posterior e separado (§2).
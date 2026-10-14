# SPEC — INSIGHT M1 v2: camada LLM read-only de apresentação

Status: **MERGED TO MASTER** — implementação integrada via `FAST_FORWARD_ONLY` no
commit `6b4a9791dfca5e562261b2c4c64c75de4e9b2e0c`, com CI de master verde (run
`38578649393`); ainda não released.
Versão de referência: **Hermes Coach 0.0.36**.
Branch canônica: **`master`**.

Rastreabilidade:
- experimento histórico: `lab/m1-contrato`;
- commits auditados: `f23f2ae`, `3781589`, `fd2b51b`, `aefd8ac`, `a335bfe`;
- arquitetura atual: `src/application.py`, `src/provider.py`, `src/intervals_adapter.py`;
- guardrails: `AGENTS.md`, `docs/EMBASAMENTO-CIENTIFICO.md`, `docs/ROADMAP.md`.

---

## 1. Problema

O Hermes já possui um motor determinístico que observa dados, constrói Views,
aplica heurísticas/policies explícitas, produz Advice e Prescription e controla
persistência/publicação.

O experimento `lab/m1-contrato` tentou adicionar um LLM para transformar estado já
decidido em linguagem clara para o atleta. A ideia continua válida, mas a
implementação histórica permitia que o LLM devolvesse campos de prescrição
(`foco`, `duracao_min`, `intensidade`) e carregava regras antigas, como
`TSB <= -20` como gatilho de alerta.

O M1 v2 redefine a fronteira:

> **o LLM pode explicar uma decisão; nunca pode tomar, alterar, completar ou reinterpretar a decisão.**

---

## 2. Arquitetura oficial

```text
Provider observations
        ↓
Application / Views
        ↓
Policies / Advice existentes
        ↓
Prescription existente
        ↓
InsightView (read-only)
        ↓
LLM
        ↓
InsightPresentation
```

`InsightPresentation` não possui caminho de retorno para plano, readiness, FTP,
progression, lifecycle, reconcile ou provider.

---

## 3. Regra de autoridade

Ordem de autoridade:

1. observed/provider state;
2. Hermes-derived View;
3. Policy / heuristic;
4. Advice;
5. Prescription;
6. InsightPresentation.

`InsightPresentation` é sempre a camada menos autoritativa.

Regra formal:

```text
InsightPresentation cannot modify upstream state.
```

---

## 4. Fora de escopo

M1 v2 não implementa:

- geração ou alteração de treinos;
- mudança de foco;
- mudança de duração;
- mudança de intensidade;
- FTP;
- progression;
- deload;
- readiness policy;
- illness/diagnosis logic;
- provider writes;
- calendar writes;
- plan persistence;
- lifecycle transition;
- automatic actions;
- chat autônomo;
- tool calling pelo LLM;
- memória própria do insight.

---

## 5. O que reaproveitar de `lab/m1-contrato`

### Reaproveitar como princípio

Do `f23f2ae`:
- LLM como enrichment, nunca decisão;
- schema fechado;
- prompt versionado;
- hash do prompt;
- validação offline;
- fallback determinístico.

Do `3781589`:
- testes offline do contrato;
- CI de evals separado;
- dataset com casos bons + contraexemplos.

Do `a335bfe`:
- invariantes do domínio pertencem ao repo do app;
- harness genérico não conhece fisiologia/ciclismo.

### Reimplementar

- `InsightContext`;
- schema;
- grounding de facts;
- runtime provenance;
- workflow de eval;
- integração com `ai-lab`.

### Descartar

- `TSB <= -20` como regra universal;
- `±10 min` de tolerância de duração;
- enums antigos de foco;
- qualquer campo de Prescription na saída do LLM;
- harness não pinado;
- billing dentro de `contract.py`.

---

## 6. InsightView

`InsightView` é o único input conceitual do LLM.

Ele deve ser:

- read-only;
- serializável;
- provider-independent;
- sem I/O;
- sem leitura de `.env`;
- sem provider call;
- sem lógica fisiológica própria;
- construído pela `Application`.

Exemplo conceitual:

```python
@dataclass(frozen=True)
class InsightView:
    schema_version: int
    subject: str
    headline_facts: tuple["InsightFact", ...]
    advisory: Optional["InsightAdvisory"]
    prescribed_session: Optional["PrescribedSessionSummary"]
    provenance: tuple["InsightSource", ...]
```

Os nomes finais são decisão de implementação.

---

## 7. Facts

O LLM não recebe `raw` como fonte canônica de números.

Fatos são estruturados:

```python
@dataclass(frozen=True)
class InsightFact:
    key: str
    value: str | int | float
    unit: Optional[str]
    classification: str
```

`classification`:

- `observed`
- `derived`
- `heuristic`
- `advice`
- `prescription`

A apresentação nunca pode promover um fato para uma classe mais autoritativa.

---

## 8. Missing data

Contrato obrigatório:

```text
missing != zero
missing != healthy
missing != completed
missing != safe
```

Ausência:
- não vira fato positivo;
- não implica normalidade;
- pode ser representada como `unavailable`;
- nunca sustenta conclusão favorável por si só.

---

## 9. Planned vs observed

Contrato obrigatório:

```text
planned workout != observed execution
```

`InsightView` distingue claramente:
- prescrição planejada;
- execução observada;
- ausência de evidência.

O LLM não pode dizer que um treino foi realizado só porque existe um
`PlannedWorkout`.

---

## 10. FTP

M1 v2 não interpreta nem altera FTP.

- `FtpReference` confirmado pode ser apresentado como canônico.
- `FtpEvidence` continua evidence/estimate.
- Advice continua Advice.
- estimativa nunca é descrita como FTP confirmado.

O LLM não pode:
- confirmar FTP;
- criar `FtpReference`;
- promover evidence;
- usar `DEFAULT_FTP` como fisiologia.

---

## 11. Readiness

Readiness só pode ser apresentado a partir das Views/decisions existentes.

O LLM não recalcula thresholds e não cria regras próprias de TSB/HRV/RHR/sono.

Sem Advice upstream correspondente, o insight não cria alerta.

---

## 12. Progression

M1 v2 não implementa PROG.

Se `ProgressionDecision` existir futuramente, o insight apenas explica a decisão recebida.

Não pode criar:
- `+5%`;
- `+10%`;
- nova intensidade;
- nova duração;
- deload;
- sequência de progressão.

---

## 13. InsightPresentation

Saída conceitual:

```python
@dataclass(frozen=True)
class InsightPresentation:
    headline: str
    explanation: str
    next_action_text: str
    caution_text: Optional[str]
```

Propriedade obrigatória:

> **nenhum campo representa Prescription.**

Proibido como campo de saída:
- `focus`;
- `duration`;
- `intensity`;
- `ftp`;
- `watts`;
- `tss`;
- workout params;
- lifecycle;
- readiness state;
- progression action;
- provider payload.

---

## 14. Schema fechado

O schema final deve usar:

```text
additionalProperties = false
```

ou equivalente.

Payload inválido → fallback determinístico.

Nunca corrigir silenciosamente JSON semanticamente inválido e tratá-lo como válido.

---

## 15. Grounding numérico

Preservar a intenção histórica de “não inventar números”, mas descartar regex sobre `raw`.

Opções aceitáveis:

### A — zero números livres
O LLM gera texto sem números; a UI interpola deterministicamente.

### B — facts estruturados
O LLM cita somente valores presentes em `InsightFact`.

### C — placeholders
O modelo devolve placeholders e o renderer substitui.

Preferência inicial: **A ou C**.

A implementação precisa escolher uma opção explicitamente antes de código produtivo.

---

## 16. Caution / alert

`caution_text` verbaliza Advice já existente.

Fluxo:

```text
Hermes Policy / Advice
        ↓
InsightView.advisory
        ↓
LLM verbaliza
```

Sem advisory upstream:

```text
caution_text = None
```

O insight não cria alerta a partir de CTL/ATL/TSB/HRV/RHR.

---

## 17. Fallback determinístico

Qualquer falha do insight preserva o funcionamento do Hermes.

Inclui:
- timeout;
- auth;
- rate limit;
- provider indisponível;
- JSON inválido;
- schema inválido;
- grader fail;
- model mismatch.

Contrato:

```text
LLM failure → deterministic fallback presentation
```

Nunca:

```text
LLM failure → no training decision
```

---

## 18. Feature flag

Primeira integração produtiva deve ser opt-in e desligada por default.

Teste obrigatório:

```text
same upstream state
insight off / insight on
→ same prescription
```

---

## 19. Runtime provenance

Separar contrato funcional de provenance.

Exemplo:

```python
@dataclass(frozen=True)
class InsightRuntimeManifest:
    provider: str
    requested_model: str
    resolved_model: Optional[str]
    prompt_version: str
    prompt_hash: str
    harness_version: Optional[str]
    harness_commit: Optional[str]
    executed_at: str
```

`executed_at` vem da camada runtime.

---

## 20. Model pinning

Registrar, quando possível:
- provider;
- requested model;
- resolved model/version;
- execution timestamp.

Não afirmar reprodutibilidade absoluta só porque o nome do modelo foi “pinado”.

---

## 21. Cost accounting

Custo é preocupação separada do contrato funcional.

Sugestão:

```text
insight/
  contract.py
  view.py
  presentation.py
  prompt.py
  runtime.py

evals/
  graders.py
  cases.jsonl
  cost_model.py
```

Preço:
- possui data de vigência;
- não entra no schema funcional;
- não altera prompt hash;
- não altera motor.

---

## 22. Harness / ai-lab

Se `ai-lab` continuar:

Hermes é dono de:
- dataset;
- domain graders;
- schema;
- prompt;
- invariantes.

`ai-lab` é dono de:
- runner;
- model invocation genérica;
- report aggregation;
- latency/cost instrumentation genérica.

O harness não conhece thresholds nem semântica do Hermes.

---

## 23. Harness pinning

Proibido rodar HEAD arbitrário do harness.

Obrigatório usar:
- SHA;
- tag imutável;
- ou release pinada.

O commit/version do harness entra no relatório de eval.

---

## 24. CI

### Core CI
Obrigatório para merge:

```bash
python3 -m unittest discover -s tests -v
```

Nunca depende de LLM/API.

### Insight eval CI
Separado.

Resultados explícitos:

```text
PASS
FAIL
SKIPPED
INFRA_ERROR
```

`SKIPPED`/`INFRA_ERROR` não equivalem a `PASS`.

---

## 25. Dataset

Dataset fica no repo do Hermes.

Cada caso deve possuir:
- `id`;
- `context`;
- `expected_properties`;
- contraexemplos por grader, quando úteis.

Preferir properties a exact-string matching.

---

## 26. Graders mínimos

### G1 — schema
Saída respeita `InsightPresentation`.

### G2 — no prescription fields
Nenhum campo proibido aparece.

### G3 — no contradiction
Texto não contradiz upstream.

### G4 — factual grounding
Nenhum fato objetivo novo é introduzido.

### G5 — caution provenance
`caution_text` só existe com advisory upstream.

### G6 — deterministic fallback
Falha do modelo devolve fallback válido.

### G7 — prescription invariance
Insight ligado/desligado não muda Prescription.

---

## 27. Graders proibidos

Não criar graders com novas policies como:

```text
TSB <= -20
HRV < 80%
RHR > +3
sleep < 6h
```

O grader verifica respeito a uma decisão upstream; não reimplementa a decisão.

---

## 28. Segurança

O LLM do insight:
- não recebe API key;
- não recebe `.env`;
- não recebe secrets;
- não possui shell;
- não possui provider write;
- não possui filesystem write;
- não possui tools mutáveis;
- recebe o mínimo contexto necessário.

---

## 29. Privacidade

Antes de integração com provider externo, revisar quais facts podem sair do ambiente local.

Preferir:
- métricas necessárias;
- labels;
- estados derivados;
- sem identificadores desnecessários;
- sem credenciais;
- sem payload bruto.

---

## 30. Determinismo do core

Insight não entra em cálculo do motor.

Teste arquitetural:

```text
build(state, insight_enabled=False) == build(state, insight_enabled=True)
```

para Prescription relevante.

---

## 31. Application boundary

A `Application` monta o `InsightView`.

Direção:

```text
domain/application state
        ↓
Application.get_insight_view(...)
        ↓
Insight service / adapter
```

Nunca:

```text
plan.py → LLM
readiness.py → LLM
ftp_history.py → LLM
```

---

## 32. LLM provider boundary

Se houver provider externo:

```python
class InsightModelProvider(Protocol):
    def generate(self, request: InsightRequest) -> InsightModelResponse:
        ...
```

Não reutilizar `TrainingMetricsProvider`.

Erros do provider LLM têm taxonomia própria e sempre caem em fallback.

---

## 33. Prompt

O prompt:
- não decide;
- não recomenda mudança não presente upstream;
- não inventa fato;
- não cria alerta;
- usa somente facts permitidos;
- produz apenas schema.

Prompt nunca substitui graders.

---

## 34. Prompt version/hash

Qualquer alteração semântica:
- incrementa versão;
- muda hash.

Testes de hash usam bytes/path injetável ou tempfile, sem modificar o prompt real do checkout.

---

## 35. Observabilidade

Registrar com segurança:
- prompt version;
- prompt hash;
- provider/model;
- latency;
- result status;
- grader status;
- fallback used.

Não registrar secrets.

---

## 36. Failure modes

| Falha | Resultado |
|---|---|
| timeout | fallback |
| auth | fallback |
| invalid JSON | fallback |
| schema violation | fallback |
| grader failure | fallback |
| unsupported model | fallback |
| harness indisponível em eval | `INFRA_ERROR` |
| no insight data | unavailable/neutral |
| upstream missing data | não inventar |

---

## 37. Persistência

M1 v2 não precisa persistir `InsightPresentation` no primeiro release.

Se persistir futuramente:
- schema version;
- runtime provenance;
- source state fingerprint;
- nunca tornar apresentação estado canônico.

---

## 38. UI futura

UI pode exibir:

```text
Treino de hoje
[structured workout card]

Insight
[headline]
[explanation]
[next action]
[caution]
```

A UI nunca extrai Prescription do texto.

---

## 39. Critérios de aceite

M1 v2 só é implementado quando:

1. existe `InsightView` read-only;
2. existe `InsightPresentation` sem Prescription;
3. schema é fechado;
4. prompt version/hash existe;
5. provider LLM está atrás de boundary;
6. fallback determinístico funciona;
7. insight off/on não altera Prescription;
8. dataset pertence ao Hermes;
9. domain graders pertencem ao Hermes;
10. harness está pinado;
11. core CI não depende de LLM;
12. eval CI não reporta PASS sem executar;
13. nenhum threshold novo foi criado;
14. nenhum provider write foi adicionado;
15. full suite permanece verde.

---

## 40. Testes mínimos

### Unit
- schema válido;
- campo extra rejeitado;
- tipos inválidos rejeitados;
- payload não objeto rejeitado;
- prompt hash estável;
- prompt hash muda com bytes diferentes;
- fallback por tipo de erro;
- no prescription fields;
- no unauthorized caution.

### Architecture
- `src/plan.py` não importa insight runtime;
- readiness não importa insight runtime;
- FTP modules não importam insight runtime;
- provider training boundary não depende do insight;
- build invariant com insight ligado/desligado.

### Eval
- treino planejado;
- execução observada;
- missing data;
- advisory presente;
- advisory ausente;
- FTP evidence vs confirmed reference;
- readiness unavailable;
- forbidden fields;
- invented fact;
- contradictory text.

---

## 41. Migração do experimento histórico

Não cherry-pickar `lab/m1-contrato`.

Estratégia:

```text
master 0.0.36
    ↓
feat/insight-m1-v2
    ↓
implementação limpa baseada nesta SPEC
```

A branch histórica permanece somente como referência de P&D.

---

## 42. Destino da branch histórica

Até o M1 v2 ser entregue:
- não mergear;
- não rebasear;
- não deletar.

Depois, remoção pode ser decidida em tarefa separada.

---

## 43. Sequência recomendada

### INSIGHT-1 — contrato (**DONE**)
- `InsightView`;
- `InsightPresentation`;
- schema;
- testes offline.

### INSIGHT-2 — renderer/fallback (**DONE**)
- fallback determinístico;
- grounding strategy.

### INSIGHT-3 — provider boundary (**DONE**)
- protocol e error taxonomy;
- sem provider/adaptador concreto e sem integração no build.

### INSIGHT-4 — eval harness (**DONE**)
- dataset;
- graders;
- harness offline no repositório;
- integração/pin do ai-lab e workflow dedicado permanecem não criados.

### INSIGHT-5 — Application seam (**DONE**)
- `Application.get_insight_view`;
- geração opcional read-only.

### INSIGHT-6 — UI/CLI presentation (**DONE**)
- apresentar insight;
- nunca parsear texto para ação.

Cada etapa deve ser commit/review separado.

---

### Status da implementação no master

INSIGHT-1..6 foram integrados em `master` via `FAST_FORWARD_ONLY` no commit
`6b4a9791dfca5e562261b2c4c64c75de4e9b2e0c`, com CI de master verde (run
`38578649393`), e ainda não houve release.

- O contrato, renderer/fallback, boundary de provider, harness offline G1–G7,
  seam read-only da `Application` e apresentação CLI foram implementados.
- `HERMES_INSIGHT_ENABLED` permanece default OFF; flag ON usa somente o
  fallback determinístico e não altera Prescription.
- Não há provider concreto, modelo selecionado, invocação LLM online, integração
  de harness externo, workflow dedicado de eval, chat autônomo, tool calling ou
  memory.
- `FtpReference` canônico permanece omitido fail-closed; `FtpEvidence` não é
  promovido; FTP planejado permanece Prescription.
- Permanecem abertos, sem bloquear merge: `INSIGHT2-AUD-03` (limites globais de
  tamanho de fact/input/output) e `INSIGHT3-AUD-01` (consistência entre request
  e provenance quando existir runtime de invocação).

---

## 44. Decisões abertas para evolução posterior

1. Grounding:
   - A: zero números livres;
   - B: facts estruturados;
   - C: placeholders.

2. Primeiro provider/model:
   - não assumir o modelo histórico.

3. Quais facts podem sair do ambiente local.

4. Primeiro local de exibição:
   - CLI;
   - relatório;
   - UI futura.

5. Eval online:
   - manual;
   - nightly;
   - path-gated em PR.

Nenhuma dessas decisões autoriza mudança no motor.

---

## 45. Não-goals

M1 v2 não é:
- coach por LLM;
- substituto de `Application`;
- substituto de readiness;
- substituto de progression;
- mecanismo de prescrição;
- mecanismo de safety;
- fonte de ciência;
- fonte canônica de estado.

É:

> **uma camada auditável de linguagem sobre decisões já produzidas pelo Hermes.**

---

## 46. Regra final

Se houver conflito:

```text
structured Hermes state wins
```

Se não for possível explicar sem inventar:

```text
fallback wins
```

Se o LLM sair do contrato:

```text
reject output
```

Nunca aceitar porque “parece razoável”.

---

## 47. Status de saída

Esta SPEC formalizou a auditoria de `lab/m1-contrato` e definiu a fronteira
segura agora implementada na feature. A implementação não altera Prescription,
não adiciona threshold e não integra um LLM online.

Status recomendado no ROADMAP:

```text
INSIGHT M1 v2 — MERGED TO MASTER
```

# SPEC — INSIGHT M2: Online Explanation Runtime

**Status: SPEC READY / IMPLEMENTATION NOT STARTED.** M2 é um milestone separado
de M1/M1.1. Provider, modelo, SDK/HTTP, credenciais, sink de telemetria e harness
externo permanecem **OPEN**. A invocação online permanece OFF por default.

## 1. Objetivo e autoridade

M2 pode explicar um `InsightView` já resolvido por Hermes: constrói request
mínimo, faz no máximo uma invocação de inferência, valida a resposta e devolve
uma `InsightPresentation` ou o fallback determinístico existente.

```text
observed/provider > derived View > policy/heuristic > Advice > Prescription
> InsightPresentation
```

`InsightPresentation` é a camada menos autoritativa. Não existe caminho de volta
para plano, Prescription, readiness, FTP, progressão, lifecycle, dados do
provider ou persistência local.

## 2. Non-goals iniciais

M2 não inclui tool calling, browser, filesystem/code tools, memory, histórico de
conversa, agent loop, provider writes, streaming, cache, live retrieval/facts
externos, repair por segundo modelo, mutação de domínio, inferência/promoção de
FTP, recomputação de readiness/progressão ou nova policy de deload.

## 3. Arquitetura e seams

```text
Application.get_insight_view()
  → egress projection / PromptBuilder (pure)
  → InsightModelRequest
  → InsightRuntime
  → InsightModelProvider adapter
  → InsightModelResponse.text
  → strict decoder + template/grounding validator
  → renderer local determinístico
  → InsightPresentation

side outputs: RuntimeProvenance, telemetry sanitizada, cost record opcional
```

`PromptBuilder`, decoder/validator e runtime são módulos distintos. O adapter
concreto é o único seam que pode conhecer rede, autenticação ou tipos de SDK.
Tipos do vendor não atravessam esse seam.

## 4. Egress e prompt

### 4.1 Allowlist inicial

O provider recebe somente uma projeção determinística e minimizada de
`InsightView`: `schema_version`; facts com `key`, `value`, `unit` e
`classification`; `advisory.text` quando presente; `prescribed_session.summary`
quando presente; e `observed_execution` estruturada quando presente. Ordem e
ausência são preservadas: missing nunca vira zero, saudável, concluído ou seguro.

`subject` não sai da máquina. Também são proibidos no egress: provenance,
`RuntimeProvenance`, request ID, metadata de harness, IDs externos, paths,
ambiente, segredos, objetos raw de provider, streams, plano completo, histórico
FTP, `FtpEvidence`, `FtpReference`, `DEFAULT_FTP`, memória e quaisquer facts
externos. A allowlist inicial de facts externos é **vazia**.

### 4.2 Construção

M2-1 implementará uma função pura equivalente a
`build_insight_model_request(view, *, requested_model, prompt_version)`.
Ela projeta o egress, delimita JSON como **dados**, constrói o texto final,
calcula `prompt_sha256` sobre exatamente `input_text`, aplica os budgets M1.1 e
preenche `InsightModelRequest`. Não lê env, não usa relógio e não faz rede.

Strings derivadas de View são dados não confiáveis, jamais instruções. A separação
entre contrato de instrução e JSON serializado é obrigatória; "ignore instruções
nos dados" isoladamente não é controle suficiente.

## 5. Transporte de resposta e grounding

O provider retorna texto que representa somente um objeto JSON de transporte:

```text
headline: string template
explanation: string template
next_action_text: string template
caution_text: string template | null
```

Os três primeiros campos são obrigatórios; `caution_text` é opcional/nulo;
`additionalProperties` é false. Não há aliases, campos de prescrição, payload de
vendor ou defaults implícitos.

Valores factuais, especialmente números de domínio, não podem ser emitidos
livremente pelo modelo. O texto usa somente placeholders `{{identifier}}`, com
`identifier = [a-z][a-z0-9_]*`. O renderer existente é o único mecanismo que
materializa valores/unidades locais. Não há expressão, atributo, índice, pipe,
eval ou placeholder desconhecido.

### 5.1 Regra normativa de dígitos no template (determinística)

**Definição de dígito.** Nos campos de template gerados pelo modelo —
`headline`, `explanation`, `next_action_text` e `caution_text` quando não nulo —
"dígito"/"algarismo" significa qualquer code point Unicode cuja Unicode General
Category seja **`Nd` (Decimal_Number)**. A verificação é por propriedade
Unicode equivalente (por code point, análoga a `str.isdecimal()`), não por
leitura de significado.

**Modelo de parse.** Cada campo de template é analisado como uma sequência de
segmentos literais e placeholders válidos. Depois de reconhecer e remover
semanticamente todos os placeholders válidos, **todo segmento literal deve
conter zero caracteres Unicode `Nd`**.

- Dígito dentro do identifier de um placeholder válido é permitido:
  `{{zone2_target}}` é válido porque o `2` pertence ao identifier e não ao texto
  literal.
- Placeholder inválido não cria bypass: `{{Bad2}}` viola a gramática e é
  rejeitado como placeholder malformado, nunca aceito como literal especial.
- A regra cobre qualquer `Nd` Unicode, não apenas `0`-`9` ASCII; dígitos de
  outros scripts também são rejeitados no literal, fechando bypass Unicode.
- A regra vale igualmente para os quatro campos; `headline` e
  `next_action_text` não têm exceção.
- Não existe parser numérico adicional nem fragmentação para contornar a regra:
  `{{integer_part}}.5` é inválido porque `5` é `Nd` literal. Pontuação e sinais
  (`.`, `,`, `-`, `+`, `%`) não são números por si só e tampouco autorizam
  dígito literal.

**Exemplos válidos (template):**

- `"Potência alvo: {{target_power}} W"` — desde que `target_power` seja fact
  permitido.
- `"Trabalhe na zona {{target_zone}}"`
- `"CTL atual: {{ctl}}"`
- `"Use {{zone2_label}}"`

**Exemplos inválidos (template):**

- `"Potência alvo: 250 W"` — `250` está em segmento literal.
- `"Faça 3 repetições"` — `3` é literal.
- `"Treine em Z2"` — `2` é literal.
- `"Zona 2"` — `2` é literal.

**Unidades.** Unidades puramente textuais (`W`, `bpm`, `h`, `min`, `%`) podem
permanecer literais, pois não contêm `Nd`. Qualquer representação de unidade ou
label que contenha dígito deve entrar via placeholder/structured fact — por isso
`Z2` não é literal válido.

**Metadados fora do template.** `schema_version`, `prompt_version`, metadata de
protocolo/versão e metadata de requisição não fazem parte dos quatro campos de
template e seguem seus próprios contratos. A proibição de `Nd` literal aplica-se
somente aos campos de template gerados pelo modelo.

**Template versus Presentation final.** A regra é aplicada **antes** do render
determinístico local. A `InsightPresentation` final pode conter números, pois
eles são inseridos exclusivamente a partir dos valores dos placeholders
resolvidos localmente. O template `"Alvo {{power_target}} W"` é válido e a
apresentação renderizada `"Alvo 250 W"` é válida quando `250` veio de
`{{power_target}}`; o template `"Alvo 250 W"` continua inválido.

**Propriedade do valor.** O modelo escolhe apenas a referência ao fact
permitido. Valor, unidade factual, classificação e autoridade vêm exclusivamente
do estado estruturado do Hermes; nada disso é determinado pelo modelo.

**Escopo do validator (determinístico, sem classificador).** Passos
semanticamente exigidos do decoder/validator:

1. reconhecer placeholders válidos pela gramática;
2. rejeitar placeholder malformado;
3. separar os segmentos literais remanescentes;
4. rejeitar qualquer segmento literal que contenha code point com General
   Category `Nd`;
5. validar cada placeholder contra as allowed fact keys;
6. executar as checagens já definidas de grounding, caution e schema.

Sem NLP, sem classificação numérica semântica, sem regex de fisiologia e sem
heurística contextual. A regra é deterministicamente verificável, evita
hallucination numérica no template e bloqueia bypass por dígito Unicode não
ASCII. Ela pertence ao grounding determinístico de runtime (G4: runtime + eval);
a contradição semântica completa (G3) permanece avaliação offline.

O decoder/validator é puro e falha fechado: JSON inválido, markdown extraction,
campo ausente/extra, tipo inválido, placeholder desconhecido, sintaxe inválida,
número factual livre, caution não autorizada ou resposta oversized levam a
fallback. Não há rename, stripping de fence, truncamento, remoção de campos,
defaults ou repair por modelo.

`caution_text` só é permitido se `InsightView.advisory` existe. O runtime não
recalcula fisiologia/readiness/progressão nem usa NLP para contradição: a parte
estrutural é runtime; contradição semântica completa continua avaliação offline.

## 6. Runtime, provenance e fallback

`InsightRuntime` recebe dependências explicitamente: provider, builder,
decoder/validator, fallback e clock/`executed_at` injetado. Não constrói View,
não muta Application e não grava nada.

O resultado conceitual é:

```text
InsightRuntimeResult
  presentation: InsightPresentation
  status: SUCCESS | FALLBACK_DISABLED | FALLBACK_CONFIG |
          FALLBACK_PROVIDER | FALLBACK_INVALID_RESPONSE | FALLBACK_INTERNAL
  provenance: InsightRuntimeProvenance | None
```

Em sucesso, provenance é construída exclusivamente por
`InsightRuntimeProvenance.from_execution()`. Em fallback não se fabrica provider,
resolved model ou provenance bem-sucedida. `request_id` continua fora de
`RuntimeProvenance`, podendo existir apenas em telemetria se observado.

Qualquer falha conhecida, e uma única contenção externa para erro inesperado,
retorna o fallback determinístico já existente. Erro bruto não é exibido ao atleta.
Explicação jamais impede decisão de treino.

## 7. Flags, timeout e retry

`HERMES_INSIGHT_ENABLED` preserva o significado atual: habilita a presentation
local. Ele não autoriza egress. A nova flag `HERMES_INSIGHT_ONLINE_ENABLED` é
separada, conservadora e OFF por default. Chamada externa exige ambas ON; valor
ausente/inválido é OFF. ON sem configuração válida não chama provider e retorna
fallback com status sanitizado.

Cada invocação permite uma tentativa. Retry automático e retries do SDK devem ser
desabilitados. Rate limit, timeout, auth, indisponibilidade, erro de transporte,
resposta inválida, grounding, provenance e size não são retryable inicialmente.
O adapter concreto deve receber timeout explícito, finito e configurado; o core
não possui timeout escondido nem aceita infinito.

Streaming e shadow egress não pertencem ao M2 inicial. Shadow exige decisão futura
porque ainda transmite dados externos.

## 8. Segurança, telemetria e custo

Sem tools, memória ou escrita de provider. Segredos ficam somente no futuro
adapter/configuration seam: nunca em View, prompt, request, Presentation,
RuntimeProvenance ou telemetria. O runtime não lê arquivos arbitrários.

Telemetria é seam separada, no-op/in-memory testável e sem persistência obrigatória
inicial. Pode registrar provider/model solicitado-resolvido, versão/hash/schema,
timestamp, latência, bytes de resposta, status, classe de erro, request ID e
metadata de harness quando disponíveis. Nunca registra prompt/raw response/View
completa/segredos/SDK object ou repr arbitrário de exceção.

Custo é record separado de `RuntimeProvenance`; uso/custo ausente continua ausente,
nunca zero fabricado. Latência é medida pela orquestração, não pelo domínio nem
pela factory de provenance.

## 9. Eval, CI e rollout

Core CI permanece offline e independente de provider. Runtime validator não é o
mesmo módulo do grader de benchmark, embora helpers puros possam ser compartilhados.
G1/G2/G4/G5 rodam em runtime e eval; G3 runtime só estrutural, eval completo; G6
é runtime+eval; G7 é teste de integração/arquitetura+eval.

Online eval será workflow separado, secret-gated e com `PASS`, `FAIL`, `SKIPPED`
e `INFRA_ERROR` distintos. Harness externo, se adotado, exige SHA/tag/release
imutável. Hermes mantém dataset, schema, prompt e invariantes; ai-lab, se usado,
mantém runner genérico, invocation e agregação de custo/latência.

Rollout: estágio 0 provider-neutral offline; estágio 1 developer opt-in online;
estágio 2 opt-in limitado. Expansão posterior exige decisão nova. A invariância de
Prescription e a ausência de writes são release-blocking.

## 10. Provider/model — OPEN

M2-0 não seleciona provider/model. M2-4 decidirá provider, estratégia de modelo
solicitado, SDK versus HTTP, origem de segredos, retenção/privacidade, timeout
operacional, retry do vendor desabilitado e estratégia de resolved-model.

Requisitos mínimos: timeout finito, sem tools/memória, non-streaming, isolamento
de credenciais, identidade de modelo quando possível, erros classificáveis e
limite local de resposta. Structured output, request ID e usage metadata são
SHOULD; metadata rica pode permanecer dentro do adapter.

## 11. Gates atômicos

| Gate | Escopo | Critério de saída |
|---|---|---|
| M2-0 | SPEC/design | esta SPEC; decisões de grounding, egress, flags, retry, resultado, telemetria e rollout fechadas |
| M2-1 | prompt/request puro | projeção minimizada, subject/provenance excluídos, hash do input final, sem I/O/rede/env |
| M2-2 | decoder/validator | JSON estrito, templates/grounding/caution (inclui a regra `Nd` da §5.1), render local, sem repair |
| M2-3 | runtime com fake provider | uma tentativa, matriz de fallback, provenance de sucesso, no-write/invariância |
| M2-4 | decisão provider/model | ADR/record de provider, modelo, SDK/HTTP, segredo, retenção e timeout — **ACEITO**: `ADR-007` (OpenAI `gpt-5.4-nano-2026-03-17`, SDK, timeout finito, `max_retries=0`, non-streaming, `store:false` quando aplicável) |
| M2-5 | adapter concreto | único local de rede/auth, timeout finito, zero retry/tools/streaming, tipos vendor contidos |
| M2-6 | telemetria/custo | eventos sanitizados, request ID operacional, custo separado |
| M2-7 | eval online | workflow separado, secrets, status explícitos, harness pinado se houver |
| M2-8 | CLI/rollout | duas flags, OFF por default, developer/limited opt-in, fallback invariável |
| M2-9 | closure | audit, CI, docs e evidência publicados; sem release implícito |

Critérios de saída de M2-2 exigem testes que cubram, no mínimo: rejeição de
dígito literal ASCII; rejeição de `Nd` Unicode não ASCII em literal; aceitação
de dígito dentro de identifier de placeholder válido; rejeição de placeholder
malformado; aceitação de Presentation final com número vindo de placeholder; e
aplicação da regra aos quatro campos de template.

M2-4 só começa após M2-1..3 publicados e verdes. M2-5 depende de M2-4; nenhuma
integração CLI online pode pular esses gates.

## 12. Critérios de aceite M2

M2 só fecha com provider/model e allowlist aprovados; adapter e provenance
consistentes; prompt/hash, schema, grounding, caution, fallback e invariância
cobertos; core offline; eval online separado; rollout explícito; telemetria segura;
e nenhum retorno ao estado de treino. Não implica release, GA ou flag ON por
default.

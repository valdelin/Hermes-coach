# ADR-007 — Provedor e modelo iniciais para INSIGHT M2 (provider-neutral runtime)

- **Data:** 2026-10-16
- **Status:** aceito
- **Escopo:** hermes-coach (repo `github.com/valdelin/Hermes-coach`), módulo `src/insight/*`

## Contexto

O M2-3 publicou o runtime provider-neutral (`1d478f0`) com seam composto M2-2 obrigatório, uma única tentativa, fallback determinístico e provenance somente em SUCCESS. Os gates M2-4/M2-5 exigem decidir e depois implementar o adapter concreto sem violar o contrato M2.

Requisitos (SPEC M2 §6–§11): provider/model abertos até M2-4; runtime não seleciona provider/model; `provider.generate` síncrono; non-streaming; retry automático zero; timeout explícito e finito; identidade de modelo resolvível; `requested_model` vs `resolved_model` observáveis; `request_id` fora de `RuntimeProvenance`; tamanho de resposta controlado localmente (Hermes `MAX_PROVIDER_RESPONSE_BYTES=8192`); validação M2-2 **obrigatória** e local; sem tools/memória/escrita; egress minimizado (subject/provenance/FTP/IDs externos não saem).

O payload é mínimo: JSON de transporte com 4 campos (`headline`, `explanation`, `next_action_text`, `caution_text|null`) gerado a partir de View projetada (M2-1). Prioriza **seguimento estrito de instrução + JSON estrito**, baixo custo/latência, simplicidade e reversibilidade.

## Drivers de decisão

1. **Compatibilidade com contrato Hermes**: `InsightModelProvider` + `InsightModelResponse` (text, provider, requested_model, resolved_model, request_id). `RuntimeProvenance.from_execution` exige que `response.requested_model == request.requested_model` (echo).
2. **Structured output estrito**: precisa emitir JSON estrito com schema fechado; `additionalProperties:false` preferencial. Validação **local M2-2** permanece mandatória (não substitui grounding/`Nd`).
3. **Sem tools / non-streaming / single attempt**: fácil de garantir; `tool_choice:none`/omitir tools; `stream:false` (default). Retry automático SDK = 0.
4. **Timeout explícito e finito**: SDK deve permitir timeout por request (float/Timeout). Default SDK não é autoridade.
5. **Identidade de modelo**: preferir **snapshot versionado** (datado/pinned) para reprodutibilidade; `model`/`modelVersion` devem expor resolved model quando possível.
6. **Privacidade/retention**: API data training **não usado por padrão** (pelo menos em tier comercial/API relevante), retention mínima; `store:false` desejável para reduzir retenção de estado de resposta.
7. **Custo/latência**: modelo pequeno/barato (nano/lite) suficiente para 4 campos curtos; sem pagar por reasoning não necessário.
8. **Contenção de vendor types**: SDK vs HTTP — SDK aceitável se tipos vendor não escapam do adapter M2-5 (boundary único).

## Candidatos pesquisados (fontes oficiais)

Foram consultados documentos oficiais (2026-10-16): OpenAI (platform.openai.com/developers.openai.com), Anthropic (platform.claude.com), Gemini (ai.google.dev). Ver relatórios de pesquisa anexados à sessão.

## Matriz comparativa (critérios obrigatórios)

| Critério | OpenAI (gpt-5.4-nano-2026-03-17) | Anthropic (claude-haiku-5-5) | Gemini (gemini-3.5-flash-lite) | Peso |
|---|---|---|---|---|
| Structured output estrito (json_schema/response_format/output_config) | **PASS** (Responses `text.format` json_schema + `strict:true`) | **PASS** (`output_config.format` json_schema; subset com `additionalProperties:false`) | **PASS** (`responseMimeType: application/json` + `responseSchema`) | alto |
| Sem tools garantido | **PASS** (omitir `tools` ou `tool_choice:"none"`) | **PASS** (omitir `tools` ou `tool_choice:{"type":"none"}`) | **PASS** (não incluir tools/functionCallingConfig) | alto |
| Non-streaming (default) | **PASS** (`stream` opt-in, default false) | **PASS** (`stream` opt-in) | **PASS** (`stream` opt-in, default false) | alto |
| Retry automático desabilitável | **PASS** (SDK `max_retries=0` desabilita; retries 2 por default) | **PASS** (SDK `max_retries=0` desabilita; retries 2 por default) | **PASS** (SDK `HttpRetryOptions.attempts==1` → sem retries; default 5) | alto |
| Timeout explícito finito | **PASS** (SDK `timeout` float/Timeout; default 10min — **sobrescrever obrigatório**) | **PASS** (SDK `timeout` float/Timeout; default 10min — **sobrescrever obrigatório**) | **PASS** (`HttpOptions.timeout` ms; opcional — **sobrescrever obrigatório**) | alto |
| Modelo com snapshot versionado | **PASS** (`gpt-5.4-nano-2026-03-17` datado/pinned) | **PARCIAL** (`claude-haiku-5-5` dateless ID é snapshot pinned (4.6+), mas sem data explícita; `claude-haiku-4-5-20251001` tem data) | **PASS** (modelo estável com ID exato; aliases existem) | alto |
| requested/resolved model observável | **PASS** (response `model` ecoa/retorna ID usado; `modelVersion` não garantido no Responses) | **PASS** (response `model` ecoa ID resolvido; snapshots 4.6+ são pinned) | **PASS** (response `modelVersion` + `responseId`) | alto |
| request_id disponível | **PASS** (HTTP `x-request-id`, response `id`) | **PASS** (HTTP `request-id`, error/response) | **PASS** (response `responseId`) | alto |
| usage metadata disponível | **PASS** (`usage.input_tokens/output_tokens/cached_*`) | **PASS** (`usage.input_tokens/output_tokens/cache_*`) | **PASS** (`usageMetadata.*`) | médio |
| Preço (input/output 1M, padrão) | $0.20 / $1.25 (gpt-5.4-nano-2026-03-17) | $0.10 / $0.50 (até 100K input; acima sobe) | $0.30 / $2.50 (gemini-3.5-flash-lite) | médio |
| Latência | baixa (nano/fast) | muito baixa (Haiku) | baixa (Flash-Lite) | médio |
| Privacidade/retention (treinamento off por padrão, ZDR/controle) | **PASS** (API data não usado p/treino por padrão; `store:false` disponível; abuso 30d; ZDR com elegibilidade) | **PASS** (commercial API: não treina em Customer Content; ZDR elegível p/ org, com limitações) | **PASS** (tier pago retém até 55d default, `store:false` possível; configurações por tier) | alto |

## Decisão

**Provedor selecionado:** `openai`
**Provider internal id:** `openai`
**Requested model (exato, versionado/pinned):** `gpt-5.4-nano-2026-03-17`
**Model family:** GPT-5.4 Nano (snapshot datado)

**SDK vs HTTP:** **SDK** (`openai-python`, oficial). O SDK cobre timeout/retries, headers `x-request-id`, tipos de erro normalizáveis e `text.format` strict. O adapter M2-5 irá **conter** quaisquer tipos de vendor dentro do boundary (não atravessar Protocol).

**Parâmetros operacionais (M2-5):**
- `streaming`: `false` (não-streaming)
- `automatic retries`: `0` (`max_retries=0`)
- `timeout seconds`: `30.0` (finito, explícito; sobrescreve default 10min). Avaliar ajuste futuro se necessário.
- `structured output`: `text.format` tipo `json_schema`, `strict: true`, schema fechado do transporte (4 campos), `additionalProperties:false`. **Local M2-2 validation permanece mandatória**.
- `temperature`: não especificar (ou omitir). `gpt-5.4-nano-2026-03-17` aceita `temperature` apenas com `reasoning.effort = none` (default `none`); para máxima simplicidade e evitar variação, **omitir sampling params**.
- `max_output_tokens`: valor conservador suficiente para `MAX_PRESENTATION_TOTAL_BYTES=4096` + overhead JSON (definir em M2-5, com base empírica; não hardcoded neste ADR).
- `tools`: **nenhum** (omitir array). `tool_choice`: não enviado.
- `store`: `false` (reduzir retenção de estado de resposta quando suportado pela chamada).
- `instructions`: usar o `input_text` canônico do M2-1 (único input). Não reescrever semanticamente; `prompt_sha256` continua sobre `input_text` exato.

**Identidade/modelo observável:** response `model` deve ecoar/retornar o ID usado; `request_id` = `response.id` (ou `x-request-id`). `resolved_model` no `InsightModelResponse` será preenchido a partir desse valor (ou `None` apenas se estritamente indisponível, mas preferível sempre preencher).

**Privacidade/retention (documentado):** API data training **desligado por padrão** para uso via API comercial; `store:false` reduz retenção; abuso monitoring até 30d por padrão (conforme docs oficiais). Zero Data Retention requer elegibilidade/approvação — **não assumido** para rollout inicial. Hermes envia **apenas** projeção minimizada (sem subject/provenance/FTP/IDs externos); external fact allowlist permanece **vazia**.

**Mapping de falhas (conceitual M2-5):** auth (401) → `InsightProviderAuthError`; rate limit (429) → `InsightProviderRateLimitError` (retryable conforme taxonomy); timeout (APITimeoutError/504-like) → `InsightProviderTimeoutError`; indisponibilidade/5xx → `InsightProviderUnavailableError`; resposta inválida/parse/schema → `InsightProviderInvalidResponseError`; demais → `InsightProviderError`. Classificações seguem taxonomy existente (não retryable por default; runtime não re-tenta).

## Alternativas rejeitadas

- **Anthropic `claude-haiku-5-5`**: muito bom custo/latência. Rejeitado por: modelo dateless (pinned mas sem data explícita no ID) dificulta auditoria/reprodutibilidade de snapshot; `temperature` deprecated/limitado em modelos recentes (risco de compatibilidade futura); necessidade de `output_config.format` com subset mais restrito em alguns casos. Ainda viável futuramente.
- **Gemini `gemini-3.5-flash-lite`**: sólido. Rejeitado por: custo output ligeiramente superior e configuração de retries SDK (`attempts==1` coerção) menos direta; retenção default por tier ligeiramente mais longa. Viável futuramente.

A escolha de **snapshot datado** (`gpt-5.4-nano-2026-03-17`) pesa mais que pequena diferença de custo para este gate (reprodutibilidade/auditabilidade).

## Consequências

**Positivas:**
- Snapshot versionado explícito → reprodutibilidade/auditabilidade (prompt_sha256 + requested_model fixo).
- Responses API + `strict:true` alinha bem com seam M2-2 (texto bruto JSON passa pelo decoder estrito).
- SDK com `max_retries=0`, timeout explícito e `x-request-id`/`id` facilita mapeamento a taxonomy e `request_id` (fora de provenance).
- Custo/latência adequados para uso pontual (insight por sessão/decisão), sem tools desnecessários.

**Negativas:**
- `store:false` pode não estar disponível em todos cenários (ZDR não assumido) — comportamento de retenção precisa ser verificado em M2-5 (sem alterar contrato).
- `gpt-5.4-nano` tem regras de sampling específicas (temperatura só com effort none) — **omitir params** evita esse ponto de fragilidade.

## Reversibilidade

A decisão é **nível adapter** (M2-5). `InsightView`/builder/validator/runtime/result **não** mudam. Troca de provider/model é reversível (apenas novo adapter + wiring), desde que respeite Protocol e M2-2. Critérios de substituição futuros: deprecação do snapshot, regressão de latência/custo, compliance de formato/grounding, confiabilidade ou mudança de política de privacidade/retention.

## Fontes (oficiais)

- OpenAI Pricing/Models/Structured Outputs/Responses API/Errors/Your Data: platform.openai.com/developers.openai.com (acesso 2026-10-16)
- Anthropic Models/Pricing/Messages API/Structured Outputs/API Errors/Data Retention: platform.claude.com (acesso 2026-10-16)
- Gemini API Models/Pricing/Structured Outputs/Interactions/Errors/Logs/Terms: ai.google.dev (acesso 2026-10-16)

## Follow-up (M2-5)

Implementar adapter `OpenAIInsightProvider` (único local de rede/auth), mapear erros exatos, configurar `timeout=30.0`, `max_retries=0`, `stream=false`, `store:false` (quando aplicável), converter response → `InsightModelResponse` (preenchendo `resolved_model` e `request_id`), validar boundary (sem tipos vendor escaparem), e adicionar testes offline com FakeProvider (já existentes) + smoke offline do adapter. Não iniciar M2-6 ainda.

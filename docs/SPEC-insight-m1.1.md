# INSIGHT M1.1 — Runtime Hardening Contract

**Status: SPEC READY / IMPLEMENTATION NOT STARTED.**

M1.1 fecha exclusivamente `INSIGHT2-AUD-03` (limites de tamanho) e
`INSIGHT3-AUD-01` (consistência request/provenance). É pré-requisito de qualquer
runtime online do M2, mas não adiciona provider concreto, modelo, rede, prompt
semântico, invocation runtime ou feature habilitada.

## 1. Invariantes e non-goals

M1.1 preserva a ordem de autoridade:

```text
observed > derived > heuristic > advice > prescription > InsightPresentation
```

Erros de tamanho ou provenance só impedem a geração de `InsightPresentation`.
Nunca criam ou alteram Advice, Policy, Prescription, FTP, readiness,
progression, lifecycle, plan, provider sync ou estado upstream.

Fora de escopo: provider/model selection, credenciais, chamadas de rede,
allowlist de facts externos, conteúdo de prompt M2, tool/function calling,
memory, agent loop, mutation de domínio, confirmação/promoção de FTP e release.
`HERMES_INSIGHT_ENABLED` permanece default OFF.

## 2. Política central de tamanho

O futuro módulo `src/insight/limits.py` é a única fonte de verdade das
constantes. `contract.py`, `render.py`, `serialization.py` e
`model_provider.py` importam essas constantes; não declaram cópias locais.

Todos os valores são **operational safety limits**, não thresholds fisiológicos,
de treino ou médicos. Protegem memória, serialização, input/output de modelo e
previsibilidade de validação.

### Unidades

- **COUNT** mede elementos da coleção.
- **CHARACTER** mede `len(str)` e é reservado aos limites semânticos já públicos
  de textos da `InsightPresentation`.
- **BYTE** mede `len(value.encode("utf-8"))` e é obrigatório nas fronteiras de
  serialização, egress ou provider.

Não é permitido comparar caracteres com limite em bytes nem truncar para
satisfazer qualquer uma das unidades.

### Constantes congeladas

| Constante | Valor | Unidade | Boundary e rationale operacional |
|---|---:|---|---|
| `MAX_FACT_COUNT` | 32 | count | `InsightView`; o producer atual chega a ~13 facts, com margem >2x sem coleção aberta. |
| `MAX_PROVENANCE_COUNT` | 16 | count | `InsightView`; o producer atual tem até 3 fontes, com margem para views compostas. |
| `MAX_FACT_KEY_BYTES` | 64 | UTF-8 bytes | `InsightFact.key`; keys são identificadores estáticos machine-readable. |
| `MAX_FACT_STRING_VALUE_BYTES` | 512 | UTF-8 bytes | string `InsightFact.value`; permite estado textual curto, não payload. |
| `MAX_FACT_UNIT_BYTES` | 32 | UTF-8 bytes | `InsightFact.unit`; rótulo estrutural curto. |
| `MAX_INSIGHT_VIEW_BYTES` | 16_384 | UTF-8 bytes | serializer canônico; limita a view completa. |
| `MAX_MODEL_INPUT_BYTES` | 24_576 | UTF-8 bytes | `InsightModelRequest.input_text`; input pequeno e previsível, maior que a view para instruções versionadas. |
| `MAX_PROVIDER_RESPONSE_BYTES` | 8_192 | UTF-8 bytes | `InsightModelResponse.text`; resposta bruta limitada antes de parsing e menor que o input. |
| `MAX_PRESENTATION_TOTAL_BYTES` | 4_096 | UTF-8 bytes | Presentation canônica; limita a soma dos campos. |
| `MAX_HEADLINE_CHARS` | 240 | characters | limite público existente, preservado. |
| `MAX_EXPLANATION_CHARS` | 2_000 | characters | limite público existente, preservado. |
| `MAX_NEXT_ACTION_TEXT_CHARS` | 1_000 | characters | limite público existente, preservado. |
| `MAX_CAUTION_TEXT_CHARS` | 1_000 | characters | limite público existente, preservado. |
| `MAX_TEMPLATE_CHARS` | 2_000 | characters | limite público existente do renderer, preservado. |

`int` e `float` finito continuam aceitos conforme o contrato atual; M1.1 não cria
faixa fisiológica para magnitude numérica. Representação numérica excessiva é
barrada pelo orçamento serializado da view, não por policy de treino.

O contrato não tem grammar global para `InsightFact.key`; M1.1 preserva texto não
vazio e adiciona somente o limite em bytes. A grammar estática da `Application`
não é promovida silenciosamente a requisito global.

## 3. Serializer e enforcement

### 3.1 Objetos estruturais

`InsightFact` valida key, string value e unit em UTF-8 bytes. `InsightView`
valida `facts` e `provenance` pelos COUNT limits. A validação ocorre na
construção, antes de renderer ou provider.

Os limites individuais existentes da Presentation ficam em CHARACTER. Além deles,
`InsightPresentation` e `validate_presentation_payload()` validam o limite total
em bytes. Unicode pode caber no limite de caracteres e falhar corretamente no
limite total de bytes.

### 3.2 Serializer canônico de `InsightView`

O novo `src/insight/serialization.py` exportará:

```python
def serialize_insight_view(view: InsightView) -> bytes: ...
```

Ele retorna JSON UTF-8, sem pretty printing, produzido por:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

O payload é explícito, sem `asdict()` implícito:

```text
schema_version: integer
subject: string
facts: [{key, value, classification, unit}, ...]
advisory: null | {text}
prescribed_session: null | {summary}
observed_execution: null | {availability, summary}
provenance: [{name}, ...]
```

Tuples são arrays JSON; `None` é `null`; enums são seus valores; números usam a
representação JSON da stdlib para `int` e `float` finito. Não há locale, defaults
implícitos, metadata runtime/provider ou hash substituindo conteúdo. A ordem das
tuplas é preservada e a ordem de chaves é estável por `sort_keys=True`.

O serializer mede `len(result)` e lança erro tipado acima de
`MAX_INSIGHT_VIEW_BYTES`.

### 3.3 Boundary de modelo e renderer

- `InsightModelRequest.__post_init__` mede `input_text` em UTF-8 e rejeita acima
  de `MAX_MODEL_INPUT_BYTES`, antes de qualquer adapter futuro.
- `InsightModelResponse.__post_init__` mede `text` em UTF-8 e rejeita acima de
  `MAX_PROVIDER_RESPONSE_BYTES`. Adapter/runtime futuro deve aplicar esse
  orçamento ao receber bytes, antes de decode, JSON parsing, schema, grounding ou
  renderer.
- Renderer valida a Presentation final. Template pequeno que expanda além de um
  limite de campo ou total falha fechado; não corta saída.
- O total da Presentation é o tamanho do JSON canônico fechado
  `{headline, explanation, next_action_text, caution_text}`, com as opções da
  seção 3.2. Um helper interno pode implementar essa medição, mas esta é a
  definição normativa de `MAX_PRESENTATION_TOTAL_BYTES`.

## 4. Erros, observabilidade e fallback

`src/insight/limits.py` definirá:

```python
class InsightSizeLimitError(ValueError):
    limit_name: str
    actual_size: int
    max_size: int
```

O erro não armazena payload, prompt, resposta bruta, segredo ou valor ofensor
completo. Nomes normativos de `limit_name`:

```text
fact_count
provenance_count
fact_key_bytes
fact_string_value_bytes
fact_unit_bytes
serialized_view_bytes
model_input_bytes
provider_response_bytes
presentation_headline_characters
presentation_explanation_characters
presentation_next_action_characters
presentation_caution_characters
presentation_total_bytes
render_output_bytes
```

| Categoria | `limit_name` típico |
|---|---|
| `CONTRACT_OBJECT_OVERSIZED` | fact/provenance/key/value/unit ou campo estrutural |
| `SERIALIZED_VIEW_OVERSIZED` | `serialized_view_bytes` |
| `MODEL_INPUT_OVERSIZED` | `model_input_bytes` |
| `PROVIDER_RESPONSE_OVERSIZED` | `provider_response_bytes` |
| `RENDER_OUTPUT_OVERSIZED` | `render_output_bytes` ou campo excedido após expansão |
| `PRESENTATION_OVERSIZED` | `presentation_total_bytes` |

`SILENT_TRUNCATION` é **FORBIDDEN**. Não usar slicing ou repair silencioso para
tornar input, response ou Presentation válida.

O status conceitual é `SIZE_LIMIT_EXCEEDED`, com somente `limit_name`,
`actual_size`, `max_size` e `stage`; nunca conteúdo bruto.

Todo `InsightSizeLimitError` mapeia para `fallback_presentation(view)` no runtime
futuro. M1.1 não cria runtime: deve apenas permitir teste explícito
`erro tipado -> fallback determinístico` com o fallback existente. A falha não
altera View, Prescription, plan, lifecycle, FTP nem chama provider.

## 5. INSIGHT2-AUD-03 — matriz e saída

Para cada limite aplicável: `limit - 1` PASS, `limit` PASS, `limit + 1` FAIL.
Limites em bytes exigem Unicode multibyte.

| Boundary | Cobertura mínima |
|---|---|
| facts e provenance | count off-by-one |
| key, string value, unit | UTF-8/off-by-one e whitespace inválido preservado |
| serializer de View | bytes determinísticos, orçamento e sem NaN/Infinity |
| request input | UTF-8/off-by-one antes de provider |
| response raw | UTF-8/off-by-one antes de parsing |
| Presentation | limites individuais existentes e total canônico |
| renderer | expansão de template que excede orçamento |
| fallback/invariância | erro tipado, fallback estável, View/Prescription/plan/FTP/lifecycle imutáveis |

`INSIGHT2-AUD-03` só fecha com constantes centralizadas, serializer canônico,
enforcement em todos os boundaries, ausência de truncamento, erro tipado, testes
off-by-one/Unicode/fallback/invariância e suíte completa verde.

## 6. Request e provenance: uma fonte por invocation

### 6.1 Novo request e compatibilidade

O contrato futuro de `InsightModelRequest` é:

```python
@dataclass(frozen=True)
class InsightModelRequest:
    prompt_version: str
    prompt_sha256: str
    requested_model: str
    input_text: str
    schema_version: int
```

`requested_model` é obrigatório e identifica alias/configuração solicitada pela
composition layer. Pode ser alias; não afirma identidade imutável e não precisa
ser igual ao modelo efetivamente resolvido.

Isso é uma **BREAKING API CHANGE: YES**. `InsightModelRequest` é exportado por
`src.insight.__init__`; não haverá default inventado. Não há consumidor produtivo
atual fora dos testes, portanto a mudança é aceita em M1.1. O prompt builder
futuro calcula `prompt_sha256` sobre os bytes efetivamente usados; M1.1 não cria
builder nem conteúdo de prompt.

### 6.2 Ownership de response e runtime

`InsightModelResponse` continua sendo observação do adapter/runtime:

```text
text             -> resposta bruta limitada
provider         -> provider efetivo
requested_model  -> echo verificável do adapter
resolved_model   -> identidade/modelo efetivamente reportado, opcional
request_id       -> identificador observado opcional
```

Provider não pertence ao request de domínio. `resolved_model` pertence à resposta
observada e pode diferir de `requested_model`. O echo de requested model fica na
response apenas para verificação: se divergir do request, falha fechada.

### 6.3 Factory canônica

`InsightRuntimeProvenance` continua frozen, mas construção direta deixa de ser
API suportada. A implementação deve torná-la indisponível para construção normal
(`dataclass(..., init=False)` ou mecanismo equivalente simples), deixando esta
factory como caminho público único:

```python
@classmethod
def from_execution(
    cls,
    request: InsightModelRequest,
    response: InsightModelResponse,
    *,
    executed_at: datetime,
    harness_version: str | None = None,
    harness_commit: str | None = None,
) -> "InsightRuntimeProvenance": ...
```

| Campo provenance | Fonte única |
|---|---|
| `prompt_version` | `request.prompt_version` |
| `prompt_sha256` | `request.prompt_sha256` |
| `requested_model` | `request.requested_model` |
| `provider` | `response.provider` |
| `resolved_model` | `response.resolved_model` |
| `executed_at` | argumento injetado da composition/runtime layer |
| `harness_version` | argumento runtime/build |
| `harness_commit` | argumento runtime/build |

A factory valida `response.requested_model == request.requested_model`. Não há
argumento duplicado para metadata compartilhada.

`executed_at` passa a ser `datetime` timezone-aware no contrato de provenance;
serialização/observabilidade futura usa ISO-8601. Datetime naive falha.
`datetime.now()` é proibido no contrato/factory. `harness_commit` permanece hex
lowercase de 7–64 chars; `harness_version` continua texto não vazio quando existe.

### 6.4 Falha de provenance

`src/insight/model_provider.py` definirá:

```python
class InsightProvenanceError(ValueError):
    code: str
```

Mismatch request/response usa `code = "requested_model_mismatch"`. Não é
`InsightProviderError`: é inconsistência local de contrato. `SILENT_RECONCILIATION`
é **FORBIDDEN**; nunca preferir request ou response silenciosamente. Runtime futuro
converte esse erro em fallback determinístico, sem mutação de domínio.

## 7. INSIGHT3-AUD-01 — matriz e saída

| Caso | Resultado esperado |
|---|---|
| request/response coerentes | provenance válida e frozen |
| prompt version/hash | derivadas do request, sem segundo argumento editável |
| echo requested model igual | PASS |
| echo requested model diferente | `InsightProvenanceError(requested_model_mismatch)` |
| resolved diferente do requested | PASS |
| provider | vem somente da response |
| `executed_at` aware injetado | PASS |
| `executed_at` naive | FAIL |
| harness version/commit válidos | PASS |
| metadata harness inválida | FAIL |
| mesmas entradas | igualdade determinística |
| arquitetura | sem env, SDK, HTTP, clock escondido ou imports de domínio |

`INSIGHT3-AUD-01` só fecha quando requested model pertence ao request, metadata
compartilhada é derivada pela factory, mismatch não é silencioso,
requested/resolved permanecem distintos, timestamp é injetado, não há env/SDK/
clock oculto, os testes acima e a suíte completa estão verdes.

## 8. Gates de implementação

### M1.1-A — SIZE_LIMITS

Fecha somente `INSIGHT2-AUD-03`.

```text
novo      src/insight/limits.py
novo      src/insight/serialization.py
modificar src/insight/contract.py
modificar src/insight/render.py
modificar src/insight/model_provider.py
modificar src/insight/__init__.py
novo      tests/test_insight_limits.py
modificar tests/test_insight_contract_v2.py
modificar tests/test_insight_render.py
modificar tests/test_insight_model_provider.py
```

### M1.1-B — REQUEST_PROVENANCE

Começa somente após review, audit, push e CI de A. Fecha somente
`INSIGHT3-AUD-01`.

```text
modificar src/insight/model_provider.py
modificar src/insight/__init__.py
modificar tests/test_insight_model_provider.py
```

Teste dedicado de provenance é aceitável apenas se melhorar isolamento. Nenhum
gate altera `src/application.py`, CLI, dataset de eval ou workflow sem evidência
nova. A e B exigem review, auditoria e CI próprios; não são um único commit.

Quando ambos fecharem, M1.1 desbloqueia somente gates de design/implementação do
M2. Isso não seleciona provider/model, não implementa runtime online, não habilita
feature e não cria release.

Baseline informativo desta SPEC: 55 testes focais de Insight e 1586 na suíte
completa; essas contagens não são contrato permanente.

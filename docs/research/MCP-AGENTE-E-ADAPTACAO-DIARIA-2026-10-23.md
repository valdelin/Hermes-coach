# MCP, agente hospedado e adaptação diária — modelos para o Hermes — 2026-10-23

> [!info] Dono deste documento
> Fonte canônica: `docs/research/MCP-AGENTE-E-ADAPTACAO-DIARIA-2026-10-23.md` **no repo**
> (o mesmo arquivo do vault é cópia). Quando divergirem, o repo vence. Editar no repo e copiar.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/MCP-AGENTE-E-ADAPTACAO-DIARIA-2026-10-23.md`.

## Contexto

Este documento responde ao feedback do operador sobre o dossiê
`PROVA-ENDURANCE-ANALISE-COMPARATIVO-HERMES-2026-10-22.md`. A lista de “o que o Prova faz
melhor” foi revisada ponto a ponto, mas com uma separação explícita:

| Ponto do Prova | Status para o Hermes | Encaminhamento |
|---|---|---|
| Proveniência por sessão/regra e aba Coach | **Aprovado como direção** | Especificar `DecisionRecord`/`RuleRef` antes de qualquer UI |
| Aprovação como estado (“Waiting/Accept/Decline”) | **Hipótese** | Só faz sentido com adaptação diária; testar antes de construir |
| Onboarding via MCP no app de IA do usuário | **A estudar** | O modelo desejado é plataforma/agente, não o LLM do usuário; comparar modelos |
| Alcance `.fit`/Intervals/Garmin/Wahoo/Hammerhead | **Correção factual** | O Intervals já entrega `.fit`, `.zwo`, `.erg`, `.JSON` e `.MRC` |
| Servidor próprio no Brasil | **Correção de horizonte** | Local-first hoje; servidor próprio é roadmap, não estado permanente |

Este documento não implementa nada. Ele fixa vocabulário, contratos e critérios de decisão para
que a implementação não comece pelo transporte (MCP) nem pela UI (Coach tab) antes do contrato de
dados.

## 1. Proveniência no produto — aprovado como direção

O Prova mostra, por sessão, a fonte científica ou uma nota de julgamento; a aba Coach registra
propostas, decisões, e-mails e chamadas de ferramenta. O Hermes já tem a matéria-prima na §15 do
`docs/EMBASAMENTO-CIENTIFICO.md` (matriz de rastreabilidade por feature), mas ela é documentação,
não um contrato de runtime.

### Contrato mínimo

`RuleRef` é o catálogo versionado; `DecisionRecord` é o snapshot imutável do que foi aplicado.

```text
RuleRef
  rule_id: string
  rule_kind: evidence | heuristic | model
  source_id: DOI/PMID | JUDGMENT | NONE
  source_note: string | null
  scope: plan | week | session | readiness | ftp
  feature: string
  version: integer

DecisionRecord
  decision_id: string
  created_at: ISO-8601
  actor: engine | agent | user
  scope: plan | week | session | readiness | ftp
  rule_id: string
  rule_kind: evidence | heuristic | model
  source_id: DOI/PMID | JUDGMENT | NONE
  source_note: string | null      # o que a fonte NÃO mostra, quando evidence
  model_name: string | null       # obrigatório quando rule_kind=model (ex.: PMC-EWMA)
  inputs: object                  # dados normalizados que entraram
  outcome: object                 # o que foi decidido
  reason: string                  # explicação curta, em linguagem de atleta
  confidence: number | null
  plan_hash: string | null        # versão do plano à qual a decisão se aplica
  parent_decision_id: string | null
  supersedes: string | null       # correção append-only de um registro anterior
```

`DecisionRecord` repete `rule_kind`/`source_id`/`source_note` de propósito: se a regra for
revisada, o registro antigo continua contando a história que foi aplicada. O `rule_id` aponta
para o `RuleRef` atual; o snapshot preserva o passado.

Regras de integridade:

- `rule_kind=evidence` exige `source_id` verificável e `source_note` com a ressalva da §15.
- `rule_kind=heuristic` exige `source_id=JUDGMENT` ou uma origem explícita (“produto”,
  “operador”), nunca um DOI que não sustenta a regra.
- `rule_kind=model` cobre fórmulas e aproximações computacionais (PMC, Banister, TSS, zonas);
  `source_id` pode ser `NONE` se a fórmula for interna, mas `model_name` é obrigatório.
- Toda sessão publicada tem pelo menos um `DecisionRecord`; toda mudança de plano tem um
  `parent_decision_id` que aponta para a decisão anterior.
- O ledger é **append-only**. Correção = novo registro com `supersedes`, não `UPDATE`.

### Onde persistir

- `plan.json` continua sendo o estado operacional do plano.
- O ledger fica em `decisions.jsonl` (ou tabela equivalente, se houver servidor), com
  `plan_hash` para amarrar a decisão à versão do plano.
- O `summary`/relatório lê o ledger; a futura aba Coach lê o mesmo ledger. Uma fonte, duas
  renderizações.

### Critério de aceite

- Nenhuma sessão publicada sem `DecisionRecord`.
- Nenhum `rule_kind=evidence` sem `source_id` e `source_note`.
- Nenhum `source_id` que não resolva no verificador de referências.
- Teste de regressão: para cada regra da §15, existe pelo menos um teste que crie um
  `DecisionRecord` e valide a integridade.

Isso é a productização da §15. Não é uma feature de UI; é o contrato que permite a UI.

## 2. Aprovação como estado — hipótese, não decisão

A intuição do operador está correta em um ponto importante: **o valor de “Waiting for you /
Accept/Decline” depende da frequência com que o sistema muda o treino**. Em uma agenda semanal
estável, um fluxo de aprovação por sessão vira burocracia. Em um sistema que muda o treino
diariamente, o estado de aprovação passa a ser o mecanismo de controle do atleta.

Mas há uma distinção que o Prova mistura e que o Hermes deve separar:

| Camada | O que é | Frequência | Quem aprova |
|---|---|---|---|
| **Plano** | Bloco/semana com foco, TSS, sessões e restrições | Semanal ou por bloco | Atleta, uma vez por versão |
| **Ajuste diário** | Mudança na sessão de hoje por prontidão/execução | Diária | Automático dentro de um envelope; proposta fora dele |
| **Mutação de plano** | Troca de foco, redistribuição de carga, taper | Eventual | Atleta, com diff e veredito |

Pelo que a página descreve, o Prova aprova o plano e auto-aplica a semana seguinte; o
“Accept/Decline” aparece no ciclo de proposta/mutação do plano, não como aprovação de cada
sessão. O Hermes já tem `build` (plano) e `check` (ajuste do dia) separados; o que falta é o
**contrato de envelope** e o **ledger**.

### Modelo de dois níveis

**Nível 1 — plano aprovado.** O atleta aprova uma versão do plano com restrições duras:
orçamento de TSS, pisos de zona, espaçamento de sessões duras, semana de recuperação, taper.
Essas restrições não são negociadas pelo agente.

**Nível 2 — ajuste diário dentro do envelope.** O motor pode, sem nova aprovação:

- reduzir volume até um limite (ex.: −20%);
- trocar uma sessão de qualidade por recuperação;
- mover uma sessão dentro da janela permitida;
- manter a sessão e apenas registrar o sinal.

Fora do envelope — aumentar carga, empilhar sessões duras, mexer em taper, mudar foco — o motor
**propõe** e o atleta aprova. Toda ação, automática ou aprovada, gera `DecisionRecord`.

### Por que não aprovar tudo diariamente

- **Ruído:** RHR/HRV são sinais com erro de medida; uma leitura isolada não deveria disparar
  mudança. O Prova usa média multi-dia; o Hermes hoje pode reagir a um sinal isolado (como
  proposta). O envelope precisa de janela e limiar de mudança.
- **Fricção:** Accept/Decline diário reduz aderência. A aprovação deve ser reservada para
  decisões de maior consequência.
- **Compromisso:** o plano semanal é um compromisso; mudanças diárias ilimitadas o dissolvem.
- **Auditoria:** o ledger é independente de aprovação. Mesmo o ajuste automático fica rastreável.

### Experimento para testar a hipótese

Não construir um motor diário completo antes de medir. Protocolo mínimo:

- **Condições:** (A) plano semanal + `check` diário como proposta; (B) plano semanal + ajuste
  diário automático dentro do envelope.
- **Desenho:** N-of-1 primeiro, 8–12 semanas, com washout; depois pequeno paralelo se houver
  base de atletas. Randomizar a ordem no N-of-1.
- **Métricas:** aderência, conclusão das sessões, RPE, wellness, progressão de carga,
  espaçamento de sessões duras, lesão/doença, confiança declarada, tempo até ajuste.
- **Guardrails:** nenhum piso de zona violado; nenhuma sessão dura empilhada; nenhuma
  compensação de sessão perdida com volume; nenhuma mutação sem ledger.
- **Hipótese nula:** o ajuste diário não melhora aderência/resultado o suficiente para justificar
  a complexidade e a perda de compromisso semanal.

Critério de decisão: só promover o ajuste diário a “automático por padrão” se ele ganhar em
aderência **sem** piorar segurança/estabilidade de carga. Caso contrário, manter o modelo de
proposta.

## 3. MCP e o agente — a estudar

### O que o MCP é (e não é)

MCP (Model Context Protocol) é um protocolo JSON-RPC entre um **host/cliente** (app de IA ou
agente) e um **servidor** que expõe ferramentas, recursos e prompts. O MCP **não roda o modelo**.
Quem raciocina é o host; o servidor só executa ferramentas e devolve dados. Em HTTP, o servidor
pode exigir OAuth 2.1 com discovery, DCR e PKCE.

Isso separa duas decisões que o Prova junta:

1. **Quem roda o host/LLM:** o usuário (BYO-AI) ou a plataforma (agente hospedado).
2. **Quem paga a inferência:** o usuário ou a plataforma.

### Três modelos

| Modelo | Quem roda o host/LLM | Quem paga | Onboarding | Dados | Risco principal |
|---|---|---|---|---|---|
| **A. BYO-AI** (Prova) | App do usuário (Claude, ChatGPT, Gemini, Le Chat) | Usuário | Cola URL MCP + OAuth | Vão ao provedor de IA escolhido | Dependência de menus/capacidades de terceiros; UX fragmentada |
| **B. Agente hospedado** | Plataforma (servidor ou app desktop) | Plataforma | Login + OAuth no Intervals | Ficam no servidor da plataforma + provedor do LLM | Custo de inferência, chave de API, prompt injection, retenção |
| **C. Híbrido** | Plataforma por padrão; cliente externo opcional | Plataforma + usuário | Login; MCP opcional | Dois caminhos | Duas superfícies para segurar/testar; auditoria por ator |

**Ponto central:** no modelo B, o MCP é **opcional**. O agente hospedado pode chamar as mesmas
ferramentas por function calling ou RPC interno. O MCP é uma decisão de **distribuição/integração**
(permitir que Claude/ChatGPT acessem o Hermes), não um requisito de arquitetura. O contrato que
importa é o das ferramentas, não o transporte.

### Contrato de ferramentas (independente do transporte)

```text
get_athlete_context()          -> perfil, thresholds, histórico, wellness, restrições
get_plan(scope)                -> plano atual + versão/hash
get_rules()                    -> catálogo de regras com kind/source/scope
propose_change(diff, reason)   -> ProposedChange + rule_verdicts
validate_change(proposal_id)   -> veredito + violações
apply_change(proposal_id)      -> grava no plano (não publica)
push(scope)                    -> publica no Intervals (ação explícita)
get_activity(id)               -> atividade pareada + análise
```

O agente (hospedado ou externo) **propõe**; o motor **valida e grava**. O `push` é sempre uma
ação separada e auditada.

### O que muda no onboarding

**BYO-AI:** o usuário precisa de um app com conector MCP; adiciona a URL, passa pelo OAuth,
seleciona ferramentas. O Hermes precisa de OAuth 2.1 + DCR + PKCE, grants por conexão, rotação de
refresh token, escopos, revogação e audit log. O bug do Prova (refresh token single-use
compartilhado entre sessão web e app de IA) é o caso de teste.

**Agente hospedado:** o usuário faz login, conecta o Intervals via OAuth e conversa. Não há
conector MCP. O Hermes precisa de autenticação de usuário, sessão, chave de LLM, limites de
custo/rate, proteção contra prompt injection vindo de atividades/notas, retenção e subprocessores
do provedor de modelo.

**Híbrido:** os dois; o `DecisionRecord.actor` distingue `engine`, `agent` e `user`, e o audit
distingue `connection_id` (cliente externo) de sessão da plataforma.

### Critério de decisão

Antes de escolher A/B/C, responder:

1. O produto exige que o atleta use Claude/ChatGPT, ou o Hermes deve prover a conversa?
2. Quem paga a inferência e qual é o custo por atleta ativo/mês?
3. O Hermes aceita processar saúde no provedor de LLM? Com qual DPA/região?
4. O diferencial é o motor determinístico (forte no B) ou a distribuição via apps de IA (forte no A)?
5. Há base para arcar com evals, rate limits e suporte de um agente hospedado?

Recomendação condicional: **definir o contrato de ferramentas e o ledger primeiro**. Se a decisão
for prover a conversa dentro do produto, o agente hospedado é o primeiro host; expor MCP fica para
depois, se houver demanda de clientes externos. Isso preserva o motor como fonte de verdade e evita
começar pelo transporte.

## 4. Correções factuais

### 4.1 Formatos do Intervals

O Intervals.icu disponibiliza `.fit`, `.zwo`, `.erg`, `.JSON` e `.MRC` para treinos planejados.
O Hermes **depende do Intervals** para esses formatos; não gera localmente. Portanto:

- a comparação não deve dizer “Hermes sem `.fit`”; deve dizer “Hermes sem geração local; o
  Intervals entrega `.fit`/`.zwo`/`.erg`/`.JSON`/`.MRC`”;
- o gap real é **independência de dispositivo/ecossistema**, não ausência de formato;
- se o atleta usa Intervals, o `.fit` já está resolvido; se não usa, a geração local passa a ter
  valor.

### 4.2 Servidor próprio

O Hermes é local-first **hoje**. “Servidor próprio” é um horizonte de roadmap, não uma promessa
de arquitetura permanente. Quando o servidor existir, o modelo de privacidade muda:

- autenticação de usuário e isolamento entre atletas;
- criptografia em trânsito e em repouso;
- retenção, exclusão e backups com prazo definido;
- subprocessores (LLM, e-mail, pagamento) e DPAs;
- LGPD/GDPR, incident response e audit log;
- se o agente for hospedado, custo de inferência e limites por usuário.

A comparação deve dizer “local-first hoje; servidor próprio no roadmap”, não “local-first por
definição”.

## 5. Decisões e próximos passos

| Item | Status | Próximo artefato |
|---|---|---|
| Proveniência por decisão (`DecisionRecord`/`RuleRef`) | **Aprovado como direção** | Spec do ledger + testes de integridade |
| Aprovação como estado | **Hipótese** | Protocolo do experimento A/B (acima) |
| MCP no app do usuário | **A estudar** | Matriz de custo/segurança A/B/C |
| Intervals `.fit`/`.zwo`/`.erg`/`.JSON`/`.MRC` | **Corrigido** | Ajuste no dossiê do Prova |
| Servidor próprio | **Roadmap** | Atualizar comparação de privacidade |

O que **não** fazer agora:

- não implementar MCP antes do contrato de ferramentas;
- não construir uma aba Coach antes do ledger;
- não trocar o motor determinístico por um LLM como autor;
- não prometer adaptação diária sem experimento;
- não tratar “local-first” como argumento permanente se o servidor próprio é o plano.

## 6. Fontes

- **[D]** `docs/research/PROVA-ENDURANCE-ANALISE-COMPARATIVO-HERMES-2026-10-22.md` — dossiê do
  Prova, especialmente “O que o Prova faz melhor”, MCP/OAuth, integrações e privacidade.
- **[H1]** `README.md` — `build`, `check`, `apply`, `push`, automação diária, readiness.
- **[H2]** `AGENTS.md` — fonte de verdade, separação evidência/heurística/modelo, guardrails.
- **[H3]** `docs/EMBASAMENTO-CIENTIFICO.md` — §15 (matriz de rastreabilidade) e §16 (referências).
- **[H4]** `docs/ROADMAP.md` — #13 (MCP/apps), #29 (Coach+), #23–#26 (portal/banco/API/workers),
  #18/#30 (multi-esporte).
- **[O]** Feedback do operador, 2026-10-23: proveniência aprovada; aprovação como hipótese ligada
  à adaptação diária; MCP com LLM da plataforma/agente, não do usuário; correção dos formatos do
  Intervals; servidor próprio no horizonte.

# evals — o lado do app

O dataset e o contrato vivem **no repo do app** (o dado é do app); o runner e o
método vivem no harness compartilhado (`~/Work/lab/ai-lab`, ou o secret
`AI_LAB_REPO` quando o CI rodar de verdade). O prompt nunca é um grader: o que dá
para verificar sem LLM é invariante do harness.

Rodar: `~/Work/lab/ai-lab/check.sh ~/Work/lab/cycling-coach cycling-coach` — offline,
sem chave de API.

## Regras de isolamento (o core determinístico é o ativo de segurança)

O `cycling-coach` decide treino por números auditáveis, com 374 testes. O `insight`
**enriquece**, nunca decide:

1. `src/insight` **não é importado** por `decide_focus`/`build`/`reconcile`/`push` —
   nada do fluxo diário pode depender do LLM para decidir.
2. Feature flag desligada por padrão (`COACH_INSIGHT=0`); ligar é ato explícito.
3. Dependência do provider opcional e separada; o venv do agente funciona sem ela.
4. Job de CI de evals **separado** (nightly), fora do gate do build/daily.
5. Toda falha de LLM → **fallback determinístico**. Insight é *enriquecimento*.

## Dataset

`cases.jsonl`, uma linha por caso:

- `contexto` — só o que o motor decidiu (vira o `InsightContext`).
- `esperado` — saída boa: tem que passar em **todos** os graders.
- `contra` — um contra-exemplo por grader: saída que aquele grader existe para
  rejeitar. Grader que reprova o `esperado` é regressão; grader que aceita o seu
  `contra` não discrimina.

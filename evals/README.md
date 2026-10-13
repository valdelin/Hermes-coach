# INSIGHT evals

O Hermes possui o dataset (`cases.jsonl`) e os graders de domínio (`graders.py`).
Eles verificam G1–G7: schema, campos prescritivos, contradição controlada,
grounding controlado, provenance de caution, fallback e invariância.

G3 usa markers sintéticos declarados pelo caso; G4 valida apenas metadata
`used_fact_keys` contra facts autorizados. Nenhum dos dois interpreta texto livre
como NLP ou cria uma nova policy fisiológica.

Rode offline: `python3 scripts/run_insight_evals.py --self-test`.

Status: `PASS`, `FAIL`, `SKIPPED` e `INFRA_ERROR`; os dois últimos nunca são
sinônimos de `PASS`. O CI core não executa eval online. Runner externo genérico
não está integrado até haver pin imutável confiável.

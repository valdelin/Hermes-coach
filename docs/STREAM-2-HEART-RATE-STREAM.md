# STREAM-2 — Heart Rate Stream Confirmation + Temporal Alignment

> Dono: **repo** (`docs/STREAM-2-HEART-RATE-STREAM.md`).
> Status: **DONE**. Normaliza stream temporal de FC; não calcula Pw:HR.

## Evidência

Fontes primárias confirmam `heartrate` como stream armazenado do Intervals e
`fixed_heartrate` como variante corrigida/calculada. STREAM-2B consultou três
VirtualRides históricas sanitizadas. Em todas, `time`, `watts` e `heartrate`
`moving_time`; a média de FC da série arredondou para `average_heartrate` do
resumo. Isso sustenta empiricamente bpm e alinhamento por índice, embora a
OpenAPI não prometa ambos universalmente.

O relatório, fontes e matriz estão em
`docs/research/STREAM-2-INTERVALS-HR-STREAM.md`. A fixture
`tests/fixtures/activity_streams_time_watts_heartrate.json` retém somente shape
`{type,data}`, comprimentos integrais e sete índices distribuídos, sem IDs,

## Boundary

`IntervalsAdapter` requisita explicitamente `("time", "watts", "heartrate")`
`ActivityStreamPoint(elapsed_seconds, power, heart_rate)`. A nova capability
`READ_HEART_RATE_STREAM` declara suporte de FC temporal; `fixed_heartrate` não
é requisitado nem tratado como alias.

Se `heartrate` vier com comprimento diferente de `time`, retorna
`heart_rate_length_mismatch` e não emite pontos. Não há truncamento, zip parcial,

`activity_streams.json` serializa HR normalmente; caches STREAM-1 sem o campo
continuam carregando com `heart_rate=None`. Fetch continua explícito e leitura
local continua offline/read-only.

## Limites

Nenhum cálculo Pw:HR, decoupling, split, eligibility, threshold, advisory ou
prescrição foi criado. A validação estrutural não declara que uma atividade seja
fisiologicamente comparável; isso pertence exclusivamente a HR-2.

## Gate HR-2

**HR-2 está READY.** O sistema agora representa `power(t)` e `heart_rate(t)`
no mesmo eixo temporal, com cache e mismatch explícito. HR-2 ainda precisa
definir métrica, eligibility e policy separadas.

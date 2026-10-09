# STREAM-1 — Normalized Activity Streams Boundary

> Dono: **repo** (`docs/STREAM-1-ACTIVITY-STREAMS.md`).
> Status: **DONE**. Infraestrutura de streams; não calcula Pw:HR/decoupling.

## Motivo e escopo

HR-2 permanece BLOCKED porque faltava boundary temporal, capability e cache de
streams. STREAM-1 cria somente essa infraestrutura. Não introduz ratio,
primeira/segunda metade, eligibility, segmentação, interpolação, resampling,

## Formatos auditados

O único formato exercitado por código e fixtures antes de STREAM-1 era a
resposta de `IntervalsClient.activity_streams()` como dict de arrays, com:

```python
{"time": [...], "watts": [...]}
```

`ftp_scan` já usa `time` como offsets em segundos para derivar taxa de
amostragem. STREAM-2B confirmou `heartrate` com respostas reais sanitizadas;
o detalhe está em `docs/STREAM-2-HEART-RATE-STREAM.md`.

## Boundary

`src/provider.py` fornece os contratos agnósticos:

| contrato | papel |
|---|---|
| `ProviderCapability.READ_ACTIVITY_STREAMS` | provider declara leitura temporal |
| `ActivityStreamProvider` | `activity_stream(activity_id) -> ActivityStream` |
| `ActivityStreamPoint` | `elapsed_seconds`, `power`, `heart_rate` opcionais |
| `ActivityStream` | atividade observada, pontos, campos disponíveis, alinhamento, contagens e captura |

`activity_id` é linkage do provider, nunca `HermesWorkoutId`.

## Tempo, potência e FC

`IntervalsAdapter` é o único lugar que conhece `time`, `watts` e `heartrate`.
Ele converte para pontos com `elapsed_seconds`: offset em segundos desde o
início da atividade. Não fabrica timestamp absoluto.

Potência numérica finita, inclusive `0`, é preservada. `None`, booleanos,

## Alinhamento, gaps e ordem

| condição | `alignment` | pontos |
|---|---|---|
| `time` e `watts` com mesmo comprimento e tempos finitos | `aligned` | emitidos e ordenados por tempo; duplicatas preservam ordem recebida |
| tempo ausente | `missing_time` | nenhum |
| comprimentos diferentes | `length_mismatch` | nenhum |
| tempo inválido/ausente dentro de arrays de mesmo tamanho | `invalid_time` | emitidos na ordem recebida, com `elapsed_seconds=None` |
| ambos vazios/ausentes | `empty` | nenhum |

Não há interpolação, fill, nearest neighbor, agregação de timestamps duplicados

## Cache e APIs

Streams não foram adicionados a `training_snapshot.json`, pois podem ser

```python
app.fetch_activity_stream(activity_id, provider=..., now=...)
app.get_cached_activity_stream(provider="intervals", activity_id=...)
```

`fetch_...` é operação remota explícita e escreve apenas seu cache. `get_cached...`

## Limitação e gate HR-2

STREAM-1 resolve capability, contrato, normalização de tempo+potência,

## Testes

`tests/test_activity_streams.py` (15) cobre DTO frozen/serialização, zero e

# STREAM-2 - Intervals.icu HR Stream

> Dono: **repo**. Pesquisa em fontes primarias oficiais do Intervals.icu e
> inspecao local. Consultada em 2026-10-05. Nenhum codigo de producao foi
> alterado.

## Conclusao

| Pergunta | Achado | Nivel de confirmacao |
|---|---|---|
| Chave temporal de FC armazenada | `heartrate` | Confirmado por fonte oficial do mantenedor. |
| Chave temporal de FC corrigida/calculada | `fixed_heartrate` | Confirmado por fonte oficial do mantenedor. |
| Chave a requisitar para dados originais | `heartrate` em `types`, por exemplo `types=heartrate,time` | Confirmado para o nome do stream; a especificacao REST aceita `types` mas nao enumera valores. |
| Unidade | Nao confirmada explicitamente para `ActivityStream.data` pela especificacao/API oficial examinada. | **Nao assumir bpm como contrato da API.** |
| Shape da resposta | Array de objetos `ActivityStream`; cada objeto tem `type`, `name`, `data`, `data2`, `valueTypeIsArray`, `anomalies`, `custom` e `allNull` no schema oficial. | Confirmado. |
| Array paralelo a `time` | Nao ha contrato oficial examinado que declare `data.length == time.data.length` ou alinhamento por indice entre `heartrate`/`fixed_heartrate` e `time`. | **Nao confirmado.** |

Portanto, STREAM-2 nao deve habilitar Pw:HR com base somente nesta pesquisa. O
consumidor pode pedir `heartrate,time`, mas deve validar em uma resposta real
autorizada: presenca dos dois streams, arrays, comprimentos iguais, timestamps
finitos e valores de FC validos. `fixed_heartrate` e uma alternativa corrigida,
nao um alias documentado de `heartrate`; a escolha entre bruto e corrigido e uma
decisao de produto que requer regra explicita.

## Evidencia oficial

### Endpoint e resposta

1. A especificacao OpenAPI oficial declara `GET /api/v1/activity/{id}/streams{ext}`
   como "List streams for the activity". O parametro opcional `types` e uma lista
   de strings, e a resposta 200 e um array de `ActivityStream`:
   [OpenAPI - getActivityStreams](https://intervals.icu/api/v1/docs).
2. No mesmo schema, `ActivityStream.type` e `string`; `data` e `object`; nao ha
   enum de tipos, unidade, nem restricao de tamanho/alinhamento entre streams:
   [OpenAPI - ActivityStream](https://intervals.icu/api/v1/docs).
3. O endpoint pedido nesta tarefa, `/api/v1/activity/{id}/streams.json`, e a forma
   com extensao `.json` do path `{ext}`. A documentacao oficial tambem diferencia
   `.csv`: "If ext is .csv then CSV data is returned instead of JSON":
   [OpenAPI - descricao de getActivityStreams](https://intervals.icu/api/v1/docs).

### Nome exato da FC

1. David, mantenedor do Intervals.icu, declarou para `ActivityStream`: "You need
   to get the `fixed_heartrate` stream and maybe also `time` (if you are concerned
   about activities with multiple seconds between ticks).":
   [Forum oficial, post #3](https://forum.intervals.icu/t/server-side-data-model-for-scripts/25781/3).
2. A documentacao oficial do modelo de dados, publicada pelo mesmo mantenedor,
   lista os tipos `time`, `heartrate`, ... `fixed_watts`, `fixed_heartrate` e
   explica que `fixed_heartrate` pode ser obtido como
   `icu.streams.fixed_heartrate`; tambem afirma que streams armazenados aparecem
   em `stream_types` e que "others e.g. fixed_watts are computed on the fly":
   [modelo de dados oficial, ActivityStreamSet](https://forum.intervals.icu/t/server-side-data-model-for-scripts/25781#activitystreamset).
3. Em orientacao sobre a API, o mantenedor chama explicitamente `heartrate` de
   stream, junto com `watts`: "The watts and heartrate streams include info on
   anomalies detected and fixed by Intervals.icu.":
   [Forum oficial, post #131](https://forum.intervals.icu/t/api-access-to-intervals-icu/609/131).

Isso estabelece `heartrate` como a chave do stream armazenado/bruto e
`fixed_heartrate` como a chave corrigida/calculada. Nenhuma das fontes autoriza
trocar uma pela outra silenciosamente.

### Unidade e alinhamento: limite da evidencia

- O modelo de dados chama o resultado de `fixed_heartrate` de "heart rate", mas
  nao anota unidade para `ActivityStream.data`. Ele usa `bpm` explicitamente em
  outro DTO (`HRRecovery.start_bpm` e `end_bpm`), o que **nao** especifica a
  unidade do stream: [modelo de dados oficial, HRRecovery](https://forum.intervals.icu/t/server-side-data-model-for-scripts/25781#hrrecovery).
- A observacao oficial sobre "multiple seconds between ticks" prova que o tempo
  nao deve ser presumido como grade de 1 Hz. Ela nao estabelece que um array de
  FC tenha o mesmo comprimento do array `time`, nem alinhamento por indice.
- Consequentemente, bpm e arrays paralelos a `time` sao expectativas plausiveis
  de dominio, mas permanecem **nao confirmadas como contrato oficial** desta
  resposta REST. Esta nota deliberadamente nao as transforma em contrato.

## Inspecao local

- Nao ha fixture, captura real sanitizada, arquivo FIT ou CSV versionado que
  contenha `heartrate`, `fixed_heartrate` ou uma resposta real de streams.
- `tests/test_intervals_client.py` exercita apenas resposta sintetica
  `[{"type": "watts", "data": [...]}, {"type": "time", "data": [...]}]`.
  Ela confirma somente o flattening local, nao a FC nem o contrato remoto.
- `docs/KNOWN_ISSUES.md` registra uma sondagem real anterior para
  `types=watts,time`: a API retornou uma lista de `{type, data}`. O registro nao
  inclui FC, unidade, identificador de atividade ou payload preservado; e
  evidencia local historica, nao substituto das fontes oficiais acima.

## Contrato seguro para eventual implementacao

Requisicao candidata, ainda sujeita a validacao em atividade real:

```text
GET /api/v1/activity/{id}/streams.json?types=heartrate,time
```

Nao introduzir suporte a `fixed_heartrate`, conversao para bpm, zip por indice,
interpolacao ou resampling sem uma captura real sanitizada e testes que comprovem
o formato observado. Se a politica exigir dados corrigidos, requisitar
explicitamente `fixed_heartrate,time` e registrar essa escolha como semantica de
dados, nao como detalhe de transporte.

## STREAM-2B - validacao empirica sanitizada

Em 2026-10-05, tres VirtualRides historicas independentes foram consultadas
com `types=time,watts,heartrate,fixed_heartrate`. IDs, atleta, nome,
localizacao e timestamps absolutos nao foram retidos.

| amostra | moving time | len(time/watts/heartrate) | tempo | nulls HR | zeros HR | media HR / resumo |
|---|---:|---:|---|---:|---:|---|
| A | 2447 s | 2448 / 2448 / 2448 | 0..2447, finito e monotono | 0 | 0 | 131.043 / 131 |
| B | 3284 s | 3285 / 3285 / 3285 | 0..3284, finito e monotono | 0 | 0 | 143.500 / 144 |
| C | 3046 s | 3047 / 3047 / 3047 | 0..3046, finito e monotono | 0 | 0 | 137.896 / 138 |

Foram conferidos inicio, indices 1/2, primeiro quarto, metade, terceiro quarto

`tests/fixtures/activity_streams_time_watts_heartrate.json` preserva o shape
`{type, data}`, valores reais sanitizados de sete indices distribuidos da
amostra A e os comprimentos integrais. E fixture estrutural compacta, nao a
atividade inteira.

| questao | resultado | evidencia | confianca |
|---|---|---|---|
| chave HR | `heartrate` | fonte oficial + tres respostas reais | confirmada |
| unidade HR | bpm | valores 67..161 e media arredonda para `average_heartrate` nos tres resumos; OpenAPI nao a rotula | fortemente sustentada empiricamente |
| time e offset | segundos decorridos | 0..moving time, uma amostra por segundo nas tres respostas | confirmada empiricamente |
| alinhamento por indice | suportado | arrays coextensivos e indices distribuidos em tres amostras | fortemente sustentado; validar toda resposta |
| missing | nenhum nas tres amostras | contagem direta | nao generalizavel |

O boundary pode normalizar defensivamente `power(t), heart_rate(t)`, mas deve

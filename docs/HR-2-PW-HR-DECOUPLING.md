# HR-2 - Pw:HR / aerobic decoupling

> Dono: **repo** (`docs/HR-2-PW-HR-DECOUPLING.md`). Espelho de leitura no vault.
> Status: **DONE**. Metrica observacional e validade metodologica sao
> representadas separadamente; steady/aerobico nao e inferido sem evidencia.

## Decisao e comparabilidade externa

O Hermes calcula Pw:HR somente sobre um `ActivityStream` local ja normalizado e
em cache. O resultado separa sinais **observados pelo provider** (`power`,
`heart_rate`) da metrica **derivada pelo Hermes** e da metodologia computacional
de eligibility. Nenhuma camada cria advisory ou prescricao.

O Hermes adota a familia **TrainingPeaks-style EF decoupling**: `Normalized
Power / FC media` por metade. Nao reproduz numericamente TrainingPeaks sem
comparacao sobre a mesma selecao, pois o Hermes impoe sua propria regra de
samples/gaps e nao conhece a politica de pausas do produto externo. Portanto o
nome do resultado e **Hermes-specific, com formula TrainingPeaks-style**.

Isso diverge da formula publicada pelo mantenedor do Intervals.icu:
`average power / average HR` em cada metade, seguida de
`(EF1 - EF2) * 100 / EF1` ([forum oficial, post #10](https://forum.intervals.icu/t/aerobic-decoupling-calculation-question/1823/10)).
Quando `Normalized Power != potencia media`, os valores diferem. Hermes nao
alega compatibilidade numerica com Intervals.icu e nao troca para potencia media
silenciosamente.

## Formula e sinal

A definicao segue a documentacao metodologica do TrainingPeaks para ciclismo:

```text
NP_h = NormalizedPower(amostras da metade h)
HR_h = media aritmetica de heart_rate na metade h
EF_h = NP_h / HR_h
Pw:HR (%) = ((EF_primeira - EF_segunda) / EF_primeira) * 100
```

`NormalizedPower` usa a media movel de 30 segundos elevada a quarta potencia,
seguida da media e raiz quarta. A janela de 30 segundos vem da definicao de NP,
nao e um threshold fisiologico criado pelo Hermes.

- valor **positivo**: `EF` caiu na segunda metade; por exemplo, FC subiu com
  potencia semelhante;
- **zero**: `EF` permaneceu igual;
- valor **negativo**: `EF` aumentou. Isso nao prova melhora fisiologica: warm-up,
  clima e outros confundidores tambem podem produzir esse sinal.

TrainingPeaks define EF como a razao de Normalized Power por FC para ciclismo e
compara a primeira com a segunda metade; NP tambem pode ser calculada para uma
selecao/segmento ([Pw:HR/EF](https://help.trainingpeaks.com/hc/en-us/articles/204071724-Aerobic-Decoupling-Pw-Hr-and-Pa-HR-and-Efficiency-Factor-EF), [Normalized Power](https://help.trainingpeaks.com/hc/en-us/articles/204071804-Normalized-Power)). Hermes calcula NP **separadamente em cada metade**, nao sobre a atividade inteira antes do split.

## Methodological validity

Tres dimensoes permanecem separadas:

| dimensao | o que Hermes determina | resultado |
|---|---|---|
| structural/data quality | shape, sinais, ordenacao, duplicatas, gaps e janela NP | `computable` ou `not_eligible` com razao |
| effort structure | steady, intervalado, warm-up, cooldown, pausas/coasting | nao determinado automaticamente |
| contexto fisiologico | predominancia aerobica, intensidade individual, temperatura, hidratacao e fadiga | `methodological_context="unverified"` |

TrainingPeaks orienta selecionar um esforco longo e steady-state e informa que
EF vale para treino aerobico steady-state; o maintainer do Intervals.icu tambem
limita a interpretacao a intervalos longos, onde HR lag pesa menos. Essas sao
condicoes metodologicas, nao regras que o Hermes consegue inferir com os dados
atuais. Nao existe LT1/AeT individual, classificacao confiavel de intensidade,
cadence, temperatura, grade, vento, fueling, pausa ou marcador de warm-up neste
boundary. Zonas de FTP existentes sao prescricao operacional, nao prova de
intensidade aerobica individual.

## Eligibility computacional

`evaluate_pw_hr_eligibility(stream)` e separada de
`derive_pw_hr_decoupling(first_half, second_half)`. Uma atividade e elegivel
somente quando:

1. o stream esta `aligned`;
2. ha pontos com `elapsed_seconds`, `power` e `heart_rate` finitos e nao
   negativos;
3. offsets, ordenados por tempo sem mutar a entrada, sao estritamente unicos e
   contiguos em um segundo;
4. cada metade possui ao menos 30 samples, o minimo computacional da janela NP;
5. as medias de FC de ambas as metades sao maiores que zero.

Ausencia, `NaN`, desalinhamento, duplicatas, gap, amostras insuficientes ou FC
media zero retornam `not_eligible` com razao explicita. Power zero e FC zero nao
sao convertidos nem eliminados: power zero participa da NP; FC zero so impede o
calculo se tornar a media da metade igual a zero. Nao ha interpolacao,
resampling, forward-fill, nearest-neighbor ou media de timestamps duplicados.

O requisito de um segundo contiguo permite executar NP sem inventar amostras.
Ele e uma **data-quality policy / conservative computational guardrail do
Hermes**, nao uma afirmacao de que toda atividade computavel seja steady,
aerobica ou fisiologicamente comparavel. As tres amostras STREAM-2B foram 1 Hz,
mas a API nao promete universalmente essa frequencia; por isso o guardrail e
mantido e nao relaxado.

## Split, gaps e pausas

O eixo e `elapsed_seconds`. Depois da ordenacao deterministica, o midpoint e
`(primeiro_offset + ultimo_offset) / 2`; ponto exatamente no midpoint pertence
a primeira metade (`<=`), os posteriores pertencem a segunda (`>`). Portanto o
split e por tempo analisado, nao por quantidade de samples.

Como o provider nao oferece um contrato de moving time, pausa, coasting ou
segmento aerobico estavel neste boundary, qualquer gap ou intervalo irregular
invalida esta versao do calculo. Coasting com power zero em sequencia continua
nao e removido. O Hermes nao declara cobertura percentual: sem denominador de
tempo de esforco defensavel, um percentual seria falsa precisao.

## Resultado e API

`PwHrDecouplingView` expone `provider`, `activity_id`, `status`, `reason`,
`decoupling_pct`, agregados de ambas as metades, contagem/duracao analisadas,
`captured_at`, `computable` e `methodological_context="unverified"`. O alias
de leitura `physiological_context` permanece para o contrato HR-2B.

- `unavailable / stream_not_cached`: nao ha leitura local para a atividade;
- `not_eligible`: dados invalidos para esta metodologia;
- `calculated` + `computable=true`: valor matematico derivado, ainda com
  `methodological_context="unverified"`.

`Application.get_pw_hr_decoupling(provider=..., activity_id=...)` le somente
`activity_streams.json`. Nunca busca provider, nao altera cache, plano, snapshot,
lifecycle, completion, readiness ou PMC. `fetch_activity_stream(...)` continua
sendo a operacao remota explicita. `captured_at` e proveniencia/freshness, nao
gate automatico da metrica.

## Segmentacao, limites e ausencia de policy

Nesta etapa o calculo usa a atividade inteira. Isso nao afirma que warm-up,
intervalos ou cooldown sejam adequados: apenas nao ha detector defensavel para
remove-los. A proxima extensao correta, se necessaria, e uma selecao explicita
de segmento pelo consumidor (`start_elapsed`, `end_elapsed`), antes de qualquer
segmentacao automatica. Ela nao foi implementada aqui.

Cardiovascular drift descreve aumento de FC em exercicio prolongado, mas tambem
depende de hidratacao e temperatura (Coyle 1998, PMID 9694416; Coyle &
Gonzalez-Alonso 2001, PMID 11337829). O material metodologico recomenda
esforco longo, estavel e abaixo do limiar, mas nao fornece regra universal para
pausas, gaps, coasting, duracao ou classificacao de uma atividade real.

Por isso HR-2 nao infere `steady aerobic effort` e marca o contexto como
`unverified`. Nao ha threshold de 5% ou qualquer outro, labels bom/ruim,
metrica e, se desejado, receber contexto adicional que este boundary ainda nao
possui.

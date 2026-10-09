# PROMPT 57 - FTP/eFTP no Intervals.icu

> Dono: **repo**. Relatório de pesquisa e documentação. Consultado em
> 2026-10-07. Não houve alteração de código de produção, contrato de API ou
> calendário Intervals.icu.

## Objetivo Avaliado

Determinar, com fronteira explícita entre fontes oficiais do Intervals.icu,
modelos científicos e inferências, como o provider estima eFTP e como o Hermes
deve consumir essa informação sem promover estimates a FTP canônico.

## Conclusão

| Pergunta | Resultado | Confiança |
| --- | --- | --- |
| O que o eFTP representa no Intervals? | Potência da curva Morton 3P ajustada que corresponde a 1 h, a partir de esforço máximo. | Alta, resposta do mantenedor. |
| O estimate é atualizado automaticamente? | O eFTP contínuo é avaliado atividade a atividade; effort elegível pode elevá-lo e há decay declarado com queda de carga. | Alta para o comportamento geral; baixa para a fórmula do decay. |
| O algoritmo integral é reproduzível? | Não. Coeficientes, seleção completa de esforços, outliers e decay não foram publicados. | Alta. |
| `icu_pm_ftp` é FTP do atleta? | É eFTP específico da atividade, derivado pelo provider. | Alta. |
| Campos Intervals podem virar FTP Hermes automaticamente? | Não. São evidência/estimate, não confirmação explícita. | Decisão de produto Hermes. |
| CP e FTP são equivalentes? | Não. Podem se associar, mas não são intercambiáveis individualmente. | Alta, literatura. |
| FTP20 x 0,95 é FTP fisiológico universal? | Não. É estimate operacional; confiabilidade não prova equivalência individual com MLSS, IAT ou outros marcadores. | Alta, literatura. |

## Evidência Avaliada

### INTERVALS_OFFICIAL

1. [David, Intervals.icu - FTP and CP Interchangeability](https://forum.intervals.icu/t/ftp-and-cp-interchangeability-some-notes/2665/2)
   - O eFTP procura a curva Morton 3P mais próxima de um esforço máximo.
   - A potência da curva em 1 h é usada como eFTP.
   - A calibração usou milhares de curvas do FastFitness.Tips e os primeiros
     20 min de cada curva.
   - O autor apresenta a solução como pragmática para zonas/acompanhamento, não
     como validação fisiológica universal.
2. [David, Intervals.icu - Power model now complete](https://forum.intervals.icu/t/power-model-now-complete/1680/4)
   - O eFTP contínuo é calculado somente a partir dos dados de cada atividade.
   - Estimate maior pode elevar o eFTP; estimate menor não reduz imediatamente o
     valor corrente.
   - Há decay quando training load diminui, sem função ou parâmetros publicados.
3. [David, Intervals.icu - Download all activities in CSV format](https://forum.intervals.icu/t/download-all-activities-in-csv-format/599/1)
   - `icu_ftp` é o FTP capturado pelo usuário e é usado no cálculo de intensidade.
   - `icu_pm_ftp` é o FTP do power model da atividade.
4. [David, Intervals.icu - Custom field Java help](https://forum.intervals.icu/t/custom-field-java-help/40283/3)
   - Declara explicitamente que `activity.icu_pm_ftp` é o eFTP da atividade.
5. [Modelo de dados server-side](https://forum.intervals.icu/t/server-side-data-model-for-scripts/25781/16)
   - Confirma a existência de campos `icu_pm_ftp_secs`, `icu_pm_ftp_watts`,
     `icu_rolling_ftp`, `icu_rolling_ftp_delta`, `SportSettings.ftp`,
     `SportSettings.indoor_ftp` e `ftp_est_min_secs`.
   - Não estabelece semântica temporal/histórica completa desses campos.
6. [Texto de UI reproduzido no fórum](https://forum.intervals.icu/t/eftp-calculation-formula-based-on-effort/70480/2)
   - Relata esforço máximo entre 180 s e 30 min e duração mínima configurável.
   - É evidência operacional de confiança média: não é uma especificação do
     mantenedor e não deve ser fixada como invariante Hermes.

### SCIENTIFIC_MODEL

1. Morton (1996), modelo Critical Power de três parâmetros, PMID 8854981,
   [DOI](https://doi.org/10.1080/00140139608964484).
   - Fundamenta o modelo 3P citado pelo Intervals; não fornece a implementação
     proprietária do provider.
2. Jones et al. (2010), CP/W′, PMID 20195180,
   [DOI](https://doi.org/10.1249/MSS.0b013e3181d9cf7f).
   - No modelo clássico: $P(t) = CP + W'/t$.
3. Mackey et al. (2021), revisão FTP20, PMID 34304689,
   [PubMed](https://pubmed.ncbi.nlm.nih.gov/34304689/).
   - FTP20 tem uso prático/repetibilidade reportada, mas limites de concordância
     impedem assumir intercâmbio entre marcadores.
4. Borszcz et al. (2018), FTP, FTP60 e IAT, PMID 29801189,
   [DOI](https://doi.org/10.1055/s-0044-101546).
   - Viés médio pequeno não autoriza intercâmbio individual.
5. Borszcz et al. (2019), FTP e MLSS, PMID 30676826,
   [DOI](https://doi.org/10.1123/ijspp.2018-0572).
   - Associação forte não estabelece identidade entre FTP e MLSS.
6. Tramontin et al. (2022), dependência de aquecimento no FTP20, PMID 34749416,
   [DOI](https://doi.org/10.1055/a-1524-2312).
   - Aquecimento e pacing alteram o resultado do TT20.

### INFERENCE Deliberadamente Não Aceita

- Reconstruir a fórmula completa do eFTP Intervals a partir dos posts públicos.
- Inferir coeficientes, transformação de dados, tratamento de outliers ou taxa de
  decay do provider.
- Atribuir o modelo de Riegel ao eFTP Intervals.
- Assumir que `icu_ftp`, `icu_pm_ftp` ou rolling FTP possuem effective dating,
  imutabilidade ou auditabilidade histórica garantidos.
- Tratar CP como FTP, FTP como MLSS, ou 95% de TT20 como equivalência universal.
- Promover resultado de Zwift ou de outro provider a FTP Hermes sem confirmação.

## Decisão Hermes Verificada

O contrato documentado preserva a seguinte separação:

```text
provider estimate, teste ou algoritmo -> FtpEvidence -> Advice/suggestion
-> confirmação explícita do usuário -> FtpReference -> FTP canonical Hermes
```

| Entrada | Classificação Hermes | Pode alterar `FTP_CANONICAL` sem usuário? |
| --- | --- | --- |
| `activity.icu_pm_ftp` / eFTP | estimate específico da atividade | Não |
| `activity.icu_ftp` | dado capturado pelo provider | Não |
| best20 / `ftp_scan` | evidência derivada Hermes | Não |
| CP/W′ | parâmetros de modelo | Não |
| FTP20 x 0,95 | estimate operacional | Não |
| `DEFAULT_FTP` | fallback de engenharia | Não |
| valor confirmado | `FtpReference` | A confirmação cria a referência |

## Artefatos Produzidos

- `docs/EMBASAMENTO-CIENTIFICO.md`, seção `2.1 FTP, eFTP e modelos
  Power-Duration`.
- Referências 34--43 adicionadas à bibliografia do documento científico.
- Espelho oficial de `EMBASAMENTO-CIENTIFICO.md` sincronizado com
  `scripts/sync_vault_docs.py --sync docs/EMBASAMENTO-CIENTIFICO.md`.

## Validação Executada

| Comando | Resultado |
| --- | --- |
| `python3 -m unittest tests.test_embasamento_cientifico -v` | 21 testes OK |
| `python3 -m unittest discover -s tests -v` | 1401 testes OK |
| `git diff --check` | OK |
| `python3 scripts/sync_vault_docs.py --check` | `EMBASAMENTO-CIENTIFICO.md` em sincronia |

O último `--check` ainda apontou divergências pré-existentes em
`docs/ARQUITETURA.md` e `docs/DIAGRAMAS.md`; elas não pertencem a este prompt e
não foram modificadas.

## Próximo Trabalho Técnico

O próximo item planejado é FTP-H1: integrar `AthletePhysiologicalProfile` com
`FtpHistory`. Essa integração deve preservar o contrato acima: resolver uma
`FtpReference` confirmada por tempo, sem fallback implícito para estimativas do
provider ou de algoritmos.

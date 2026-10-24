# Treinos longos indoor baseados em potência — evidência e política candidata para o Hermes — 2026-10-23

> [!info] Dono deste documento
> Fonte canônica: `docs/research/TREINOS-LONGOS-INDOOR-POTENCIA-2026-10-23.md` **no repo**.
> O arquivo correspondente no vault é cópia. Quando divergirem, o repo vence.

## Pergunta, escopo e método

**Pergunta.** Que política o Hermes deve usar para gerar sessões longas indoor por potência, preservando o estímulo de endurance de baixa intensidade sem fundi-lo sem intenção a limiar, VO₂ ou fartlek?

**Escopo.** Ciclismo em trainer/ergômetro com potência como alvo operacional. “Longo” significa >=90 min apenas neste documento: é um corte de produto, não fisiológico. Foram priorizados estudos originais e um position stand do ACSM, consultados em 2026-10-23. DOI, PMID e URLs estão nas referências.

**Regra de leitura.** Cada conclusão é marcada como **evidência**, **extrapolação prática** ou **heurística de produto**. FTP é referência operacional de potência: não é automaticamente VT1, LT, MLSS, RCP ou CP. Portanto, nenhum paper abaixo valida a banda Z2 Hermes (56–75% FTP) como “abaixo de VT1” individual; ver também `docs/EMBASAMENTO-CIENTIFICO.md`, §2.

## Resumo executivo

1. **Evidência:** sessões longas de baixa intensidade participaram de intervenções de endurance bem-sucedidas, mas não existe duração universal. No RCT de Stöggl & Sperlich, LOW era lactato <2 mmol·L⁻¹ e os longos eram 150–240 min em atletas bem treinados [R1].
2. **Evidência:** potência média não certifica que o treino foi leve. Em ciclistas de elite, potência variável e constante com igual média produziram VO₂ e lactato diferentes [R3].
3. **Extrapolação prática:** indoor não tem o vento relativo da estrada; fluxo de ar ativo deve ser requisito de execução. Menor velocidade do ar reduziu a capacidade de endurance e acelerou a elevação de temperatura central em experimento no calor [R5].
4. **Heurística recomendada:** `endurance_long_indoor` deve ser estável, com teto explícito, `quality_minutes=0`, duração progressiva e checklist de ventilação/hidratação. Limiar, VO₂ e variabilidade são templates distintos.

---

## 1. Endurance de baixa intensidade: intensidade e duração

### Evidência verificável

| Achado | O que sustenta | Limite |
|---|---|---|
| Stöggl & Sperlich randomizaram 48 atletas bem treinados (15 ciclistas; VO₂peak médio 62,6 mL·kg⁻¹·min⁻¹) para HVT, threshold, HIIT ou POL por 9 semanas. `LOW` era FC correspondente a lactato <2 mmol·L⁻¹. Nas semanas de carga HVT havia três LOW de 90 min e duas LOW de 150–240 min. | Estrutura experimental explícita de trabalho prolongado abaixo de um marcador de lactato. | Multiesporte, bem treinados; não é indoor nem prescrição por FTP nem teste da duração ótima. [R1] |
| O POL do mesmo RCT continha duas sessões LONG LOW de 150–240 min, duas LOW de 90 min e duas HIIT por semana de carga. POL obteve os maiores ganhos de VO₂peak, tempo até exaustão e potência/velocidade de pico entre os grupos. | Longos LOW podem compor um programa efetivo no contexto estudado. | Não isola causalmente os longos LOW; havia também HIIT e os volumes totais diferiam. [R1] |
| Neal et al. compararam seis semanas de distribuição polarizada e threshold em ciclistas treinados e relataram maiores adaptações fisiológicas e de performance na polarizada. | Estudo específico de ciclistas que favorece olhar a distribuição semanal, não apenas uma sessão. | Não define duração individual do longão, ambiente indoor ou %FTP. [R2] |

Não existe nesses estudos uma duração “ideal” de 90, 120, 180 ou 240 min, tampouco um conversor de `%FTP` para o primeiro limiar.

### Extrapolação prática

- A Z2 Hermes é um **alvo operacional**, não prova fisiológica de baixa intensidade individual. FC, RPE e deriva ao longo da sessão podem indicar que o alvo prático está alto naquele dia, mas não criam um limiar fisiológico sem protocolo adequado.
- Uma sessão estável torna o estímulo entregue e a comparação entre semanas mais auditáveis. Isso é especialmente útil no trainer, sem coasting natural.
- A duração deve progredir a partir de volume observado, conclusão de sessões equivalentes e ambiente; não deve saltar para 150–240 min só porque essa faixa ocorreu em atletas treinados no RCT.

### Heurística de produto

`endurance_long_indoor` declara:

```text
intent=endurance_low_intensity
power_floor, power_ceiling
planned_duration
quality_minutes=0
variability=constant
environment_check_required=true
```

O teto faz parte do contrato: aceleração planejada acima dele deixa de ser esse template.

---

## 2. Limites de longos com VO₂/limiar ou muita variabilidade

### Evidência verificável: variabilidade não é neutra

Kolsung, Ettema & Skovereng fizeram 15 ciclistas competitivos de elite completar bouts de 28 min em trainer, constante ou variável, pareados por potência média. As condições baixa e alta foram 70% e 95% do limiar de lactato; a variável oscilou ±15% a cada dois minutos (na alta, alcançando 110% do limiar). Em ambas, a condição variável elevou VO₂ e lactato; na baixa também elevou o RPE global. Na alta, RPE global similar coexistiu com lactato maior [R3].

**O que isso demonstra:** potência média e duração iguais podem esconder custo fisiológico distinto; uma média na Z2 não basta para chamar uma sessão variável de endurance fácil; e RPE global pode não expor todo o custo no trabalho intenso.

**O que não demonstra:** o estudo não mede longos de 2–4 h, lesão, overtraining ou adaptação longitudinal. Logo, não demonstra que qualquer variação seja prejudicial.

Palmer et al. encontraram respostas metabólicas e cardiovasculares globais similares em 140 min constante versus variável, pareados por intensidade média, em ciclistas treinados [R4]. Isso impede a regra falsa “toda variabilidade sempre custa mais”. Amplitude, frequência e desenho da variação importam.

### Longo com qualidade: o que não foi encontrado

Não foi identificado nesta busca um RCT indoor que compare “endurance puro” contra “endurance longo acrescido de VO₂/threshold” com mesma duração e que fixe máximo seguro ou universal de minutos/potência/frequência. Também não há evidência aqui de que a combinação seja inerentemente insegura.

O RCT de [R1] separava LOW, HIIT e LT no calendário, mas seus longos POL incluíam 6–8 sprints máximos de 5 s separados por >=20 min. É uma combinação deliberada em atletas bem treinados, não evidência para o Hermes inseri-la por padrão: o efeito isolado dos sprints não foi testado e a intenção já não é estritamente estável.

### Extrapolação prática

- Picos threshold/VO₂, over-unders ou fartlek amplo tornam um treino difícil de classificar, recuperar e comparar se ele ainda for chamado de “endurance”.
- Uma sessão variável pode ser válida para especificidade de prova, mas deve ser `race_specific_variable`, nunca `endurance_long_indoor`; registrar amplitude, minutos acima do teto e variabilidade, não apenas média.
- Warm-up/cool-down Z2 não tornam uma sessão de qualidade um longão. A intenção primária continua `threshold` ou `vo2max`.

### Heurísticas de produto

1. `endurance_long_indoor`: `quality_minutes=0`; não sortear sprints, limiar, VO₂ ou fartlek.
2. `threshold` e `vo2max`: somente warm-up/cool-down Z2 necessários; não adicionar 60–120 min para preencher TSS.
3. Variação: somente template de especificidade com amplitude, limites e tempo acima do teto calculáveis; contabilizar como carga/qualidade distinta.
4. Longo perdido não vira limiar/VO₂ nem longo variável. É política Hermes, não conclusão dos papers.

---

## 3. Indoor: termorregulação, ventilação e hidratação

### Evidência verificável

| Achado | Limite |
|---|---|
| Menor velocidade do ar reduziu progressivamente o tempo até exaustão e associou-se a elevação mais rápida da temperatura central em exercício no calor. | Não é comparação direta entre home trainer e pedal outdoor. [R5] |
| Em nove ciclistas treinados, TT de 40 km a 32°C teve potência média menor que a 17, 22 e 27°C e temperatura central maior no fim. | Câmara ambiental; ciclismo com potência, mas não setup doméstico sem ventilador. [R6] |
| Após 2 h steady-state, grupo desidratado (~2,2% de perda de massa versus ~0,2%) produziu menor potência em TT de 5 km; os participantes estavam cegos ao estado de hidratação. | Não transforma 2,2% em regra universal de ingestão individual. [R7] |
| O position stand ACSM recomenda estratégia individualizada de fluidos, considerando taxa de suor, duração, intensidade e ambiente. | Não fornece uma dose universal de ml/h. [R8] |

### Extrapolação prática

Na estrada há velocidade relativa de ar criada pelo deslocamento; no trainer estacionário não, salvo ventilador. Com [R5], isto sustenta fluxo de ar ativo dirigido ao corpo em sessão longa indoor. É inferência física e operacional: [R5] não define vazão, tamanho ou posição de ventilador para uma casa.

Não exibir “beba X ml/h” como regra universal. O produto pode pedir líquido acessível e registrar condições/ingestão; a reposição deve considerar a estratégia individual, taxa de suor e ambiente [R8]. Sede, massa corporal e performance não devem colapsar em um gatilho único.

### Heurística de produto

Antes de publicar sessão indoor >=90 min, mostrar checklist de execução — não validação clínica:

- ventilador/ventilação disponível e direcionado ao atleta;
- líquido acessível e estratégia individual de reposição, se conhecida;
- opção explícita de reduzir/encerrar diante de mal-estar, sintomas de calor ou incapacidade de manter o alvo com segurança;
- captura opcional de temperatura, confirmação de ventilador, RPE e ingestão.

Sem confirmação ambiental, propor encurtar ou exigir aprovação humana em vez de publicar automaticamente a duração máxima. O corte de 90 min é conservador e de produto, não uma conclusão testada.

---

## 4. Templates longos por potência que não misturam estímulos

Os templates são **heurísticas de produto**. A literatura contextualiza LOW e mostra que potência média pode esconder custo; não validou estes percentuais, tempos ou critérios Hermes.

| Template | Estrutura | Intenção/proteção |
|---|---|---|
| `endurance_long_steady` | 10–15 min progressivos dentro de Z2 Hermes → 60–150 min contínuos Z2, sem passar `power_ceiling` → 5–10 min fáceis. | Endurance baixo; `quality_minutes=0`; default recomendado. |
| `endurance_long_segmented` | Mesma banda Z2; por exemplo 3 × 30–45 min com 2–5 min muito fáceis entre blocos para beber/ajustar setup, sem aumentar a potência. | Preserva intenção, permite pausas operacionais. Pausa não cria intervalo de qualidade. |
| `threshold_session_bounded` | Warm-up Z2 → blocos threshold explícitos → cool-down Z2; duração total só a necessária ao protocolo. | É limiar, não longão; expor minutos de qualidade, sem filler para elevar TSS. |
| `vo2_session_bounded` | Warm-up Z2 → blocos VO₂ e recuperações explícitos → cool-down Z2. | É VO₂, não endurance; sem filler longo, recuperação posterior prioritária. |
| `race_specific_variable` | Perfil previamente descrito: amplitude, duração, picos, recuperação, teto e tempo em cada faixa. | Especificidade opt-in; nunca classificar pela potência média como endurance. |

Faixas de duração são construção do produto, não prescrição individual. Seleção depende de volume semanal observado, sessões equivalentes concluídas e ambiente — não apenas FTP.

---

## 5. Política recomendada

### Decisão

Adotar **endurance estável, baixa intensidade e condicionado ao ambiente como default de longão indoor**. Não gerar “longão + qualidade” por padrão nem usar potência média como prova de que a intenção endurance foi mantida.

### Contrato mínimo

```text
LongIndoorPolicy
  intent: endurance_low_intensity | threshold | vo2max | race_specific_variable
  duration_min: integer
  power_floor: watts | %FTP
  power_ceiling: watts | %FTP
  quality_minutes: integer
  variability: constant | specified
  max_planned_time_above_endurance_ceiling: integer
  environment_check_required: boolean
  hydration_prompt_required: boolean
  evidence_refs: DOI/PMID[]
  rule_kind: evidence | heuristic | model
```

| Regra | Tipo | Proveniência |
|---|---|---|
| Default endurance é constante, `quality_minutes=0`, com teto. | Heurística de produto | [R3] motiva não usar média como dose; não ordena esse design. |
| Não converter longão em limiar/VO₂ para preencher TSS. | Heurística de produto | Separa intenção e preserva guardrails Hermes; não há RCT que fixe esse gate. |
| Pico acima do teto endurance troca `intent` e registra perfil/tempo. | Heurística de produto | Média igual pode ter custo diferente [R3]; taxonomia é do Hermes. |
| Indoor >=90 min requer confirmação de ventilação e prompt de hidratação individual. | Heurística informada por evidência | [R5–R8]; o corte 90 min é produto. |
| Duração progride por sessões concluídas e volume observado; sem evidência individual, menor duração ou aprovação humana. | Heurística de produto | Não há duração universal; evita extrapolar [R1]. |
| `%FTP` fica operacional; Hermes não diz que Z2 = VT1. | Modelo/contrato de domínio | FTP não é marcador fisiológico intercambiável. |

### Instrumentação antes de automatizar progressão

```text
planned_duration, completed_duration, prescribed_power_band,
time_above_endurance_ceiling, power_variability_metric,
room_temperature_if_available, fan_confirmed, fluids_confirmed,
RPE, interruptions, post_session_note, next_day_recovery_signal
```

Avaliar por atleta (N-of-1): conclusão, RPE, interrupções por calor, deriva de FC quando disponível e capacidade de completar a próxima sessão de qualidade. Sucesso não é maximizar TSS do longão; é aderência e carga tolerada sem violar intenção/guardrails.

## Fatos, lacunas e recomendação final

### Fatos verificáveis

- [R1] aplicou LOW de 150–240 min, abaixo de 2 mmol·L⁻¹ de lactato, em programa de atletas bem treinados.
- Em [R3], potência variável e constante com mesma média tiveram VO₂/lactato diferentes em ciclistas de elite.
- Menor velocidade do ar reduziu capacidade de endurance [R5]; calor e hipohidratação reduziram performance/potência nos protocolos de ciclismo [R6–R7].

### Lacunas

- Sem duração indoor universal ou mapeamento validado `%FTP` → VT1/baixa intensidade individual.
- Sem comparação quantitativa suficiente de trainer doméstico ventilado versus outdoor para igualar potência/duração/ventilador.
- Sem RCT que fixe máximo seguro universal para “longão + threshold/VO₂/variabilidade”. A separação recomendada é proteção de engenharia e intenção, não fisiologia provada.
- Estudos de distribuição têm amostras pequenas, treinadas e/ou multiesporte; não prescrevem automaticamente para iniciante, baixa disponibilidade ou calor.

### Recomendação

**Decisão do operador (2026-10-23): treino indoor tem teto absoluto de 180 min.** Aprovar `endurance_long_indoor` estável em Z2 Hermes, sem qualidade planejada e duração condicionada por histórico e checklist térmico/hidratação. O teto não é alvo; somente esse template pode se aproximar dele por padrão. Manter limiar, VO₂ e variabilidade em templates separados e opt-in por especificidade. Registrar a política como **heurística de produto informada por evidência**, instrumentá-la e só então ampliar duração automaticamente.

## Referências primárias e position stand

- **[R1]** Stöggl T, Sperlich B. *Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training.* Front Physiol. 2014;5:33. DOI: [10.3389/fphys.2014.00033](https://doi.org/10.3389/fphys.2014.00033). PMID: [24550842](https://pubmed.ncbi.nlm.nih.gov/24550842/). [Texto completo](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2014.00033/full).
- **[R2]** Neal CM, Hunter AM, Brennan L, et al. *Six weeks of a polarized training-intensity distribution leads to greater physiological and performance adaptations than a threshold model in trained cyclists.* J Appl Physiol. 2013;114(4):461–471. DOI: [10.1152/japplphysiol.00652.2012](https://doi.org/10.1152/japplphysiol.00652.2012). PMID: [23264537](https://pubmed.ncbi.nlm.nih.gov/23264537/).
- **[R3]** Kolsung EB, Ettema G, Skovereng K. *Physiological Response to Cycling With Variable Versus Constant Power Output.* Front Physiol. 2020;11:1098. DOI: [10.3389/fphys.2020.01098](https://doi.org/10.3389/fphys.2020.01098). PMID: [32982801](https://pubmed.ncbi.nlm.nih.gov/32982801/). PMCID: [PMC7481374](https://pmc.ncbi.nlm.nih.gov/articles/PMC7481374/).
- **[R4]** Palmer GS, Borghouts LB, Noakes TD, Hawley JA. *Metabolic and performance responses to constant-load vs. variable-intensity exercise in trained cyclists.* J Appl Physiol. 1999;87(3):1186–1196. DOI: [10.1152/jappl.1999.87.3.1186](https://doi.org/10.1152/jappl.1999.87.3.1186). PMID: [10484594](https://pubmed.ncbi.nlm.nih.gov/10484594/).
- **[R5]** Otani H, Kaya M, Tamaki A, Watson P, Maughan RJ. *Air velocity influences thermoregulation and endurance exercise capacity in the heat.* Appl Physiol Nutr Metab. 2018;43(2):131–138. DOI: [10.1139/apnm-2017-0448](https://doi.org/10.1139/apnm-2017-0448). PMID: [28985477](https://pubmed.ncbi.nlm.nih.gov/28985477/).
- **[R6]** Peiffer JJ, Abbiss CR. *Influence of environmental temperature on 40 km cycling time-trial performance.* Int J Sports Physiol Perform. 2011;6(2):208–220. DOI: [10.1123/ijspp.6.2.208](https://doi.org/10.1123/ijspp.6.2.208). PMID: [21725106](https://pubmed.ncbi.nlm.nih.gov/21725106/).
- **[R7]** Cheuvront SN, et al. *Dehydration Impairs Cycling Performance, Independently of Thirst: A Blinded Study.* Med Sci Sports Exerc. 2018;50(8):1697–1703. DOI: [10.1249/MSS.0000000000001597](https://doi.org/10.1249/MSS.0000000000001597). PMID: [29509643](https://pubmed.ncbi.nlm.nih.gov/29509643/).
- **[R8]** Sawka MN, Burke LM, Eichner ER, Maughan RJ, Montain SJ, Stachenfeld NS. American College of Sports Medicine position stand. *Exercise and Fluid Replacement.* Med Sci Sports Exerc. 2007;39(2):377–390. DOI: [10.1249/mss.0b013e31802ca597](https://doi.org/10.1249/mss.0b013e31802ca597). PMID: [17277604](https://pubmed.ncbi.nlm.nih.gov/17277604/).

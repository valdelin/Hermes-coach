# 🧬 Embasamento Científico do Algoritmo — Hermes Coach

> [!important] Fonte única da verdade: o vault
> A **tabela científica Z1–Z7** e o embasamento completo vivem no vault do
> Obsidian, e é de lá que `ZONE_BANDS` (`src/coach.py`) deriva:
>
> ```
> ~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/EMBASAMENTO-CIENTIFICO.md
> ```
>
> Este arquivo guarda apenas o **contrato algorítmico**: o que o código faz e
> por quê, em termos de seção e fórmula. O *por quê fisiológico* (a tabela
> Z1–Z7 com %FCmáx, %FC de limiar, RPE, sistema energético, recuperação
> típica, ressalvas por zona e a matriz de geração `.ZWO`) está no vault.
>
> Alterar a tabela exige alterar **os dois lados** — o teste
> `ZoneIntegrityTest` compara `ZONE_BANDS` com os valores da tabela e falha a
> suíte se divergirem (v0.0.30).

**Data:** 25/09/2026 · atualizado 01/10/2026 (v0.0.31)  
**Projeto:** Hermes Coach  
**Mapeamento:** Fisiologia do Exercício aplicada ao Algoritmo de Treino  

---

## 📌 Visão Geral

O **Hermes Coach** não aplica ajustes arbitrários. Toda a lógica de distribuição de dias, redução de carga por faltas, compensação de intensidade e estrutura de blocos baseia-se em princípios consolidados da **fisiologia do exercício** e da **metodologia do treinamento desportivo de endurance**.

### Contrato de carga: medida, estimativa e sinais distintos

O motor distingue quatro coisas que não podem ser somadas ou tratadas como
sinônimos:

| Campo | Origem | Uso no Hermes |
| --- | --- | --- |
| `power_training_load` | **Executado**: NP, duração e FTP válidos | TSS operacional: `horas × IF² × 100`, com `IF = NP / FTP`. Sem NP, ou em segmento de 30 s ou menos, é desconhecido; o motor não inventa NP para treino curto ou planejado. |
| `estimated_tss` | **Planejado**: blocos em %FTP, duração e recuperação | Orça carga futura para `build`, `reconcile` e forecast. Não representa TSS medido após execução. |
| `external_load` | Trabalho mecânico, distância, elevação ou outro marcador externo, com unidade declarada | Contexto de volume; não é convertido automaticamente para TSS. |
| `internal_load` | FC, RPE, TRIMP ou score de fonte declarada | Contexto de resposta do atleta; não é convertido automaticamente para carga externa. |

`icu_training_load` é a carga autoritativa que o Intervals.icu expõe para os
fluxos atuais de CTL/ATL/TSB. O Hermes a preserva em vez de recalcular o
histórico, porque a pipeline interna do Intervals não é reproduzível apenas por
TSS local. **Modelo computacional:** o PMC local usa TSS/`icu_training_load`
como entrada de EWMA 42/7 para projeção; não é uma medida fisiológica direta.

> **Limite operacional:** IF/NP/TSS são definições de prescrição e quantificação
> de carga por potência, não equivalentes a MLSS, LT, RCP ou Critical Power. Em
> HIIT curto, o valor depende fortemente de como a NP foi calculada, da janela
> analisada e das recuperações; não se deve inferir NP de potência média ou
> atribuir precisão fisiológica a um TSS estimado.

### Periodização e autoregulação são camadas distintas

**Heurística do sistema:** `GOAL` e a proximidade da prova definem fase e alvo
semanal. `TrainingPlanState` mantém goal, fase, semanas, cargas, TSB e
readiness, mas TSB não troca fase nem template semanal. TSB < -15 ou readiness
desfavorável adaptam somente a primeira sessão de qualidade para recuperação Z2.

**Evidência científica:** Galán-Rioja et al. (2023) contextualizam
periodização, distribuição de intensidade e volume. A separação acima é uma
decisão arquitetural do Hermes, não uma afirmação de que limites de TSB ou
readiness determinem universalmente a fase fisiológica.

### TrainingPhase é uma arquitetura, não uma sequência universal

`TrainingPhaseEngine` explicita as fases `BASE`, `BUILD`, `SPECIFIC`, `PEAK`,
`RECOVERY` e `TEST`, cada uma com objetivo, duração configurável, estímulos,
limites de carga e critérios de progressão, deload e saída. As transições são
regras de plano; a ordem não representa uma sequência fisiológica universal.

### Distribuição de intensidade

`IntensityDistributionEngine` reporta minutos efetivos de baixa, moderada e alta
intensidade, independentemente do número de sessões. `POLARIZED`, `PYRAMIDAL`,
`THRESHOLD_HEAVY` e `CUSTOM` são modelos de configuração, sem pressupor 80/20
universal. Galán-Rioja et al. (2023) e a revisão/meta-análise de 2025 (PMID
39788807) contextualizam a evidência; o relatório é um modelo computacional.

### Perfil fisiológico

`AthletePhysiologicalProfile` preserva FTP e sua fonte/confiança separadamente
de CP, W′, VO2max e marcadores de frequência cardíaca, todos opcionais. FTP é
uma referência operacional de potência; não é tratado como sinônimo de MLSS,
LT, CP ou RCP, nem usado para inferir marcadores ausentes.

### Estado de adaptação

`AdaptationState` mantém domínios normalizados de 0 a 1, atualizados por vetor
de contribuição, decaimento temporal e saturação. São heurísticas
computacionais para o motor, não medições fisiológicas.

### Prontidão multimodal

`ReadinessAssessment` combina HRV contra baseline individual, tendência de RHR,
sono, fadiga subjetiva, carga, desempenho opcional e consistência. GREEN/YELLOW/
RED indicam adequação ao treino, não diagnóstico; um sinal isolado não cancela
automaticamente uma sessão. Referências: Düking et al. (2021), PMID 34489178;
Granero-Gallegos et al. (2020), PMID 33143175.

---

## 📊 1. Distribuição Semanal e Reagendamento

* **Regra do Algoritmo:** A agenda é **configurável** (`TRAINING_DAYS` no `.env`; padrão `seg,ter,qua,qui,sex`), não fixa. Um treino perdido é redistribuído para o **próximo dia de treino da agenda**, e a redistribuição obedece ao teto de carga ([seção 4](#4-orçamento-semanal-de-carga-guardrail-do-algoritmo)) — não a uma regra fixa de dias. Implementação: `cmd_reconcile` / `_absorb_missed_into_budget`.
* **Fisiologia Aplicada:** **Princípio da Carga e Recuperação / Adaptação Genética**.
* **Fundamentação:**
  - O estímulo do treino causa microlesões musculares e depleção de glicogénio. A ressíntese total e a supercompensação mitocôndrial exigem um intervalo de **24h a 48h**.
  - Espaçar os treinos em dias intercalados evita o acúmulo de fadiga residual não funcional (*Non-Functional Overreaching*), garantindo que o sistema nervoso e metabólico esteja pronto para produzir a potência alvo.
  - **Ressalva:** a agenda é do **atleta**, não do algoritmo — impô-la ignoraria férias, turnos ou chuva. O que o motor garante é o **espaçamento mínimo** entre estímulos intensos, via ordenação dos focos na sequência de slots.

---

## 📉 2. Autorregulação de Carga e TSS Futuro

* **Regra do Algoritmo:** O teto da janela rolante de 7 dias é `cap diário × nº de dias de treino × escala do goal` (`weekly_budget()`), com o cap diário derivado da carga média **realizada** (`avg_load`, janela `BUDGET_WINDOW_DAYS = 60`). `build_plan` e `reconcile` partilham a mesma base, para nunca derivarem tetos diferentes da mesma carga.
* **Fisiologia Aplicada:** **Modelo Fitness-Fadiga de Banister & Teoria do Estresse**.
* **Fundamentação:**
  - **Fórmula de Banister:** $\text{Desempenho} = \text{Fitness} - \text{Fadiga}$.
  - Faltas e baixa aderência costumam ser sintomas de estresse extrínseco (trabalho, sono deficiente, doença ou fadiga oculta).
  - Tentar "compensar" treinos perdidos acumulando TSS em semanas seguintes gera um pico desproporcional de fadiga sobre um nível de *Fitness* que diminuiu levemente. O teto ajusta a carga à **capacidade absorutiva atual do atleta**, prevenindo lesões e imunodepressão.

> **Nota:** esta seção trata da **autorregulação de volume futuro** pelo `build` (faltas
> acumuladas/aderência). O tratamento **imediato** de um treino perdido isolado, absorvido
> pelo orçamento semanal, está na [seção 5](#5-treino-perdido-absorver-pelo-orçamento-não-substituir-por-recuperação).

---

## ⚡ 3. Limiar versus Teto: o que se preserva quando o orçamento aperta

* **Regra do Algoritmo:** Quando o orçamento semanal não comporta o plano, a redução é **hierárquica e preserva a zona declarada**: (1) corta `repeats`; (2) encurta `on_sec`; (3) encurta `off_sec`; (4) só então reduz `on_power`, **nunca abaixo do piso da zona**. Quando não cabe sem sair da zona, o código **prefere estourar o teto semanal a rebaixar o estímulo**.
* **Fisiologia Aplicada:** **Modelo de Treinamento Polarizado (Dr. Stephen Seiler)**, e as ressalvas por zona do documento canônico (vault).
* **Fundamentação:**
  - Pedalar acima do Primeiro Limiar Ventilatório ($VT1$) ou Limiar Autonômico provoca um estresse substancial no **Sistema Nervoso Simpático**.
  - A literatura mostra que o tempo de recuperação autonômica (variabilidade da frequência cardíaca - HRV) após treinos de alta intensidade é significativamente mais longo do que após treinos de Z2 (Endurance).
  - **Consequência no motor:** cortar **volume** antes de cortar **intensidade** é fisiologicamente mais conservador. Um treino de limiar rebaixado vira um treino de endurance *travestido* de limiar: o nome mente e a adaptação esperada (acima do LT1) não acontece. Bug real corrigido em v0.0.30: `2026-10-02` estava com `focus=sweetspot @ 0,55` — 55% é estímulo de recuperação com o nome de Sweet Spot intacto.
---

## 📏 4. Orçamento Semanal de Carga (Guardrail do Algoritmo)

* **Regra do Algoritmo:** O teto de TSS de uma janela rolante de 7 dias é calculado como
  `cap diário × nº de dias de treino da semana`, em que `cap diário = média de carga
  por dia de treino × 0,95`.
* **Fisiologia Aplicada:** **Teoria da Periodização** (Seiler) + **Modelo Fitness-Fadiga de Banister**.
* **Fundamentação:**
  - Seiler recomenda que a carga cresça de forma **gradual e controlada**, dentro de um
    volume semanal que o atleta consiga absorver. O teto funciona como *guardrail*: ele não
    é um alvo a atingir, é o limite que impede o plano de prescrever mais do que o atleta
    demonstrou tolerar.
  - A média de carga (`avg_load`) é calculada **apenas sobre sessões efetivamente
    executadas** (`paired_activity_id` presente no Intervals.icu). Carga prescrita mas não
    realizada não é evidência de tolerância e, por isso, não alimenta o teto.
  - **Erro corrigido (v0.0.30):** o teto era calculado como `cap diário × 7`. Como a média
    de carga é **por dia de treino** (não por dia-calendário), multiplicar por 7 concedia 7
    sessões numa semana que tem apenas `n` dias de treino, inflando o teto em `7/n`
    (≈1,4× com 5 dias). O teto semanal caiu de ~287 para ~220 TSS, e 5 dias de treino
    passaram a caber em 5 sessões de teto.

---

## 🔄 5. Treino Perdido: Absorver pelo Orçamento, Não Substituir por Recuperação

* **Regra do Algoritmo:** Um treino perdido não é reparado por uma sessão binária de
  "recuperação" nem por uma redução fixa de −5% no próximo Limiar. A carga não feita é
  **redistribuída** nos treinos posteriores de mesma natureza que ainda tenham folga dentro
  do teto semanal — limitada por um teto (`weekly_budget`), não por um fator arbitrário.
* **Fisiologia Aplicada:** **Teoria da Periodização** (Seiler) — Seção sobre consequences de
  sessões perdidas.
* **Fundamentação:**
  - Seiler e Friel tratam a falha de adesão como **ruído esperado** no macrociclo, e não como
    um evento a ser "reparado". A orientação é absorver o déficit ajustando a carga das
    sessões restantes **dentro do volume semanal já prescrito**, evitando tanto o acúmulo
    compensatório (pico de fadiga) quanto a troca binária.
  - A compensação é limitada por um teto, garantindo que a soma de 7 dias não exceda a
    capacidade atual do atleta.

### O que **não** se compensa — e por quê

O custo de perder uma sessão é proporcional ao **estímulo fisiológico**, não ao TSS bruto:

| Treino perdido | TSS (FTP 250) | Decisão do Algoritmo | Fundamentação |
|---|---|---|---|
| **Active recovery** (Z2 ≈0.55–0.60) | ~14 | **Não compensa** | O propósito do treino é **não gerar carga**; compensar exigiria carga, contradizendo o objetivo. Perder é quase sem custo. |
| **Z2 base** (≈0.70) | ~24 | **Absorve** (dentro do teto) | Volume puro; workload absorvível com mais volume de mesma natureza. |
| **SweetSpot** (≈0.88) | ~37 | **Absorve** (dentro do teto) | Volume puro, mesma natureza. |
| **Limiar** (≈0.98) | ~48 | **Não substitui com volume** | O estímulo é de alta intensidade; VO2/limiar não se constroem com mais Z2. Fica como "débito" para o `build` repriorizar pelo TSB real. |
| **VO2máx** (≈1.15) | ~41 | **Não substitui com volume** | A adaptação aeróbica vem da **intensidade acima do LT1** (Seiler), não de volume de base. |

> **Erro corrigido (v0.0.30):** a regra anterior inseria uma "recuperação" e reduzia −5% no
> próximo Limiar para **qualquer** falta, sem distinguir a natureza do treino perdido —
> inclusive quando o treino perdido era o próprio active recovery, ou quando era de VO2máx
> (caso em que se tentava "compensar" um estímulo de intensidade com mais volume de base,
> fisiologicamente ineficiente).

### Limites de segurança da absorção

- Só sessões **Z2/SweetSpot** recebem elevação de volume (nunca VO2/Limiar).
- Cada treino cresce no máximo **20%** de `on_sec` por reconciliação (evita inflar um único
  treino e criar um pico).
- Só absorve enquanto a soma rolante de 7 dias couber no teto; sem folga, a carga não feita
  sobe o TSB, e o próprio `build` reduz a semana seguinte (autorregulação).

---

## 🎯 6. Zonas como Invariante do Código (`ZONE_BANDS`)

*v0.0.30. Adicionado em v0.0.31.*

A tabela Z1–Z7 do documento canônico (vault) não é apenas documentação: ela é
uma **invariante verificável em código**. `ZONE_BANDS` (`src/coach.py`) carrega
pisos e tetos de %FTP, e `ZoneIntegrityTest` compara o dicionário com a tabela —
divergir entre código e documento **falha a suíte**.

```python
ZONE_BANDS = {
    FOCUS_ZONE1_RECOVERY:    (0.00, 0.55),   # Z1 Recuperação   <55%
    FOCUS_ZONE2_ENDURANCE:   (0.56, 0.75),   # Z2 Endurance   56–75%
    FOCUS_ZONE3_TEMPO:       (0.76, 0.90),   # Z3 Tempo       76–90%
    ZONE_SWEETSPOT:          (0.84, 0.97),   # Sweet Spot     84–97%
    FOCUS_ZONE4_LIMIAR:      (0.91, 1.05),   # Z4 Limiar      91–105%
    FOCUS_ZONE5_VO2MAX:      (1.06, 1.20),   # Z5 VO₂máx      106–120%
    FOCUS_ZONE6_ANAEROBICA:  (1.21, 1.50),   # Z6 Anaeróbica 121–150%
}
```

Helpers: `zone_floor(focus)`, `zone_ceiling(focus)`, `zone_band(focus)` e
`focus_zone(focus)` — aceitam tanto o foco de prescrição (`'sweetspot'`) quanto a
zona canônica (`'Z4 Limiar'`).

### Quatro decisões que a tabela impõe ao motor

**1. Todas as zonas têm faixa, mas nem todas têm foco prescrito.** `ZONE_BANDS`
cobre Z1–Z6 integralmente; o que existe em `FOCUS_ZONE` são só os focos
efetivamente prescritos hoje (Z2, Sweet Spot, Z4, Z5). Z1, Z3 e Z6 têm faixa
declarada **sem** template que as gere — estão no dicionário para tornar a
tabela completa e verificável, não para sugerir que sejam prescritas. Um teste
trava essa separação.

**2. Z7 está fora de `ZONE_BANDS` — deliberadamente.** A tabela o descreve como
**potência máxima**, não como faixa de %FTP: a potência máxima pode ser várias
vezes o FTP. Como `ZONE_BANDS` é um modelo de *faixa de %FTP*, não há o que
colocar entre 1,21 e ∞. A ausência é intencional, tem comentário no código e um
teste que verifica que nada `z7` entra.

**3. Active recovery é uma sessão dentro de Z2, não um foco Z1.** A tabela
define Z1 como `<55%`, mas o *active recovery* do motor é executado a **≈0,60** —
dentro da banda **Z2**, não em Z1. Não é arredondamento: a **zona** descreve o
estímulo fisiológico, enquanto *active recovery* descreve a **intenção da
sessão** (descarregar, circular) aplicada sobre um estímulo que, se isolado, seria
Z2. Logo Z1 é uma **intenção de sessão** dentro da banda Z2, sem foco próprio.
Consequência: `_is_active_recovery()` classifica por `focus == zone2` **e**
`on_power ≤ 0,65`, e o `reconcile` nunca compensa um active recovery perdido.

**4. Um foco de prescrição pode ser servido por mais de uma zona.**

```python
FOCUS_ZONE = {
    "zone2":     FOCUS_ZONE2_ENDURANCE,
    "endurance": FOCUS_ZONE2_ENDURANCE,   # mesma zona, outra template
    "sweetspot": ZONE_SWEETSPOT,          # categoria, não zona numerada
    "threshold": FOCUS_ZONE4_LIMIAR,
    "vo2max":    FOCUS_ZONE5_VO2MAX,
}
```

`zone2` e `endurance` são **ambos Z2** — duas templates distintas na mesma zona.
E `sweetspot` é **categoria de prescrição** (sobrepõe final de Z3 e início de
Z4), não um número de zona.

### Nomenclatura: constantes renomeadas, valores preservados

As constantes seguem a nomenclatura da tabela (`FOCUS_ZONE2_ENDURANCE`, não
`FOCUS_ZONE2`). Os **valores string** (`"zone2"`, `"threshold"`, `"vo2max"`) não
mudaram, e é deliberado: o valor é **persistido** em `plan.json` e **publicado**
no calendário do Intervals.icu — renomeá-lo quebraria planos salvos e eventos já
publicados. Logo `FOCUS_ZONE2_ENDURANCE = "zone2"` (constante nova, valor legado)
e `FOCUS_ZONE2 = FOCUS_ZONE2_ENDURANCE` (alias antigo, mesmo valor). O teste
`test_valores_string_dos_focos_nao_mudaram` trava essa compatibilidade, para que
uma futura "limpeza" de nomenclatura não quebre o histórico.

Verificação: varredura de 2.000 treinos gerados (5 TSB × 4 FTP × 5
`weekly_hours`) com **0 violações de zona**.

---

## 📚 Referências Bibliográficas Relevantes

> A lista completa (8 referências, incluindo a base das faixas de %FCmáx/%FC de
> limiar por zona e da meta-análise de distribuição de intensidade) está no
> documento canônico do vault.

1. **Banister, E. W. (1991).** *Modeling Muscle Fatigue and Recovery in Training*.
2. **Seiler, S. (2010).** *What is Best Practice for Training Intensity Distribution in Endurance Athletes?* International Journal of Sports Physiology and Performance.
3. **Seiler, S. (2018).** *Periodization Theory: Confronting an Inconvenient Truth*. Swiss Sports Institute.
4. **Coggan, A., & Allen, H. (2010).** *Training and Racing with a Power Meter*. Velopress.
5. **Billat, L. V. (2001).** *Interval Training for Performance: A Scientific and Empirical Update*. Sports Medicine.
6. **Friel, J. (2014).** *The Periodization Bible*. 2nd ed. Velo.
7. **Coggan, A. (2026).** *Normalized Power, Intensity Factor and Training Stress Score.* TrainingPeaks — <https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/>.
   *Definição operacional de NP, IF e TSS; não é evidência fisiológica primária.*
8. **Galán-Rioja, M. Á., Gonzalez-Ravé, J. M., González-Mohíno, F., & Seiler, S. (2023).** *Training Periodization, Intensity Distribution, and Volume in Trained Cyclists: A Systematic Review.* International Journal of Sports Physiology and Performance. <https://doi.org/10.1123/ijspp.2022-0302>
   *Contexto de periodização, distribuição de intensidade e volume em ciclistas treinados.*

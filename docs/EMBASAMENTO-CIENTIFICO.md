# 🧬 Embasamento Científico do Algoritmo — Hermes Coach

> [!important] Fonte única da verdade: o vault
> A **tabela científica Z1–Z7** e o embasamento completo vivem no vault do
> Obsidian, e é de lá que `ZONE_BANDS` (`src/coach.py`) deriva:
>
> ```
> ~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/EMBASAMENTO-CIENTIFICO.md
> ```
>
> Este arquivo é o **contrato algorítmico**: o que o código faz e por quê, em
> termos de seção e fórmula. O *por quê fisiológico* (a tabela Z1–Z7 com
> %FCmáx, %FC de limiar, RPE, sistema energético, recuperação típica, ressalvas
> por zona e a matriz de geração `.ZWO`) está no vault.
>
> Alterar a tabela exige alterar **os dois lados** — o teste
> `ZoneIntegrityTest` compara `ZONE_BANDS` com os valores da tabela e falha a
> suíte se divergirem (v0.0.30).

**Data:** 25/09/2026 · atualizado 01/10/2026 (P2-04)
**Projeto:** Hermes Coach
**Mapeamento:** Fisiologia do Exercício aplicada ao Algoritmo de Treino

## Como ler este documento

Toda afirmação relevante carrega uma classificação. A distinção é o ponto:
o motor **não** é fisiologia, e apresentar heurística como mecanismo é o modo
mais fácil de este projeto mentir para quem o lê.

| Classificação | Significado |
| --- | --- |
| **EVIDÊNCIA CIENTÍFICA** | Achado de literatura com fonte verificável. Não implica que o motor o reproduza. |
| **HEURÍSTICA DO SISTEMA** | Convenção do Hermes, configurável e contestável. Sem lastro fisiológico necessário. |
| **MODELO COMPUTACIONAL** | Aproximação numérica interna. Não é medição. |

**Sobre superlativos.** Não há "melhor", "ideal" ou "ótimo" sem base
comparativa. Onde a literatura não encontrou superioridade, o texto diz **não há
evidência suficiente** e aponta a heterogeneidade.

---

## Índice

1. [Princípios](#1-princípios) · 2. [FTP](#2-ftp) · 3. [Critical Power e W'](#3-critical-power-e-w) ·
4. [Zonas](#4-zonas) · 5. [Periodização](#5-periodização) ·
6. [Distribuição de intensidade](#6-distribuição-de-intensidade) ·
7. [Training Load](#7-training-load) · 8. [CTL / ATL / TSB](#8-ctl--atl--tsb) ·
9. [Readiness](#9-readiness) · 10. [Adaptation State](#10-adaptation-state) ·
11. [Progression Engine](#11-progression-engine) · 12. [VO2max](#12-vo2max) ·
13. [Recovery / Deload](#13-recovery--deload) · 14. [Limitações](#14-limitações) ·
15. [Referências](#15-referências)

---

## 1. Princípios

**HEURÍSTICA DO SISTEMA.** O Hermes não aplica ajustes arbitrários: a agenda, a
redução por faltas, a compensação de intensidade e a estrutura de blocos seguem
regras explícitas, todas localizáveis em `src/`. Onde uma regra é convenção
nossa, ela está rotulada como heurística — não como fisiologia.

**EVIDÊNCIA CIENTÍFICA.** A base é o princípio da carga e recuperação e o
modelo fitness-fadiga de Banister (1991). Banister é a **origem do modelo**,
não uma validação das constantes do Hermes: `0,95` no cap diário e o
`-15` de TSB são do sistema.

**Distinção estrutural: periodização ≠ autoregulação.** `GOAL` e a
proximidade da prova definem fase e alvo semanal. `TrainingPlanState` mantém
goal, fase, semanas, cargas, TSB e readiness, mas **TSB não troca fase nem
template semanal**. TSB < −15 ou readiness desfavorável adaptam somente a
primeira sessão de qualidade. Galán-Rioja et al. (2023) contextualizam
periodização, distribuição e volume; a separação em camadas é decisão
arquitetural, não afirmação de que limites de TSB determinem universalmente a
fase fisiológica.

**Nomenclatura: constantes renomeadas, valores preservados.** As constantes
seguem a nomenclatura da tabela (`FOCUS_ZONE2_ENDURANCE`). Os **valores string**
(`"zone2"`, `"threshold"`, `"vo2max"`) não mudam, e é deliberado: são
persistidos em `plan.json` e publicados no Intervals.icu — renomeá-los quebraria
planos salvos e eventos já publicados. `test_valores_string_dos_focos_nao_mudaram`
trava essa compatibilidade.

## 2. FTP

**EVIDÊNCIA CIENTÍFICA.** O teste FTP20 (20 min autocronometrado × 0,95) foi
descrito como **confiável** numa revisão de escopo de 15 estudos. A mesma
revisão registra que os estudos que comparam FTP20 com outros marcadores
fisiológicos relatam **limites de concordância amplos**, e conclui que os
parâmetros não são intercambiáveis. A literatura é limitada e a amostra é
majoritariamente masculina treinada (PMID 34304689).

**EVIDÊNCIA CIENTÍFICA — FTP não equivale a marcadores fisiológicos.**

- FTP correlaciona-se fortemente com a potência associada a lactato 4,0 mmol/L
  (r = 0,88; p < 0,001) e não difere significativamente dela em média — mas o viés
  médio foi 2,9 ± 24,6 W com limites de concordância de **−45 a +51 W**, o que
  **refuta equivalência**. LT, IAT, e LT por Dmax e Dmax modificado diferiram
  significativamente de FTP (todos p < 0,05) (PMID 31269000).
- A potência em MLSS foi **88,5% do FTP** (DP 4,8%) e **93,1% do FTP95%**
  (DP 5,1%), ambas diferentes de FTP95% (p < 0,001). MLSS respondeu ao treino
  (+12 ± 8 W; p = 0,002) enquanto FTP20 e FTP95% não responderam (p = 0,75) —
  95% do FTP é um substituto ruim para MLSS, e os autores registram que a alta
  variabilidade desaconselha trocar 95% por 88% (PMID 31689684).
- A potência no FTP foi maior que no limiar ventilatório (p < 0,001), e FTP e
  RCP tiveram correlação muito alta (r 0,71–0,90 em W; 0,79–0,93 em W/kg) com
  viés médio não significativo — com o alerta explícito de não usar os dois
  conceitos indistintamente (PMID 33728842).

**Consequência no motor.** `AthletePhysiologicalProfile` (`src/athlete_profile.py`)
preserva FTP e sua fonte/confiança (`FtpSource`, `FtpConfidence`) separadamente
de CP, W′, VO2max e marcadores de FC, todos opcionais. **O motor não infere
marcador ausente a partir de FTP.** FTP é referência operacional de potência.

## 3. Critical Power e W'

**EVIDÊNCIA CIENTÍFICA.** O modelo de dois parâmetros interpreta a relação
potência-duração, com CP como a taxa associada ao estado aeróbico máximo e W′
como a quantidade de trabalho tolerável acima de CP sem recuperação. Protocolos
de 3 min e rampa *all-out* fornecem medidas válidas em um único teste, além
dos testes de taxa constante distribuídos em vários dias (PMID 32899777).

**MODELO COMPUTACIONAL.** `CriticalPowerProfile` (`src/critical_power.py`) guarda
`critical_power`, `w_prime`, `protocol`, `confidence` e `test_dates`.
`estimate_cp()` e `estimate_w_prime()` ajustam $P = CP + W'/t$ por mínimos
quadrados e devolvem `None` com menos de dois esforços válidos — **nunca um valor
inventado**. `work_above_cp()` limita o esforço acima de CP pelo W′ disponível.

**HEURÍSTICA DO SISTEMA.** O ritmo padrão de reconstituição de W′ (0,1 W/s) é
convenção do Hermes, configurável por atleta, **não constante fisiológica
universal**. Idem para qualquer limiar de W′ do código.

**CP e W′ são complementares ao FTP:** não o substituem e não são equivalentes
a MLSS, LT ou RCP. Uso previsto: esforços acima do limiar, Z6, HIIT e análise
power-duration.

## 4. Zonas

**MODELO COMPUTACIONAL (invariante verificável).** A tabela Z1–Z7 do documento
canônico não é apenas documentação: `ZONE_BANDS` (`src/coach.py`) carrega pisos
e tetos de %FTP, e `ZoneIntegrityTest` compara o dicionário com a tabela —
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
`focus_zone(focus)` — aceitam tanto o foco de prescrição (`'sweetspot'`) quanto
a zona canônica (`'Z4 Limiar'`). Verificação: varredura de 2.000 treinos gerados
(5 TSB × 4 FTP × 5 `weekly_hours`) com **0 violações de zona**.

### Quatro decisões que a tabela impõe ao motor

**1. Todas as zonas têm faixa, mas nem todas têm foco prescrito.** `ZONE_BANDS`
cobre Z1–Z6; em `FOCUS_ZONE` existem só os focos prescritos hoje (Z2, Sweet
Spot, Z4, Z5). Z1, Z3 e Z6 têm faixa declarada **sem** template que as gere —
estão no dicionário para tornar a tabela completa e verificável, não para
sugerir que sejam prescritas. Um teste trava essa separação.

**2. Z7 está fora de `ZONE_BANDS` — deliberadamente.** A tabela o descreve como
**potência máxima**, não como faixa de %FTP: a potência máxima pode ser várias
vezes o FTP. Como `ZONE_BANDS` é um modelo de *faixa de %FTP*, não há o que
colocar entre 1,21 e ∞. A ausência é intencional, tem comentário no código e um
teste que verifica que nada `z7` entra.

**3. Active recovery é uma sessão dentro de Z2, não um foco Z1.** A tabela
define Z1 como `<55%`, mas o *active recovery* do motor é executado a **≈0,60** —
dentro da banda **Z2**. Não é arredondamento: a **zona** descreve o estímulo
fisiológico, enquanto *active recovery* descreve a **intenção da sessão**
(descarregar, circular). Logo Z1 é uma **intenção de sessão** dentro da banda Z2,
sem foco próprio. Consequência: `_is_active_recovery()` classifica por
`focus == zone2` **e** `on_power ≤ 0,65`, e o `reconcile` nunca compensa um active
recovery perdido.

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

### Intenção e dose: as famílias se sobrepõem

**EVIDÊNCIA CIENTÍFICA.** As bandas se cruzam: `sweetspot` (84–97%) e
`threshold` (91–105%) compartilham **91–97% FTP**. Nessa faixa a potência **não
distingue** as duas famílias, e é por isso que a diferenciação é por intenção e
dose (`src/zone_intent.py`), não por %FTP. `classify()` levanta
`AmbiguousIntensity` nessa faixa em vez de escolher pelo número.

| Família | Intenção | Dose | Forma | Alavancas de progressão |
| --- | --- | --- | --- | --- |
| Z2 Endurance | Sustentar blocos contínuos e treinos longos; construir base aeróbica e capacidade de *eload* | Contínuo, 30 min–4 h, sem lacunas internas | `CONTINUOUS` | duração, volume total |
| Sweet Spot | Alta densidade de estímulo com fadiga administrável, sobre o final de Z3 e o início de Z4 | Blocos de 8–30 min, com folga para sustentar a repetição | `INTERVAL` | duração, volume total |
| Z4 Limiar | Elevar a potência de limiar e a depreciação de lactato em esforço máximo sustentável | Blocos de 5–20 min, recuperação 2:1 a 4:1 | `INTERVAL` | duração, repetições, recuperação |

**HEURÍSTICA DO SISTEMA.** **Z2 não usa intervalos artificiais.** Fragmentar o
volume em pedaços para trabalhar "mais forte" quebra o que sustenta a base sem
acrescentar estímulo específico. **Sweet Spot é faixa de prescrição**, não zona
fisiológica universal: existe justamente por sobrepor Z3/Z4, e não equivale a
limiar fisiológico. **Não afirme que 95% FTP = MLSS** (ver seção 2).

### Redução hierárquica quando o orçamento aperta

**HEURÍSTICA DO SISTEMA.** A ordem é: (1) corta `repeats`; (2) encurta `on_sec`;
(3) encurta `off_sec`; (4) só então reduz `on_power`, **nunca abaixo do piso da
zona**. Sem caber sem sair da zona, o código **prefere estourar o teto semanal a
rebaixar o estímulo**.

**Justificativa.** Um treino de limiar rebaixado vira um treino de endurance
*travestido* de limiar: o nome mente e a adaptação esperada (acima do LT1) não
acontece. Bug real corrigido em v0.0.30: `2026-10-02` estava com
`focus=sweetspot @ 0,55` — 55% é estímulo de recuperação com o nome de Sweet
Spot intacto. Cortar volume antes de cortar intensidade é mais conservador e é
decisão do sistema, não achado de literatura.

## 5. Periodização

**MODELO COMPUTACIONAL.** `TrainingPhaseEngine` (`src/training_phase.py`)
explicita `BASE`, `BUILD`, `SPECIFIC`, `PEAK`, `RECOVERY` e `TEST`, cada uma com
objetivo, duração configurável, estímulos, limites de carga e critérios de
progressão, deload e saída. **As transições são regras de plano; a ordem não
representa uma sequência fisiológica universal.**

**EVIDÊNCIA CIENTÍFICA.** Não há evidência atual a favor de um modelo de
periodização específico em 8–12 semanas em ciclistas de estrada treinados, e
poucos estudos examinaram o impacto sazonal de forma sistemática (Galán-Rioja
et al., 2023; PMID 36640771). A revisão encontrou blocos de 1–8 semanas na
periodização por blocos, volume de 8,75–11,68 h/semana, e volume de 7,5–10,76
h/semana na periodização tradicional, com TID piramidal ou polarizada.

**MODELO COMPUTACIONAL.** A agenda é **configurável** (`TRAINING_DAYS` no
`.env`; padrão `seg,ter,qua,qui,sex`), não fixa. Um treino perdido é
redistribuído para o **próximo dia de treino da agenda**, obedecendo ao teto de
carga — não a uma regra fixa de dias. `cmd_reconcile` /
`_absorb_missed_into_budget`.

## 6. Distribuição de intensidade

**MODELO COMPUTACIONAL.** `IntensityDistributionEngine`
(`src/intensity_distribution.py`) reporta minutos efetivos de baixa, moderada e
alta intensidade, independentemente do número de sessões. `POLARIZED`,
`PYRAMIDAL`, `THRESHOLD_HEAVY` e `CUSTOM` são **modelos de configuração**, sem
pressupor 80/20 universal.

**EVIDÊNCIA CIENTÍFICA — não há modelo superior.** Meta-análise de 41 estudos,
81 grupos de treino e 797 participantes: tanto a abordagem polarizada
quanto a não polarizada melhoraram VO₂max (g = 0,42; IC 95% 0,31–0,53) e
desempenho em contrarrelógio (g = 0,39; IC 95% 0,25–0,53), **sem diferença
significativa entre modalidades** (p > 0,05). Duração de intervenção maior
associou-se a VO₂max (g = 0,03; IC 95% 0,02–0,05). **Nenhuma associação** foi
encontrada entre volume semanal ou total e mudanças em VO₂max ou desempenho. Os
autores concluem que, atingido o volume necessário, aumentos adicionais não
parecem enhancing performance, e recomendam priorizar distribuição efetiva em
vez de volume total ou modelo específico (Cove et al., 2025; PMID 39788807,
DOI 10.1016/j.jsams.2024.12.005).

**Consequência no motor.** A tabela Z1–Z7 do vault registra a mesma conclusão para
ciclistas treinados: 41 estudos, 797 ciclistas, sem diferença entre polarizado e
não polarizado.

## 7. Training Load

**METODOLOGIA DE INDÚSTRIA — não é evidência fisiológica.** NP, IF e TSS são
definições operacionais de prescrição e quantificação de carga por potência
(Coggan, TrainingPeaks). São largamente usadas e úteis para comparar sessões do
mesmo atleta, mas **não são equivalentes a MLSS, LT, RCP ou Critical Power**.

**MODELO COMPUTACIONAL.** O motor distingue quatro coisas que não podem ser
somadas nem tratadas como sinônimos:

| Campo | Origem | Uso no Hermes |
| --- | --- | --- |
| `power_training_load` | **Executado**: NP, duração e FTP válidos | TSS operacional: `horas × IF² × 100`, com `IF = NP / FTP`. Sem NP, ou em segmento de 30 s ou menos, é desconhecido; o motor não inventa NP para treino curto ou planejado. |
| `estimated_tss` | **Planejado**: blocos em %FTP, duração e recuperação | Orça carga futura para `build`, `reconcile` e forecast. Não representa TSS medido após execução. |
| `external_load` | Trabalho mecânico, distância, elevação ou outro marcador externo, com unidade declarada | Contexto de volume; não é convertido automaticamente para TSS. |
| `internal_load` | FC, RPE, TRIMP ou score de fonte declarada | Contexto de resposta do atleta; não é convertido automaticamente para carga externa. |

> **Limite operacional:** em HIIT curto, o valor depende fortemente de como a NP
> foi calculada, da janela analisada e das recuperações. Não se deve inferir NP
> de potência média nem atribuir precisão fisiológica a um TSS estimado.

## 8. CTL / ATL / TSB

**MODELO COMPUTACIONAL.** `icu_training_load` é a carga autoritativa que o
Intervals.icu expõe para os fluxos atuais de CTL/ATL/TSB. O Hermes a **preserva**
em vez de recalcular o histórico, porque a pipeline interna do Intervals não é
reproduzível apenas por TSS local. O PMC local usa TSS/`icu_training_load`
como entrada de EWMA 42/7 para projeção — **não é medida fisiológica direta**.

**HEURÍSTICA DO SISTEMA.** O teto de TSS de uma janela rolante de 7 dias é
`cap diário × nº de dias de treino × escala do goal` (`weekly_budget()`), com
`cap diário` derivado da carga média **realizada** (`avg_load`, janela
`BUDGET_WINDOW_DAYS = 60`) e multiplicado por 0,95. `build_plan` e `reconcile`
partilham a mesma base, para nunca derivarem tetos diferentes da mesma carga.

O teto funciona como *guardrail*: **não é alvo a atingir**, é o limite que
impede o plano de prescrever mais do que o atleta demonstrou tolerar. A média é
calculada **apenas sobre sessões efetivamente executadas**
(`paired_activity_id` presente) — carga prescrita e não realizada não é
evidência de tolerância.

> **Erro corrigido (v0.0.30):** o teto era `cap diário × 7`. Como a média de
> carga é **por dia de treino** (não por dia-calendário), isso concedia 7
> sessões numa semana com `n` dias de treino, inflando o teto em `7/n` (≈1,4×
> com 5 dias). O teto semanal caiu de ~287 para ~220 TSS.

## 9. Readiness

**MODELO COMPUTACIONAL.** `ReadinessAssessment`
(`src/readiness_assessment.py`) combina HRV contra baseline individual,
tendência de RHR, sono, fadiga subjetiva, carga, desempenho opcional e
consistência. `GREEN`/`YELLOW`/`RED` indicam **adequação ao treino, não
diagnóstico**, e um sinal isolado não cancela automaticamente uma sessão.

**EVIDÊNCIA CIENTÍFICA — efeito modesto e seletivo.** Numa revisão de escopo com
meta-análise de 8 estudos (198 participantes), treino guiado por HRV teve efeito
de tamanho médio sobre parâmetros fisiológicos submáximos (g = 0,296; IC 95%
0,031–0,562; p = 0,028), mas o efeito sobre **desempenho foi pequeno e não
significativo** (g = 0,079; IC 95% −0,050–0,393; p = 0,597) e sobre
V̇O₂*pico* também (g = 0,171; IC 95% −0,213–0,371; p = 0,130). Houve menos
não-respondedores em desempenho com treino por HRV (Düking et al., 2021;
PMID 34489178).

Noutra meta-análise de ECR, treino guiado por HRV e treino de controle
melhoraram ambos o VO₂max (p < 0,0001), com ES significativamente maior para o
grupo HRV (ES = 0,187; p < 0,0001) e efeito pequeno e positivo no desempenho
(ES = 0,402), **condicionado ao nível e ao sexo do atleta** — subgrupos amador e
feminino reportaram resultados melhores e significativos (Granero-Gallegos et
al., 2020; PMID 33143175).

**Consequência no motor.** A evidência justifica usar HRV como **uma entrada
entre várias** e justifica o tratamento de não-respondedores. Não justifica
prometer ganho de VO₂max, nem tratar um único sinal como veredito — o que é
exatamente o que o código faz.

## 10. Adaptation State

**HEURÍSTICA DO SISTEMA / MODELO COMPUTACIONAL.** `AdaptationState`
(`src/adaptation.py`) mantém seis domínios normalizados de 0 a 1, atualizados
por vetor de contribuição, decaimento temporal e saturação. **São heurísticas
computacionais para o motor, não medições fisiológicas.** Nenhum valor de
decaimento ou saturação tem lastro em literatura; são escolhidos para dar
comportamento estável e configurável.

`TrainingDecision` (`src/training_decision.py`) compõe os eixos em uma decisão
com `rationale` e `confidence`. A confiança é **heurística**: reflete
concordância entre sinais, não probabilidade estatisticamente calibrada.

## 11. Progression Engine

**MODELO COMPUTACIONAL.** `CompletionScore` e a progressão por família de
estímulo ficam em `src/progression.py`. O ponto central do motor: **cada degrau
altera uma dimensão por vez**. Subir repetições e duração no mesmo degrau é erro
de prescrição, não progressão.

No gerador VO2max isso é explícito — escadas separadas para duração do
intervalo, repetições, tempo total e intensidade, expostas por
`progression_ledger()` para verificação. No caso das famílias de Z2, Sweet Spot
e Limiar, as alavancas são de **dose**: Z2 e Sweet Spot progridem em duração e
volume; Limiar em duração, repetições e recuperação (seção 4).

**HEURÍSTICA DO SISTEMA.** Granularidade de degrau, saltos de volume e os
limiares que disparam avanço, estagnação ou recuo são do sistema. A
`CompletionScore` não é uma medida de quanto o atleta de fato executou.

## 12. VO2max

**EVIDÊNCIA CIENTÍFICA.** Intervalos de trabalho longos (≥2 min) produziram mais
tempo próximo de V̇O₂max que curtos (≤30 s) ou moderados (>30 s e <2 min), e
intervalos de intensidade variável superaram formatos de ritmo par
(SMD = 0,80; p < 0,01) (PMID 42237396, DOI 10.1186/s13102-026-01766-x). A mesma
revisão registra que a modalidade de recuperação (ativa vs. passiva) **não teve
efeito** sobre o tempo perto de V̇O₂max, e que a relação dose-resposta com
adaptações de longo prazo **ainda exige investigação**.

**EVIDÊNCIA CIENTÍFICA — nenhuma estrutura de protocolo é superior.** Numa
network meta-analysis de 19 publicações (240 atletas, 25,5 ± 5,3 anos),
nenhuma abordagem de HIIT diferiu significativamente dos intervalos longos
pares em tempo acumulado ≥90% V̇O₂max. As estimativas pontuais mais altas foram
para duração decrescente (SMD = 0,87; IC 95% −0,30–2,04) e intensidade variando
(SMD = 0,54; IC 95% −0,42–1,49), e 1:1 pontuou mais baixo (SMD = −0,68), mas
**todas as comparações de referência foram não significativas**, com
heterogeneidade substancial (I² = 69,2%; Q total = 55,12; df = 17; p < 0,0001) e
inconsistência significativa (Q entre designs = 20,78; p = 0,002). Os autores
concluem que a seleção de protocolo deve priorizar viabilidade,
características do atleta e correspondência de carga **em vez do ranking**, que
classificam como exploratório (PMID 42482078, DOI 10.1186/s13102-026-01891-7).

**MODELO COMPUTACIONAL.** `VO2Workout` (`src/vo2_generator.py`) descreve o
bloco por `interval_duration`, `repetitions`, `work_power_range`,
`recovery_duration`, `recovery_power`, `total_work_time`, `progression_step` e
`lever`, em três famílias: `LONG_INTERVALS`, `SHORT_INTERVALS` e
`VARIABLE_INTERVALS`. A baseline de 4 min de `LONG_INTERVALS` segue o achado dos
intervalos ≥2 min. A faixa padrão de 106–120% FTP é a banda Z5 declarada, e
`Z5_CEILING` impede que o degrau de intensidade atravesse para Z6.

**HEURÍSTICA DO SISTEMA.** Os templates 4x4, 5x3 e 3x5 são **formatos de
prescrição configuráveis**, não protocolos universais nem recomendações de
eficácia — a network meta-analysis não encontrou superioridade entre estruturas.
115% do FTP **não** é valor universal. O degrau de intensidade (+2% por degrau)
e a direção dessa progressão são convenções: a NMA posicionou duração
decrescente e intensidade variável acima das demais, mas de forma exploratória e
não significativa. `recovery_power` (0,40) e `recovery_ratio` (0,5) são
convenções — a recuperação ativa vs. passiva não afetou o tempo perto de
V̇O₂max (PMID 42237396). A faixa de trabalho acumulado (600–2400 s) em
`evaluate()` também é heurística: os templates ficam sempre dentro dela.

## 13. Recovery / Deload

**HEURÍSTICA DO SISTEMA.** Um treino perdido **não** é reparado por uma sessão
binária de "recuperação" nem por uma redução fixa de −5% no próximo Limiar. A
carga não feita é **redistribuída** nos treinos posteriores de mesma natureza que
ainda tenham folga dentro do teto semanal — limitada por `weekly_budget`, não por
fator arbitrário. Implementação: `cmd_reconcile` /
`_absorb_missed_into_budget`.

O custo de perder uma sessão é proporcional ao **estímulo fisiológico**, não ao
TSS bruto (tabela de exemplo, FTP 250 W):

| Treino perdido | TSS | Decisão do Algoritmo | Fundamentação |
|---|---|---|---|
| **Active recovery** (Z2 ≈0,55–0,60) | ~14 | **Não compensa** | O propósito do treino é **não gerar carga**; compensar exigiria carga, contradizendo o objetivo. |
| **Z2 base** (≈0,70) | ~24 | **Absorve** (dentro do teto) | Volume puro; absorvível com mais volume de mesma natureza. |
| **SweetSpot** (≈0,88) | ~37 | **Absorve** (dentro do teto) | Volume puro, mesma natureza. |
| **Limiar** (≈0,98) | ~48 | **Não substitui com volume** | O estímulo é de alta intensidade; não se constrói com mais Z2. Fica como débito para o `build` repriorizar. |
| **VO2máx** (≈1,15) | ~41 | **Não substitui com volume** | A adaptação aeróbica vem da intensidade, não de volume de base. |

**Limites de segurança da absorção.** Só sessões **Z2/SweetSpot** recebem
elevação de volume (nunca VO2/Limiar); cada treino cresce no máximo **20%** de
`on_sec` por reconciliação; só absorve enquanto a soma rolante de 7 dias couber
no teto — sem folga, a carga não feita sobe o TSB e o próprio `build` reduz a
semana seguinte.

> **Erro corrigido (v0.0.30):** a regra anterior inseria uma "recuperação" e
> reduzia −5% no próximo Limiar para **qualquer** falta, sem distinguir a
> natureza do treino perdido — inclusive quando o treino perdido era o próprio
> active recovery, ou VO2máx (compensar estímulo de intensidade com volume de
> base).

Active recovery é tratado como **intenção de sessão dentro de Z2**, não como
foco Z1 e não absorvível quando perdido (seção 4, decisão 3).

## 14. Limitações

**MODELO COMPUTACIONAL.** O que este motor não faz, e não deve ser lido como se
fizesse.

1. **FTP não é fisiologia.** É referência operacional de potência, com limites
   de concordância amplos frente a marcadores de lactato. Não infere MLSS, LT,
   VT, RCP ou CP (seção 2).
2. **Não há modelo de periodização superior.** A evidência é insuficiente para
   eleger um; o Hermes escolhe por coerência interna e configurabilidade, não
   por eficácia demonstrada (seções 5 e 6).
3. **Não há protocolo de VO2max superior.** As comparações entre estruturas são
   não significativas e heterogêneas (seção 12).
4. **TSS é metodologia de indústria.** NP/IF/TSS não são equivalentes a medidas
   fisiológicas, e em HIIT curto o valor depende do método de cálculo da NP
   (seção 7).
5. **Prontidão não prediz desempenho.** O efeito de HRV-guidado é pequeno e não
   significativo para desempenho e V̇O₂*pico* (seção 9).
6. **Módulos isolados não afetam a publicação.** `src/training_phase.py`,
   `src/progression.py`, `src/intensity_distribution.py`,
   `src/athlete_profile.py`, `src/adaptation.py`, `src/training_decision.py`,
   `src/readiness_assessment.py`, `src/critical_power.py`,
   `src/vo2_generator.py` e `src/zone_intent.py` não participam de `build`/`push`,
   não alteram `plan.json`, os valores de `focus`, as bandas nem a publicação no
   Intervals.icu. São contratos testados, ainda não integrados ao fluxo.
7. **Heurísticas não são constantes fisiológicas.** Taxas de decaimento,
   saturação, reconstituição de W′, degraus de progressão, limites de TSB e
   coeficientes de IWMA são do sistema e configuráveis.
8. **Base de evidência restrita.** Vários estudos incluem só ciclistas do sexo
   masculino; a revisão de FTP20 (15 estudos) e a de HRV (8 estudos) são
   explicitamente pequenas. A generalização para outros orçamentos e estilos de
   pedal não está estabelecida.

## 15. Referências

Todas verificadas por PMID no NCBI. Autores, títulos e resultados citados neste
documento foram conferidos contra o abstract.

1. **Banister, E. W. (1991).** *Modeling Muscle Fatigue and Recovery in Training*.
2. **Seiler, S. (2010).** *What is Best Practice for Training Intensity Distribution in Endurance Athletes?* International Journal of Sports Physiology and Performance.
3. **Seiler, S. (2018).** *Periodization Theory: Confronting an Inconvenient Truth*. Swiss Sports Institute.
4. **Coggan, A., & Allen, H. (2010).** *Training and Racing with a Power Meter*. Velopress.
5. **Billat, L. V. (2001).** *Interval Training for Performance: A Scientific and Empirical Update*. Sports Medicine.
6. **Friel, J. (2014).** *The Periodization Bible*. 2nd ed. Velo.
7. **Coggan, A. (2026).** *Normalized Power, Intensity Factor and Training Stress Score.* TrainingPeaks — <https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/>
   *METODOLOGIA DE INDÚSTRIA. Definição operacional de NP, IF e TSS; não é evidência fisiológica primária.*
8. **Galán-Rioja, M. Á., Gonzalez-Ravé, J. M., González-Mohíno, F., & Seiler, S. (2023).** *Training Periodization, Intensity Distribution, and Volume in Trained Cyclists: A Systematic Review.* International Journal of Sports Physiology and Performance. PMID 36640771 — <https://doi.org/10.1123/ijspp.2022-0302>
   *EVIDÊNCIA. Sete estudos; nenhuma evidência a favor de um modelo de periodização específico em 8–12 semanas.*
9. **Cove, B., Chalmers, S., et al. (2025).** *The effect of training distribution, duration, and volume on VO₂max and performance in trained cyclists: a systematic review, multilevel meta-analysis, and multivariate meta-regression.* Journal of Science and Medicine in Sport. PMID 39788807 — <https://doi.org/10.1016/j.jsams.2024.12.005>
   *EVIDÊNCIA. 41 estudos, 797 participantes; polarizado e não polarizado sem diferença significativa; sem associação entre volume e adaptação.*
10. **Mackey, N., et al. (2021).** *What is known about the FTP(20) test related to cycling? A scoping review.* Journal of Sports Sciences. PMID 34304689 — <https://pubmed.ncbi.nlm.nih.gov/34304689/>
    *EVIDÊNCIA. Teste confiável, mas limites de concordância amplos impedem troca intercambiável de parâmetros.*
11. **Jeffries, O., Simmons, R., Patterson, S. D., & Waldron, M. (2021).** *Functional Threshold Power Is Not Equivalent to Lactate Parameters in Trained Cyclists.* Journal of Strength and Conditioning Research, 35(10), 2790–2794. PMID 31269000 — <https://pubmed.ncbi.nlm.nih.gov/31269000/>
    *EVIDÊNCIA. r = 0,88 com LT4,0, mas limites de concordância de −45 a +51 W; LT, IAT e Dmax diferiram de FTP.*
12. **Inglis, C., et al. (2020).** *Maximal Lactate Steady State Versus the 20-Minute Functional Threshold Power Test in Well-Trained Individuals: "Watts" the Big Deal?* International Journal of Sports Physiology and Performance. PMID 31689684 — <https://pubmed.ncbi.nlm.nih.gov/31689684/>
    *EVIDÊNCIA. MLSS = 88,5% do FTP (DP 4,8%); MLSS respondeu ao treino (+12 W) e FTP95% não.*
13. **Sitko, S., et al. (2022).** *Relationship between functional threshold power, ventilatory threshold and respiratory compensation point in road cycling.* Journal of Sports Medicine and Physical Fitness. PMID 33728842 — <https://pubmed.ncbi.nlm.nih.gov/33728842/>
    *EVIDÊNCIA. FTP acima de VT; FTP e RCP fortemente relacionados, com ressalva contra uso indistinto.*
14. **Chorley, A., Lamb, K. L., et al. (2020).** *The Application of Critical Power, the Work Capacity above Critical Power (W′), and its Reconstitution: A Narrative Review of Current Evidence and Implications for Cycling Training Prescription.* Sports, 8(9), 123. PMID 32899777 — <https://doi.org/10.3390/sports8090123>
    *EVIDÊNCIA. CP como taxa do estado aeróbico máximo; W′ como trabalho tolerável acima de CP.*
15. **Düking, P., Zinner, C., Trabelsi, K., Reed, J. L., et al. (2021).** *Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: A systematic review with meta-analysis.* Journal of Science and Medicine in Sport. PMID 34489178 — <https://doi.org/10.1016/j.jsams.2021.04.012>
    *EVIDÊNCIA. Efeito médio em parâmetros submáximos; efeito pequeno e não significativo em desempenho e V̇O₂*pico*.*
16. **Granero-Gallegos, A., González-Quílez, A., et al. (2020).** *HRV-Based Training for Improving VO₂max in Endurance Athletes. A Systematic Review with Meta-Analysis.* International Journal of Environmental Research and Public Health, 17(21), 7999. PMID 33143175 — <https://doi.org/10.3390/ijerph17217999>
    *EVIDÊNCIA. Efeito pequeno e positivo no desempenho, condicionado a nível e sexo do atleta.*
17. **Schoenmakers, B., et al. (2026).** *Time spent at or near V̇O₂max during high-intensity interval training — a systematic review and meta-analysis.* BMC Sports Science, Medicine and Rehabilitation, 2026. PMID 42237396 — <https://doi.org/10.1186/s13102-026-01766-x>
    *EVIDÊNCIA. Intervalos ≥2 min > curtos/moderados; intensidade variável > ritmo par (SMD 0,80); recuperação ativa vs. passiva sem efeito.*
18. **Held, M., et al. (2026).** *Comparison of high-intensity interval training protocol designs on accumulated time ≥90% V̇O₂max: a network meta-analysis.* BMC Sports Science, Medicine and Rehabilitation, 2026. PMID 42482078 — <https://doi.org/10.1186/s13102-026-01891-7>
    *EVIDÊNCIA. Nenhuma estrutura superior; todas as comparações não significativas, I² = 69,2%; rankings exploratórios.*

### Referências que sustentam a tabela Z1–Z7

A tabela científica Z1–Z7 — %FCmáx, %FC de limiar, RPE por zona (VT1, MLSS,
VT2), sistema energético, recuperação típica e a matriz de geração `.ZWO` —
está no documento canônico do vault, junto das referências de base de
validação de limiares (PMC5033582) e da revisão de CP/W′ e reconstituição
(PMC7552657).

# 🧬 Embasamento Científico do Algoritmo — Hermes Coach

**Data:** 25/09/2026  
**Projeto:** Hermes Coach  
**Mapeamento:** Fisiologia do Exercício aplicada ao Algoritmo de Treino  

---

## 📌 Visão Geral

O **Hermes Coach** não aplica ajustes arbitrários. Toda a lógica de distribuição de dias, redução de carga por faltas, compensação de intensidade e estrutura de blocos baseia-se em princípios consolidados da **fisiologia do exercício** e da **metodologia do treinamento desportivo de endurance**.

---

## 📊 1. Distribuição Semanal e Reagendamento (Ter/Qui/Sáb)

* **Regra do Algoritmo:** Treinos perdidos são reagendados prioritariamente para Terças, Quintas ou Sábados, garantindo que não haja dois treinos intensos em dias consecutivos.
* **Fisiologia Aplicada:** **Princípio da Carga e Recuperação / Adaptação Genética**.
* **Fundamentação:** 
  - O estímulo do treino causa microlesões musculares e depleção de glicogénio. A ressíntese total e a supercompensação mitocôndrial exigem um intervalo de **24h a 48h**.
  - Espaçar os treinos em dias intercalados evita o acúmulo de fadiga residual não funcional (*Non-Functional Overreaching*), garantindo que o sistema nervoso e metabólico esteja pronto para produzir a potência alvo.

---

## 📉 2. Autorregulação de Carga e TSS Futuro

* **Regra do Algoritmo:** Redução proporcional do volume/TSS dos próximos 7 dias (5% a 25%) em função da taxa de aderência e faltas acumuladas.
* **Fisiologia Aplicada:** **Modelo Fitness-Fadiga de Banister & Teoria do Estresse**.
* **Fundamentação:**
  - **Fórmula de Banister:** $\text{Desempenho} = \text{Fitness} - \text{Fadiga}$.
  - Faltas e baixa aderência costumam ser sintomas de estresse extrínseco (trabalho, sono deficiente, doença ou fadiga oculta).
  - Tentar "compensar" treinos perdidos acumulando TSS em semanas seguintes gera um pico desproporcional de fadiga sobre um nível de *Fitness* que diminuiu levemente. A redução de TSS ajusta a carga à **capacidade absorutiva atual do atleta**, prevenindo lesões e imunodepressão.

> **Nota:** esta seção trata da **autorregulação de volume futuro** pelo `build` (faltas
> acumuladas/aderência). O tratamento **imediato** de um treino perdido Isolado, absorvido
> pelo orçamento semanal, está na [seção 5](#5-treino-perdido-absorver-pelo-orçamento-não-substituir-por-recuperação).

---

## ⚡ 3. Compensação de Excesso de Intensidade ($IF > 1.15$)

* **Regra do Algoritmo:** Se o *Intensity Factor* (IF) real for $> 15\%$ superior ao planeado, o algoritmo reduz a carga do ciclo seguinte em $10\%$.
* **Fisiologia Aplicada:** **Modelo de Treinamento Polarizado (Dr. Stephen Seiler)**.
* **Fundamentação:**
  - Pedalar acima do Primeiro Limiar Ventilatório ($VT1$) ou Limiar Autonômico provoca um estresse substancial no **Sistema Nervoso Simpático**.
  - A literatura demonstrada por Stephen Seiler comprova que o tempo de recuperação autonômica (variabilidade da frequência cardíaca - HRV) após treinos de alta intensidade é significativamente mais longo do que após treinos de Z2 (Endurance). O corte de carga previne o *burnout* metabólico.

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

## 🎯 6. Arquitetura dos Blocos de Treino (Workout Builder)

### A. SweetSpot ($88\%$ FTP)
* **Estrutura:** $2 \times 15\text{ min}$ a $88\%$ FTP.
* **Fundamentação:** Formulado por Frank Overton e Dr. Andy Coggan, a zona de *SweetSpot* ($84\%-97\%$ FTP) oferece a **máxima densidade de adaptação fisiológica** (aumento de densidade mitocondrial e limiar de lactato) com o **mínimo custo de fadiga neuroendócrina**, permitindo alta frequência semanal de treinos.

### B. VO2máx ($110\%$ FTP)
* **Estrutura:** $4 \times 3\text{ min}$ a $110\%$ FTP (Relação esforço/pausa $1:1$).
* **Fundamentação:** Baseado nos estudos clássicos da Dra. Véronique Billat. Intervalos de 3 a 5 minutos nesta faixa de potência maximizam o tempo no qual o atleta permanece no débito cardíaco máximo ($vVO_2max$), recrutando fibras musculares do tipo IIa sem gerar acúmulo precoce de H+ que impediria a continuidade do treino.

---

## 📚 Referências Bibliográficas Relevantes

1. **Banister, E. W. (1991).** *Modeling Muscle Fatigue and Recovery in Training*.
2. **Seiler, S. (2010).** *What is Best Practice for Training Intensity Distribution in Endurance Athletes?* International Journal of Sports Physiology and Performance.
3. **Seiler, S. (2018).** *Periodization Theory: Confronting an Inconvenient Truth*. Swiss Sports Institute.
4. **Coggan, A., & Allen, H. (2010).** *Training and Racing with a Power Meter*. Velopress.
5. **Billat, L. V. (2001).** *Interval Training for Performance: A Scientific and Empirical Update*. Sports Medicine.
6. **Friel, J. (2014).** *The Periodization Bible*. 2nd ed. Velo.
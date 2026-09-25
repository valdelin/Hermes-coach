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

---

## ⚡ 3. Compensação de Excesso de Intensidade ($IF > 1.15$)

* **Regra do Algoritmo:** Se o *Intensity Factor* (IF) real for $> 15\%$ superior ao planeado, o algoritmo reduz a carga do ciclo seguinte em $10\%$.
* **Fisiologia Aplicada:** **Modelo de Treinamento Polarizado (Dr. Stephen Seiler)**.
* **Fundamentação:**
  - Pedalar acima do Primeiro Limiar Ventilatório ($VT1$) ou Limiar Autonômico provoca um estresse substancial no **Sistema Nervoso Simpático**.
  - A literatura demonstrada por Stephen Seiler comprova que o tempo de recuperação autonômica (variabilidade da frequência cardíaca - HRV) após treinos de alta intensidade é significativamente mais longo do que após treinos de Z2 (Endurance). O corte de carga previne o *burnout* metabólico.

---

## 🎯 4. Arquitetura dos Blocos de Treino (Workout Builder)

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
3. **Coggan, A., & Allen, H. (2010).** *Training and Racing with a Power Meter*. Velopress.
4. **Billat, L. V. (2001).** *Interval Training for Performance: A Scientific and Empirical Update*. Sports Medicine.
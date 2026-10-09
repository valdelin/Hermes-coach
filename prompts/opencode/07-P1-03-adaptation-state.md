# P1-03 — AdaptationState

Crie estado computacional de adaptação nos domínios:
- aerobic_base
- threshold
- vo2max
- muscular_endurance
- anaerobic
- neuromuscular

Valores de 0 a 1. Cada sessão deve possuir vetor de contribuição, com atualização, decaimento temporal e saturação.

Exemplo conceitual:
Z2 → aerobic_base +++;
Threshold → threshold +++;
VO2 → vo2max +++;
Sprint → neuromuscular +++.

Importante: esses valores são heurísticas computacionais, não medições fisiológicas.

Teste atualização, decaimento, saturação, sessões neutras e combinação de estímulos.

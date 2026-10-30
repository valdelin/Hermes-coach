# Revisão de treino na TUI — Specification

## Problem Statement

O calendário mostra o plano e as atividades, mas não permite revisar a estrutura
de um treino futuro, comparar um treino concluído ao alvo do plano ou entender a
carga da semana. O atleta precisa abrir a TUI e obter essas leituras sem que a
interface prescreva, altere ou publique dados.

## Goals

- [ ] Exibir o treino planejado completo ao abrir um dia futuro ou não realizado.
- [ ] Comparar plano e atividade realizada por métricas factuais no detalhe do dia.
- [ ] Exibir totais e distribuição de carga da semana na visão semanal.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Unificar o mini-gráfico do card com o gráfico detalhado | Débito visual explicitamente adiado pelo atleta. |
| Alterar plano, FTP ou calendário remoto | Esta entrega é estritamente de leitura. |
| Inferir cumprimento fisiológico ou recomendar mudança de treino | A UI não substitui o motor determinístico. |
| Sobrepor séries temporais de alvo e potência real | Primeira entrega usa comparação lado a lado. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Comparação no detalhe | Colunas lado a lado para plano e realizado. | Evita alinhar streams de duração diferente e mantém leitura compacta. | Sim |
| Status do plano sem atividade | Dia anterior a hoje é perdido; hoje e futuro são pendentes. | Regra escolhida para a semana em curso. | Sim |
| Distribuição por zona realizada | Calcular com streams de potência quando estiverem disponíveis; caso contrário declarar indisponível, sem estimar. | Não inventa dados de execução. | Sim |
| Falha do Intervals.icu | Manter plano local e métricas disponíveis, com estado explícito para a parte indisponível. | A TUI é local-first e leitura não deve falhar integralmente. | Sim |
| Histórico de semanas | Aplicar a mesma regra: plano sem atividade em dia passado é perdido. | Mantém semântica estável ao navegar. | Sim |

**Open questions:** none, all choices are resolved or logged above.

---

## User Stories

### P1: Detalhe de treino planejado

**User Story:** Como atleta, quero abrir um treino planejado e visualizar sua
estrutura, para executar a sessão sem interpretar o JSON do plano.

**Why P1:** O calendário só é operacional se o card levar ao conteúdo prescrito.

**Acceptance Criteria:**

1. WHEN o atleta abrir um dia com plano e sem atividade realizada, THEN the TUI SHALL mostrar foco, duração planejada, TSS planejado e os blocos de aquecimento, trabalho, recuperação e desaquecimento que existirem no plano. <!-- event-driven -->
2. WHERE o treino planejado tiver parâmetros suficientes para perfil de potência, the TUI SHALL mostrar um gráfico de potência-alvo por bloco, colorido com a mesma tabela de zonas do detalhe. <!-- optional-feature -->
3. IF um campo opcional do plano estiver ausente, THEN the TUI SHALL omitir somente a linha dependente sem falhar ao abrir o detalhe. <!-- unwanted-behavior -->

**Independent Test:** abrir um `planned` fixture com blocos e confirmar que foco, duração, TSS, blocos e perfil aparecem; repetir com parâmetro opcional ausente.

---

### P1: Comparação factual plano × realizado

**User Story:** Como atleta, quero comparar o treino planejado à atividade feita
no mesmo dia, para reconhecer aderência sem receber prescrição inventada.

**Why P1:** É o feedback diário central do coach.

**Acceptance Criteria:**

1. WHEN o atleta abrir um dia com plano e atividade realizada, THEN the TUI SHALL mostrar colunas Planejado e Realizado com duração e TSS. <!-- event-driven -->
2. WHERE a atividade realizada tiver potência média ou normalizada, the TUI SHALL mostrar esse valor somente na coluna Realizado e identificar sua natureza. <!-- optional-feature -->
3. WHEN houver plano e atividade realizada, THEN the TUI SHALL mostrar a diferença aritmética de duração e TSS como dado factual, sem classificar adaptação, sucesso ou falha fisiológica. <!-- event-driven -->
4. IF uma métrica realizada não estiver disponível, THEN the TUI SHALL mostrar `—` para essa métrica e manter as métricas restantes visíveis. <!-- unwanted-behavior -->

**Independent Test:** abrir um `planned + done` fixture com duração, TSS e potência e confirmar colunas e diferenças; repetir removendo potência.

---

### P1: Resumo semanal

**User Story:** Como atleta, quero ver os totais semanais de plano e execução,
para entender volume, carga e pendências da semana em uma única tela.

**Why P1:** A semana é a unidade operacional do plano.

**Acceptance Criteria:**

1. WHEN a visão semanal for aberta ou a semana for alterada, THEN the TUI SHALL mostrar totais Planejado e Realizado de duração e TSS para os sete dias visíveis. <!-- event-driven -->
2. WHEN a visão semanal for aberta ou a semana for alterada, THEN the TUI SHALL mostrar as contagens de realizado, perdido, pendente e extra para os sete dias visíveis. <!-- event-driven -->
3. WHILE um dia planejado sem atividade estiver antes da data atual, the TUI SHALL contá-lo como perdido. <!-- state-driven -->
4. WHILE um dia planejado sem atividade estiver na data atual ou depois dela, the TUI SHALL contá-lo como pendente. <!-- state-driven -->
5. WHEN uma atividade sem plano existir na semana visível, THEN the TUI SHALL contá-la como extra e somar sua duração e TSS ao total Realizado. <!-- event-driven -->
6. WHEN houver dados de parâmetros do plano, THEN the TUI SHALL mostrar distribuição planejada de tempo por zona baseada nesses parâmetros. <!-- event-driven -->
7. WHERE streams de potência das atividades da semana estiverem disponíveis, the TUI SHALL mostrar distribuição realizada de tempo por zona calculada dos streams. <!-- optional-feature -->
8. IF streams realizados não estiverem disponíveis, THEN the TUI SHALL identificar a distribuição realizada como indisponível sem estimá-la. <!-- unwanted-behavior -->

**Independent Test:** carregar semana fixture com plano passado/futuro, realizado e extra e confirmar totais, status e zonas planejadas; repetir sem streams para confirmar estado indisponível.

---

## Edge Cases

- IF `plan.json` não existir ou não contiver treino no dia, THEN the TUI SHALL manter a atividade realizada como extra ou informar que não há plano.
- IF o Intervals.icu falhar durante a leitura de streams, THEN the TUI SHALL preservar a comparação e o resumo local que já estiverem disponíveis.
- WHEN duração ou TSS forem zero ou inválidos, THEN the TUI SHALL tratá-los como ausentes e não como carga positiva.

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| UIR-01 | P1: Detalhe planejado | Execute | Implementing |
| UIR-02 | P1: Detalhe planejado | Tasks | Pending |
| UIR-03 | P1: Detalhe planejado | Execute | Implementing |
| UIR-04 | P1: Plano × realizado | Execute | Implementing |
| UIR-05 | P1: Plano × realizado | Execute | Implementing |
| UIR-06 | P1: Plano × realizado | Execute | Implementing |
| UIR-07 | P1: Plano × realizado | Execute | Implementing |
| UIR-08 | P1: Resumo semanal | Execute | Implementing |
| UIR-09 | P1: Resumo semanal | Execute | Implementing |
| UIR-10 | P1: Resumo semanal | Execute | Implementing |
| UIR-11 | P1: Resumo semanal | Execute | Implementing |
| UIR-12 | P1: Resumo semanal | Execute | Implementing |
| UIR-13 | P1: Resumo semanal | Execute | Implementing |
| UIR-14 | P1: Resumo semanal | Execute | Implementing |
| UIR-15 | P1: Resumo semanal | Execute | Implementing |

**Coverage:** 15 total, 0 mapped to tasks, 15 unmapped.

## Success Criteria

- [ ] O atleta revisa um treino futuro, um dia concluído e uma semana sem abrir o JSON ou o site do Intervals.icu.
- [ ] Dados ausentes e falhas remotas não se apresentam como execução ou distribuição estimada.
- [ ] A TUI mantém a prescrição sob autoridade do motor determinístico.

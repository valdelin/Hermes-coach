# Histórico planejado e execução em outra data — Specification

## Problem Statement

O build substitui a janela em `plan.json`, e o calendário deixa de mostrar
prescrições antigas. A TUI também agrupa atividades por data sem considerar
vínculos explícitos, podendo contar um registro manual duplicado e apresentar
uma execução atrasada como atividade extra.

## Goals

- [ ] Recuperar e exibir prescrições históricas disponíveis com procedência.
- [ ] Distinguir data planejada da data real de uma execução vinculada.
- [ ] Evitar contagem duplicada sem excluir atividades manuais legítimas.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Alterar eventos ou atividades no Intervals.icu | A correção do calendário é somente leitura. |
| Inferir vínculo por nome ou proximidade de data | Não constitui evidência suficiente. |
| Alterar prescrição ou regras fisiológicas | O motor determinístico permanece fonte de decisão. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Execução fora da data | Manter 02/11 como não realizado no dia e identificar execução vinculada em 03/11. | Preserva as duas datas reais. | Sim |
| Duplicata manual | Suprimir apenas se houver vínculo explícito ao mesmo evento e outra atividade for a pareada pelo evento. | Não descartar atividades manuais legítimas. | Sim |
| Prescrição histórica | Usar evento remoto identificável como Hermes quando o plano local não contiver o dia, sem gravar no plano. | O evento de 02/11 ainda existe no provider. | Sim |
| Campos não disponíveis | Mostrar indisponível e não inventar parâmetros ou zonas. | Integridade de dados. | Sim |
| Falha do provider | Preservar leitura local e indicar histórico remoto indisponível. | Local-first. | Sim |

**Open questions:** none; assumptions are recorded above.

## User Stories

### P1: Prescrição histórica

**User Story:** Como atleta, quero rever o treino planejado mesmo depois de um build.

**Why P1:** O plano atual não preserva a janela anterior.

**Acceptance Criteria:**

1. WHEN um evento histórico Hermes disponível não existir no plano local THEN the TUI SHALL mostrá-lo no dia planejado com identificação de origem remota. [HIST-01]
2. WHERE o evento fornecer estrutura de potência suficiente THEN the TUI SHALL exibir o gráfico planejado usando essa estrutura. [HIST-02]
3. IF a estrutura não estiver disponível ou não puder ser interpretada com segurança THEN the TUI SHALL indicar gráfico planejado indisponível. [HIST-03]
4. IF a consulta remota falhar THEN the TUI SHALL manter os dados locais visíveis e informar a indisponibilidade do histórico remoto. [HIST-04]

**Independent Test:** abrir 02/11 em fixture sem prescrição local e com evento remoto estruturado; verificar origem e gráfico.

### P1: Execução vinculada em outra data

**User Story:** Como atleta, quero reconhecer quando realizei em outro dia um treino planejado anteriormente.

**Why P1:** A data de execução não pode apagar a data de prescrição.

**Acceptance Criteria:**

1. WHEN o evento planejado estiver explicitamente pareado a atividade de outra data THEN the TUI SHALL mostrar no dia planejado que não houve execução naquele dia e informar a data vinculada. [HIST-05]
2. WHEN a atividade vinculada ocorrer em outra data THEN the TUI SHALL identificá-la como execução atrasada daquele evento, sem classificá-la como extra. [HIST-06]
3. WHEN houver registro manual e atividade pareada distintos vinculados explicitamente ao mesmo evento THEN the TUI SHALL contar somente a atividade pareada como execução. [HIST-07]
4. WHEN uma atividade manual não tiver duplicata comprovada THEN the TUI SHALL preservá-la como atividade. [HIST-08]
5. The TUI SHALL contar cada atividade real uma única vez nos totais semanais da data efetiva. [HIST-09]
6. IF não houver vínculo explícito THEN the TUI SHALL abster-se de associar treino e atividade apenas por nome ou data. [HIST-10]

**Independent Test:** usar evento de 02/11 pareado ao FIT de 03/11 e registro manual duplicado; conferir cards, detalhes e totais.

## Edge Cases

- IF houver múltiplos eventos ou atividades no mesmo dia THEN the TUI SHALL evitar descartá-los silenciosamente. [HIST-11]
- IF dados remotos divergirem do plano local para o mesmo evento THEN the TUI SHALL manter a prescrição local e identificar a divergência. [HIST-12]
- The TUI SHALL executar consultas e projeções sem alterar arquivos de plano ou dados remotos. [HIST-13]

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| HIST-01 | Prescrição histórica | Design | Pending |
| HIST-02 | Prescrição histórica | Design | Pending |
| HIST-03 | Prescrição histórica | Design | Pending |
| HIST-04 | Prescrição histórica | Design | Pending |
| HIST-05 | Execução em outra data | Design | Pending |
| HIST-06 | Execução em outra data | Design | Pending |
| HIST-07 | Execução em outra data | Design | Pending |
| HIST-08 | Execução em outra data | Design | Pending |
| HIST-09 | Execução em outra data | Design | Pending |
| HIST-10 | Execução em outra data | Design | Pending |
| HIST-11 | Edge cases | Design | Pending |
| HIST-12 | Edge cases | Design | Pending |
| HIST-13 | Edge cases | Design | Pending |

**Coverage:** 13 total; 0 mapped to tasks; 13 unmapped.

## Success Criteria

- [ ] O cenário real de 02/11 e 03/11 é reproduzido por fixture determinístico.
- [ ] Prescrição e execução mantêm suas datas e não há dupla contagem.
- [ ] A leitura não altera dados locais ou remotos.

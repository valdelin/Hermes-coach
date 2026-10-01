# P0-02: Separar Periodização de TSB

## Problem Statement

O `build_plan()` escolhe hoje o template semanal diretamente pelo TSB. Isso
permite que uma variação diária de fadiga mude a composição planejada do ciclo,
misturando periodização com autoregulação. O plano precisa definir a fase e a
semana-alvo antes de aplicar TSB e readiness à sessão do dia.

## Goals

- [ ] Representar o estado do plano com `TrainingPlanState`.
- [ ] Derivar fase e template semanal sem usar TSB.
- [ ] Usar TSB/readiness somente para adaptar a sessão inicial do plano.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Persistir `TrainingPlanState` em `plan.json` | O estado é calculável no build; mudar formato persistido não é necessário. |
| Alterar CTL/ATL/TSB do Intervals | O Intervals continua sendo a fonte autoritativa dessas métricas. |
| Criar novos modelos de periodização | O escopo usa os goals, templates e taper já existentes. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fase sem data de início persistida | `back-to-fitness` usa `base`, `active-off-season` usa `transition`, demais goals usam `build`; `race` entra em `taper` dentro de 7 dias da prova. | O prompt não introduz cronograma persistido e o formato atual deve permanecer compatível. | y |
| Semana do ciclo | Semana ISO do início do build, em ciclo de quatro semanas. | Fornece um valor determinístico sem inventar histórico de fase. | y |
| Autoregulação no build | TSB abaixo de -15 ou readiness desfavorável troca somente a primeira sessão de qualidade por recuperação Z2 curta. | Representa ajuste diário; as sessões futuras mantêm o objetivo da fase. | y |

**Open questions:** none - all resolved or logged above.

## User Stories

### P1: Plano por fase

**User Story**: Como treinador, quero que o plano semanal venha da fase do
objetivo para que uma variação de TSB não reescreva o macrociclo.

**Why P1**: A separação é o objetivo central do P0-02.

**Acceptance Criteria**:

1. The system SHALL expose `TrainingPlanState` with `goal`, `phase`, `week_in_phase`, `cycle_week`, `planned_load`, `current_load`, `tsb`, and `readiness`.
2. WHEN two builds use the same goal and phase with different TSB values THEN the system SHALL keep the same phase and weekly target.
3. WHEN a race is within seven days THEN the system SHALL select the `taper` phase without consulting TSB.

**Independent Test**: Construir estados equivalentes com TSB diferente e
comparar fase/template; construir estado `race` próximo da prova.

### P1: Autoregulação da sessão

**User Story**: Como atleta, quero que fadiga diária adapte apenas a sessão
imediata para que o plano preserve seus objetivos de fase.

**Why P1**: TSB/readiness deve proteger a execução sem decidir o macrociclo.

**Acceptance Criteria**:

1. WHEN TSB is below -15 THEN the system SHALL replace the first quality session with a Z2 recovery session while keeping the plan phase unchanged.
2. WHEN readiness signals are unfavorable THEN the system SHALL replace the first quality session with a Z2 recovery session while keeping the plan phase unchanged.
3. WHEN TSB is -15 or greater and readiness is favorable THEN the system SHALL execute the planned session unchanged.

**Independent Test**: Construir planos com mesma fase e TSB/readiness distintos;
comparar a primeira sessão e a fase.

## Edge Cases

- IF readiness is absent THEN the system SHALL treat readiness as favorable.
- WHEN the first session is already Z2 THEN the system SHALL keep it unchanged.

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PERIOD-01 | Plano por fase | Implementing | Verified |
| PERIOD-02 | Plano por fase | Implementing | Verified |
| PERIOD-03 | Plano por fase | Implementing | Verified |
| PERIOD-04 | Autoregulação da sessão | Implementing | Verified |
| PERIOD-05 | Autoregulação da sessão | Implementing | Verified |
| PERIOD-06 | Autoregulação da sessão | Implementing | Verified |
| PERIOD-07 | Edge case | Implementing | Verified |
| PERIOD-08 | Edge case | Implementing | Verified |

**Coverage:** 8 total, 8 mapped to implementation tests.

## Success Criteria

- [ ] TSB não altera a fase ou o template semanal.
- [ ] TSB/readiness desfavoráveis adaptam somente a primeira sessão de qualidade.
- [ ] A suíte completa passa.

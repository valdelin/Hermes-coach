# P0-02 — Separar Periodização de TSB

Implemente uma separação arquitetural entre periodização e autoregulação diária.

## Estado
Criar `TrainingPlanState` com:
- goal
- phase
- week_in_phase
- cycle_week
- planned_load
- current_load
- tsb
- readiness

## Fluxo
`GOAL → TRAINING PHASE → PHASE OBJECTIVES → WEEK TARGET → TSB/READINESS → SESSION MODIFICATION`.

TSB deve modificar a sessão, não determinar sozinho a fase do macrociclo.

## Testes
- Alterar TSB não pode mudar automaticamente a fase.
- TSB baixo pode reduzir/adaptar a sessão.
- TSB adequado permite executar a sessão planejada.

Documente a distinção entre periodização e autoregulação e cite Galán-Rioja et al. (2023).

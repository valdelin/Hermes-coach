# P1-04 — TrainingDecisionEngine

Crie o motor central de decisão adaptativa.

## Fluxo
`GOAL → PHASE → LIMITATIONS/ADAPTATION PRIORITIES → RECENT LOAD → READINESS → DESIRED STIMULUS → DOSE → PROGRESSION STEP → SAFETY ADJUSTMENTS → WORKOUT`.

## TrainingDecision
- goal
- phase
- primary_adaptation
- secondary_adaptation
- selected_zone
- workout_family
- progression_step
- planned_duration
- planned_load
- readiness_modifier
- rationale
- confidence

A decisão deve responder “por que este estímulo agora?” e considerar objetivo, fase, adaptações, carga, readiness, progressão e segurança.

Evite regras baseadas somente em zona ou TSB.

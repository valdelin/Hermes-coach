# P0-03 — TrainingPhase

Crie uma abstração explícita de fase de treinamento.

## Enum
`BASE`, `BUILD`, `SPECIFIC`, `PEAK`, `RECOVERY`, `TEST`.

Crie `TrainingPhaseEngine`.

Cada fase deve possuir:
- objective
- duration
- priority_stimuli
- secondary_stimuli
- load_limits
- progression_criteria
- deload_criteria
- exit_criteria

As durações devem ser configuráveis, sem codificar uma duração universal.

Crie testes de criação, permanência, transição, deload, recovery e test.

Na documentação, deixe claro que a arquitetura é inspirada em princípios de periodização e não representa uma sequência fisiológica universal.

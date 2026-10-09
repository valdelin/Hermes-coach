# P0-04 — ProgressionEngine

Crie um motor de progressão por família de estímulo.

## Famílias
`SWEET_SPOT`, `THRESHOLD`, `VO2MAX`, `ENDURANCE`, `ANAEROBIC`.

Modele progressão por duração, repetições, intensidade ou redução de recuperação. Não aumente todas simultaneamente.

Exemplos de templates:
- Sweet Spot: 3x8 → 3x10 → 3x12 → deload → 2x15 → 3x15.
- Threshold: 3x8 → 3x10 → 3x12 → 2x15 → 3x15.
- VO2: 4x3 → 5x3 → 4x4 → 5x4.

Crie `CompletionScore` usando potência-alvo, tempo completado, RPE, FC e interrupções/falhas.

Classifique `COMPLETED`, `PARTIAL`, `FAILED`, `EASY`.

Só progrida após sucesso. Em PARTIAL/FAILED, repita, reduza ou ajuste.

Documente as sequências como heurísticas do sistema, não protocolos universais.

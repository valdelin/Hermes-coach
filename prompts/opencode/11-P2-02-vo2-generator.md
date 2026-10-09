# P2-02 — VO2WorkoutGenerator

Crie gerador estruturado de treinos VO2max.

Modelo:
- interval_duration
- repetitions
- work_power_range
- recovery_duration
- recovery_power
- total_work_time
- progression_step

Use faixa configurável inicialmente em torno de 106–120% FTP, sem fixar 115% universalmente.

Permita progressão por duração, tempo total, repetições e intensidade, sem aumentar tudo simultaneamente.

Famílias:
`LONG_INTERVALS`, `SHORT_INTERVALS`, `VARIABLE_INTERVALS`.

Templates: 4x4, 5x3, 3x5. Não trate como protocolos universais.

Avalie intensidade + duração + recuperação + trabalho acumulado.

Referências: meta-análise/revisão de 2026 sobre HIIT/VO2max, PMID 42237396; network meta-analysis, PMID 42482078.

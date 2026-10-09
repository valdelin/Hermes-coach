# P2-01 — Critical Power / W'

Adicione CP e W' como métricas complementares ao FTP.

Crie `CriticalPowerProfile`:
- critical_power
- w_prime
- protocol
- confidence
- test_dates

Funções:
`estimate_cp()`, `estimate_w_prime()`, `work_above_cp()`, `w_prime_balance()`, `w_prime_reconstitution()`.

Só calcule quando houver dados suficientes.

Use CP/W' para esforços acima do limiar, Z6, HIIT e análise power-duration. Não substitua FTP automaticamente por CP e nunca trate os dois como equivalentes.

Referência principal: revisão sobre Critical Power/W', W' e reconstituição, PMID 32899777.

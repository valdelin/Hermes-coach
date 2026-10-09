# P1-02 — AthletePhysiologicalProfile

Crie um modelo fisiológico explícito.

## Campos
`ftp`, `ftp_source`, `ftp_confidence`, `critical_power`, `w_prime`, `vo2max`, `max_hr`, `threshold_hr`, `resting_hr`, `hrv_baseline`, `weekly_training_hours`, `training_days`, `training_age`, `preferred_long_day`.

`ftp_source`: USER, FTP20, FTP60, RAMP, CP_ESTIMATE, PERFORMANCE_ESTIMATE.

`ftp_confidence`: LOW, MEDIUM, HIGH.

Não trate FTP como sinônimo de MLSS, LT, CP ou RCP. CP/W' e VO2max são opcionais. Preserve atletas que possuem somente FTP.

Documente as limitações de intercambialidade entre FTP e marcadores fisiológicos.

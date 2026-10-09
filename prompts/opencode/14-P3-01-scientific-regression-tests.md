# P3-01 — Scientific Regression Tests

Crie `tests/scientific/` com:
- `test_training_load.py`
- `test_periodization.py`
- `test_progression.py`
- `test_readiness.py`
- `test_adaptation.py`
- `test_ftp.py`
- `test_critical_power.py`
- `test_vo2.py`
- `test_intensity_distribution.py`

Teste propriedades/invariantes, não apenas execução.

Cobrir:
- TSS;
- CTL;
- ATL;
- TSB;
- progressão;
- deload;
- transição de fases;
- distribuição;
- readiness;
- adaptação;
- confiança do FTP;
- CP/W';
- VO2;
- recuperação.

Preserve os testes existentes, adicione casos-limite e execute a suíte completa.

O objetivo é impedir que futuras mudanças transformem heurísticas documentadas em regras fisiológicas rígidas sem justificativa.

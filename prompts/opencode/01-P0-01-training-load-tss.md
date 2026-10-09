# P0-01 — Training Load / TSS

Audite e corrija o cálculo de carga do Hermes Coach.

## Objetivo
Separar claramente `power_training_load`, `estimated_tss`, `external_load` e `internal_load`, preservando compatibilidade com CTL, ATL e TSB.

## Implementação
- Quando houver NP: `IF = NP / FTP` e `TSS ≈ duração_em_horas × IF² × 100`.
- Não fabrique NP para treinos curtos ou apenas planejados.
- Diferencie TSS estimado do treino planejado de TSS calculado após execução.
- Documente as limitações de TSS/IF para HIIT curto.

## Testes
1h@100%=100 TSS; 1h@70%=49; 1h@75%=56,25; 2h@70%=98. Teste também treino variável, HIIT curto, FTP inválido/ausente, duração zero e potência zero.

## Documentação
Atualize `EMBASAMENTO-CIENTIFICO.md` sobre IF, NP, TSS, CTL, ATL e TSB. Diferencie metodologia operacional de evidência científica.

## Referências
TrainingPeaks/Coggan para a definição operacional de IF/NP/TSS; Galán-Rioja et al. (2023) para contexto de carga e periodização.

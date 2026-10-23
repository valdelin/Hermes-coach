# Configuração de duração de treino indoor

## Problem Statement

`WEEKLY_HOURS` escala a semana, mas não limita um treino individual. Um atleta
pode ter disponibilidade semanal sem querer sessões longas. O teto não pode
transformar VO₂ ou limiar em um treino de 180 min.

## Goals

Configurar uma duração por sessão indoor, com padrão de 180 min e faixa válida de
30–180 min. Quando uma sessão futura não couber no teto, compactar duração sem
reduzir potência/zona declarada.

## Out of Scope

| Item | Razão |
|---|---|
| Alterar foco ou potência | O teto controla tempo, não intenção/intensidade. |
| Longão variável/específico | Política separada em `TREINOS-LONGOS-INDOOR-POTENCIA-2026-10-23.md`. |
| Publicar no Intervals | A configuração é validada localmente. |

## Assumptions & Open Questions

| Decisão | Valor |
|---|---|
| Default | 180 min |
| Faixa configurável | 30–180 min, inclusiva |
| Escopo | Toda sessão indoor futura; sessão de hoje já publicada é preservada |
| Compressão | Warm-up/cooldown até 5 min; work/recovery até 1 min; potência/zona preservadas |
| Preferência individual mínima | `MIN_REGULAR_DURATION_MINUTES`; ausente não altera o comportamento legado |
| Qualidade abaixo da preferência | Recuperação Z2 na duração preferida; não se reduz potência para forçar o orçamento |

**Open questions:** none - all resolved above.

## User Stories

### P1: Limite configurável ⭐ MVP

**User Story**: As an athlete, I want a per-workout indoor duration limit so that weekly availability does not create a session longer than I can perform.

**Why P1**: It is the requested safety and usability boundary.

- **DUR-01**: WHERE `MAX_WORKOUT_DURATION_MINUTES` estiver ausente, o sistema SHALL usar 180 min como teto por sessão indoor.
- **DUR-02**: WHEN `MAX_WORKOUT_DURATION_MINUTES` estiver entre 30 e 180, inclusivos, o sistema SHALL usar o valor como teto por sessão indoor futura.
- **DUR-03**: IF `MAX_WORKOUT_DURATION_MINUTES` estiver fora de 30–180 ou for inválido, THEN o sistema SHALL rejeitar a configuração com aviso e manter o default de 180 min.

### P1: Compactação de sessão

**User Story**: As an athlete, I want a short session to preserve its declared intensity so that limiting time does not silently change its training intent.

**Why P1**: The 30-minute lower bound must remain usable for quality sessions.

- **DUR-04**: WHEN a duração planejada exceder o teto, THEN o sistema SHALL gerar duração total menor ou igual ao teto sem alterar `on_power` ou o foco declarado.
- **DUR-05**: WHEN for necessária compactação, THEN o sistema SHALL manter warm-up e cooldown com pelo menos 5 min cada e work/recovery existentes com pelo menos 1 min cada.
- **DUR-06**: WHILE uma sessão de hoje vier preservada de plano existente, o sistema SHALL mantê-la sem aplicar o novo teto.

### P2: Preferência individual mínima

**User Story**: As an athlete, I want a minimum duration preference for regular sessions so that my calendar does not contain a quality workout too short to be useful to me.

- **DUR-07**: WHERE `MIN_REGULAR_DURATION_MINUTES` estiver configurado, IF uma sessão qualitativa regular continuar abaixo dessa duração após as proteções de orçamento, THEN o sistema SHALL substituí-la por recuperação Z2 na duração configurada.
- **DUR-08**: WHILE `MIN_REGULAR_DURATION_MINUTES` estiver ausente, o sistema SHALL manter a prescrição legada sem aplicar a substituição por duração.

## Requirement Traceability

| Requirement ID | Story | Status |
|---|---|---|
| DUR-01 | Limite configurável | Verified |
| DUR-02 | Limite configurável | Verified |
| DUR-03 | Limite configurável | Verified |
| DUR-04 | Compactação de sessão | Verified |
| DUR-05 | Compactação de sessão | Verified |
| DUR-06 | Compactação de sessão | Verified |
| DUR-07 | Preferência individual mínima | Verified |
| DUR-08 | Preferência individual mínima | Verified |

## Success Criteria

- O build offline gera Z2, Endurance, Sweet Spot, Threshold e VO₂ entre 30 e 180 min.
- A compressão de um Threshold e de um VO₂ em teto de 30 min preserva foco e potência.
- Nenhuma configuração inválida produz sessão acima de 180 min.

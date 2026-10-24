# Feature: Pre-push sanity check (VAR-03)

## Objetivo

Adicionar uma barreira de integridade ao `training_plan.py push` para impedir a publicação de sessões obviamente inconsistentes com as regras vigentes. A checagem **só alerta/bloqueia**, nunca reescreve o plano.

## Contexto

- DUR-01: teto configurável por sessão (`MAX_WORKOUT_DURATION_MINUTES`, 30–180). 180 é default/teto absoluto.
- Preferência individual: `MIN_REGULAR_DURATION_MINUTES` (alerta quando não respeitada).
- VAR-01: rotação por semana ISO preserva `focus` e piso de zona.
- Taper: evitar qualidade muito próxima da prova.
- Treino já publicado hoje deve continuar preservado pelo fluxo existente.

## Requisitos

### P1: Integração

- **SAN-01**: WHEN `training_plan.py push` for executado, o sistema SHALL rodar o sanity check **antes** de criar/remover eventos no Intervals.icu.
- **SAN-01b**: WHEN `push --dry-run` for usado, o sistema SHALL reportar WARN/BLOCK sem abortar a simulação.
- **SAN-01c**: WHEN houver ao menos um `BLOCK` e **não** for `--dry-run`, o sistema SHALL abortar a publicação com relatório claro e sem chamar a API para mutação.

### P2: Duração e configuração

- **SAN-02**: IF a duração total da sessão (warmup + work/recovery + cooldown) > `MAX_WORKOUT_DURATION_MINUTES` (em segundos), THEN o sistema SHALL emitir `BLOCK`.
- **SAN-06**: WHERE `MIN_REGULAR_DURATION_MINUTES` estiver configurado, IF uma sessão **qualitativa regular** tiver duração < `MIN_REGULAR_DURATION_MINUTES`, THEN o sistema SHALL emitir `WARN`. Esta checagem **não** deve auto-corrigir.

### P3: Taper / proximidade de prova

- **SAN-03**: WHERE `RACE_DATE` existir, IF a sessão for **qualitativa** (`sweetspot`, `threshold`, `vo2max`) e houver `<= 2` dias entre o dia da sessão e `RACE_DATE` (D-0, D-1, D-2), THEN o sistema SHALL emitir `BLOCK`. Sessões `zone2`/`endurance` não são bloqueadas por esta regra.

### P4: Estrutura e piso de zona

- **SAN-04**: IF uma sessão **qualitativa** não possuir estrutura mínima coerente (sem `warmup_sec > 0` ou sem `cooldown_sec > 0` ou sem blocos de trabalho válidos), THEN o sistema SHALL emitir `BLOCK`.
- **SAN-05**: IF uma sessão com `focus` qualitativo tiver potência alvo abaixo do **piso declarado da zona** para aquele `focus` (com tolerância numérica 1%), THEN o sistema SHALL emitir `BLOCK`.

## Critérios de aceite

| ID | Critério | Estado |
|---|---|---|
| SAN-01 | Integrado ao `push` antes de mutação | Planned |
| SAN-01b | Funciona em `--dry-run` (só relatório) | Planned |
| SAN-01c | Aborta com BLOCK sem mutação fora de dry-run | Planned |
| SAN-02 | Teto por duração respeitado/barrado | Planned |
| SAN-03 | Bloqueio de qualidade em D-0/D-1/D-2 de prova | Planned |
| SAN-04 | Estrutura mínima válida | Planned |
| SAN-05 | Piso de zona preservado | Planned |
| SAN-06 | Alerta para preferência individual mínima | Planned |

## Não objetivos

- Reescrever `plan.json`, workouts ou eventos
- "Ajustar" taper automaticamente
- Alterar a lógica de compactação existente (DUR-01)
- Mexer em prontidão/reconcile

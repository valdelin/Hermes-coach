# Rotação semanal de variantes de treino

## Problem Statement

`_block_for()` reinicia a rotação de variantes a cada `build_plan()`, porque usa
o índice local do dia. Duas semanas com a mesma sequência de focos podem receber
o mesmo formato de bloco, apesar de o plano já declarar variantes para evitar
monotonia.

## Goals

- [ ] Variar o formato do mesmo foco entre semanas ISO consecutivas quando há `GOAL`.
- [ ] Preservar foco, piso de zona, orçamento e comportamento de planos sem `GOAL`.

## Out of Scope

| Item | Razão |
|---|---|
| Consultar sessões concluídas | É VAR-02, posterior a medir VAR-01 em plano real. |
| Alterar distribuição de focos | VAR-01 muda formato, não intenção semanal. |
| Adicionar novas variantes | Catálogo atual permanece inalterado. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|---|---|---|---|
| Âncora temporal | Semana ISO do dia da sessão | Não reinicia ao chamar build e é determinística sem persistência nova | y |
| Escopo | Somente `GOAL` presente | Preserva comportamento legado sem GOAL | y |

**Open questions:** none - all resolved above.

## User Stories

### P1: Variação entre semanas ⭐ MVP

**User Story**: As an athlete, I want the same weekly focus to use another block format in the next week so that the plan is less repetitive without changing its training intent.

**Why P1**: Resolve a repetição observada com mudança local e sem nova heurística fisiológica.

1. **VAR-01**: WHEN duas sessões do mesmo foco ocuparem a mesma posição em semanas ISO consecutivas num plano com `GOAL`, THEN o sistema SHALL escolher variantes diferentes quando houver mais de uma variante disponível.
2. **VAR-02**: WHILE `GOAL` estiver ausente, o sistema SHALL manter o template legado do foco sem rotação de variantes.
3. **VAR-03**: The system SHALL preserve `focus` and the declared-zone floor when applying the weekly variant offset.

## Requirement Traceability

| Requirement ID | Story | Status |
|---|---|---|
| VAR-01 | Variação entre semanas | Verified |
| VAR-02 | Variação entre semanas | Verified |
| VAR-03 | Variação entre semanas | Verified |

## Success Criteria

- [ ] Um build offline de duas semanas demonstra variantes diferentes para a mesma posição/foco em semanas consecutivas.
- [ ] O mesmo cenário sem `GOAL` é byte-equivalente ao template legado.

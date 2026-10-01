# P0-02: Separar Periodizacao de TSB - Validation

**Date**: 2026-10-01
**Spec**: `.specs/features/p0-02-periodizacao-tsb/spec.md`
**Diff range**: `c144ce7..b4a9548`
**Verifier**: independente (author != verifier)

## Verdict

**PASS**. Os oito requisitos tem asserts sobre o resultado definido na spec,
os gates passam e as tres mutacoes comportamentais solicitadas foram mortas.

## Spec-Anchored Acceptance Criteria

| Requirement | Spec-defined outcome | `file:line` + assertion expression | Result |
| --- | --- | --- | --- |
| PERIOD-01 | `TrainingPlanState` expoe `goal`, `phase`, `week_in_phase`, `cycle_week`, `planned_load`, `current_load`, `tsb` e `readiness`. | `tests/test_periodization_state.py:18-26` - `assertIsInstance(state, TrainingPlanState)` e `assertEqual`/`assertIsNone` para cada campo. | PASS |
| PERIOD-02 | Mesmo goal/fase com TSB distinto mantem a mesma fase e o mesmo alvo semanal. | `tests/test_periodization_state.py:31-32` - `assertEqual(low.phase, adequate.phase)` e `assertEqual(phase_weekly_template(low), phase_weekly_template(adequate))`. | PASS |
| PERIOD-03 | `race` a menos de sete dias seleciona `taper` sem consultar TSB. | `tests/test_periodization_state.py:36` - `assertEqual(training_phase("race", "2026-10-16", day), "taper")`; `training_phase` nao recebe TSB (`src/plan.py:473-486`). | PASS |
| PERIOD-04 | TSB < -15 troca somente a primeira sessao de qualidade por recuperacao Z2 e preserva a fase. | `tests/test_periodization_state.py:46-59` - `assertEqual(low[quality_index]["focus"], FOCUS_ZONE2)`, `assertEqual(low[next_quality], adequate[next_quality])` e igualdade de `phase`. | PASS |
| PERIOD-05 | Readiness desfavoravel troca somente a primeira sessao de qualidade por recuperacao Z2 e preserva a fase. | `tests/test_periodization_state.py:61-72` - `assertEqual(plan[0]["focus"], FOCUS_ZONE2)`, igualdade do foco/potencia da proxima sessao e igualdade de `phase`. | PASS |
| PERIOD-06 | TSB >= -15 com readiness favoravel executa a sessao planejada sem alteracao. | `tests/test_periodization_state.py:74-78` - `assertEqual(actual[0], expected[0])`. | PASS |
| PERIOD-07 | Readiness ausente e favoravel. | `tests/test_periodization_state.py:80-81` - `assertEqual(self._plan(0), self._plan(0, readiness=None))`. | PASS |
| PERIOD-08 | Se a primeira sessao ja e Z2, ela permanece inalterada. | `tests/test_periodization_state.py:83-86` - `assertEqual(adapted[0], planned[0])` compara o workout inteiro sob TSB baixo. | PASS |

**Status**: 8/8 requisitos cobertos pelo resultado definido na spec.

## Discrimination Sensor

Scratch: tres worktrees destacados em `/tmp/opencode`, todos em `b4a9548`;
nenhuma mutacao ocorreu na arvore real. O baseline e o pos-cleanup de
`git status --porcelain` foram identicos.

| Mutation | File:line | Description | Result |
| --- | --- | --- | --- |
| 1 | `src/plan.py:641` | Remove `adapted = True`; todas as sessoes de qualidade passam a ser adaptadas. | Killed - 2 falhas nos asserts `tests/test_periodization_state.py:56,66`. |
| 2 | `src/plan.py:518-519` | Readiness com dados, inclusive favoravel, passa a ser desfavoravel. | Killed - falha no assert `tests/test_periodization_state.py:78`. |
| 3 | `src/plan.py:526` | Uma Z2 planejada sob sinal desfavoravel e trocada pela recuperacao curta. | Killed - falha no assert `tests/test_periodization_state.py:86`. |

**Sensor depth**: targeted, 3 mutacoes comportamentais solicitadas.
**Result**: 3/3 killed - **PASS**.

## Gate Check

- Focused: `python3 -m unittest tests.test_periodization_state -v` -> 8 passed, 0 failed.
- Full: `python3 -m unittest discover -s tests -v` -> 409 passed, 0 failed.
- Diff check: `git diff --check c144ce7..b4a9548` -> exit 0.
- Test-file count: base `c144ce7` 16; target `b4a9548` 17; delta +1.

## Summary

**Overall**: Ready. A logica em `src/plan.py:522-530,635-641` e os testes
em `tests/test_periodization_state.py:46-86` discriminam as fronteiras de
adaptar somente a primeira qualidade, preservar readiness favoravel e nao
alterar uma Z2 planejada.

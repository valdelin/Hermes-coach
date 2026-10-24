# Validation: Pre-push sanity check (VAR-03) — PASS

**Date**: 2026-10-23
**Spec**: `.specs/features/pre-push-sanity-check/spec.md`
**Diff range**: `src/plan_sanity.py`, `src/training_plan.py`, `tests/test_plan_sanity.py`, `.specs/STATE.md`
**Verifier**: local

## Verdict

PASS. Checagem integrada ao `push` antes de mutações, apenas alerta/bloqueio (sem auto-correção). Funciona em `--dry-run` com relatório.

## Acceptance criteria

| ID | Expected | Evidence | Result |
|---|---|---|---|
| SAN-01 | Integrado ao `push` antes de mutação | `src/training_plan.py` — hook em `cmd_push` antes de `push_workouts` | ✅ PASS |
| SAN-01b | `--dry-run` reporta sem abortar | Não aborta em `dry_run` | ✅ PASS |
| SAN-01c | Com `BLOCK` e sem `--dry-run` aborta sem mutação | `return` antes de chamar `push_workouts` | ✅ PASS |
| SAN-02 | Duração > `MAX_WORKOUT_DURATION_MINUTES` -> BLOCK | `src/plan_sanity.py` | ✅ PASS |
| SAN-03 | Qualidade em D-0/D-1/D-2 de `RACE_DATE` -> BLOCK (só qualidade) | `delta >=0 and delta <= 2` | ✅ PASS |
| SAN-04 | Estrutura mínima -> BLOCK | warmup/cooldown/repeats/on_sec | ✅ PASS |
| SAN-05 | Potência abaixo do piso da zona -> BLOCK | `coach.ZONE_BANDS` | ✅ PASS |
| SAN-06 | Abaixo de `MIN_REGULAR_DURATION_MINUTES` -> WARN | não bloqueia | ✅ PASS |

## Tests

```text
Ran 7 tests in 0.06s
OK
```

Full regression: `tests.test_plan`, `tests.test_application`, `tests.test_training_plan` — **OK**.

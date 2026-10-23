# Workout Variant Rotation Validation

**Date**: 2026-10-23
**Spec**: `.specs/features/workout-variant-rotation/spec.md`
**Diff range**: uncommitted working tree; verified slice: `src/plan.py` and `tests/test_plan.py`
**Verifier**: independent sub-agent (author ≠ verifier)

## Verdict: PASS

## Spec-Anchored Acceptance Criteria

| Requirement | Spec-defined outcome | Evidence | Result |
| --- | --- | --- | --- |
| VAR-01 | Same focus and position in consecutive ISO weeks with `GOAL` use different variants when multiple variants exist. | `src/plan.py:1138-1141` derives an ISO-week offset and passes it to `_block_for`; `src/plan.py:1277-1278` selects `(slot + week_offset) % len(variants)`. `tests/test_plan.py:1441-1446` builds 2026-W43/W44 with `goal="ftp-builder"` and asserts equal focus plus different params. | PASS |
| VAR-02 | Without `GOAL`, keep the legacy focus template with no variant rotation. | `src/plan.py:1275-1276` returns `templates()[focus]` when `goal is None`. `tests/test_plan.py:1451-1454` builds the same scenario without `GOAL` and asserts equal focus and byte-equivalent params. | PASS |
| VAR-03 | Applying the weekly offset preserves `focus` and the declared-zone floor. | `src/plan.py:1140-1141` creates `WorkoutParams` with the already-selected `focus`; `src/plan.py:1164-1167` validates final focus/params zone intent. `tests/test_plan.py:1445-1448` asserts focus preservation and `on_power >= zone_floor(focus)`. | PASS |

**Spec-anchored check**: 3/3 requirements matched their specified outcomes. No spec-precision gap found.

## Focused Gate

- `python3 -m unittest tests.test_plan.WorkoutVariantRotationTest -v`: **2 passed, 0 failed**.
- `python3 -m unittest tests.test_plan -v`: **120 passed, 0 failed**.
- `python3 -m unittest discover -s tests -v`: **1557 passed, 0 failed**.

## Discrimination Sensor

Both mutations ran in independently copied `src/` and `tests/` trees under `/tmp/opencode`; production files were not mutated.

| Mutation | Target | Expected killed-by test | Result |
| --- | --- | --- | --- |
| Remove ISO-week offset by replacing `src/plan.py:1138-1139` with `week_offset = 0`. | VAR-01 rotation between 2026-W43 and W44 | `WorkoutVariantRotationTest.test_goal_builds_in_consecutive_iso_weeks_rotate_same_slot_variant` | **Killed**: failed at `tests/test_plan.py:1446` because params became equal. |
| Make `goal is None` fall through to variants by changing `src/plan.py:1275` to `if False`. | VAR-02 legacy behavior without `GOAL` | `WorkoutVariantRotationTest.test_build_without_goal_keeps_legacy_variant` | **Killed**: failed at `tests/test_plan.py:1454` because params differed. |

**Sensor result**: 2/2 killed — PASS.

## Diff and Isolation Status

- `git diff --check`: PASS.
- The real-tree `git status --porcelain` was identical immediately before and after each sensor run.
- The worktree already contains unrelated modified and untracked files; this validation covers only the VAR-01 implementation slice. This report is the sole verifier-created change.

## Summary

The uncommitted VAR-01 implementation satisfies VAR-01 through VAR-03. Its focused tests pass and both required behavior-level faults are detected.

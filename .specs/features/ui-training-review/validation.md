# Revisão de treino na TUI — Validation

**Date**: 2026-10-30
**Spec**: `.specs/features/ui-training-review/spec.md`
**Diff range**: `fd41e4c` (HEAD)
**Verifier**: independent sub-agent (author ≠ verifier)

## Verdict: PASS

**Result**: PASS

All mapped requirements UIR-01..UIR-15 are covered by implementation and tests; the focused UI/projection gates pass and the full CI-equivalent suite is green.

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 | ✅ Done | `src/ui/training_review.py` + `tests/test_training_review.py`. |
| T2 | ✅ Done | Detail rendering + projections; `tests/test_ui_calendar_detail.py` updated. |
| T3 | ✅ Done | Weekly summary in calendar + projections; `tests/test_ui_calendar_week.py` updated. |
| T4 | ✅ Done | Manual/teaching copies present (`docs/CODIGO-COMENTADO/...`). |

## Spec-Anchored Acceptance Criteria (UIR-01..UIR-15)

| ID | Spec-defined outcome | Evidence (`arquivo:linha`) | Result |
| --- | --- | --- | --- |
| UIR-01 | Planned-only detail shows focus, duration, TSS and existing blocks; block list comes from plan params. | `tests/test_training_review.py:34-53` (`planned_workout_summary`); `tests/test_ui_calendar_detail.py:38-48` (`test_detalhe_planejado_mostra_estrutura_sem_streams_reais`); `src/ui/training_review.py:116-139`, `src/ui/screens/calendar_detail.py:311-322,685-758`. | PASS |
| UIR-02 | When sufficient parameters exist, target-power profile shown with zone-colored bands matching detail zones. | `tests/test_ui_calendar_detail.py:105-121` (`test_perfil_planejado_usa_cores_por_zona`) asserts `PERFIL DO TREINO` and colored markup; `src/ui/screens/calendar_detail.py:563-613,748-757` (`_profile`, `_zone_color_for_p`); zone table used by `_format_zone_time`/`_zone_time`. | PASS |
| UIR-03 | Absent optional planned field omits only its dependent line without failing; blocks omitted when absent. | `tests/test_ui_calendar_detail.py:90-103` (`test_detalhe_planejado_omite_campos_ausentes`) asserts no `Foco`/`Duração`/`TSS` when missing; `src/ui/screens/calendar_detail.py:694-718` renders fields only when present/non-zero; `tests/test_training_review.py:48-53` omits blocks when params incomplete. | PASS |
| UIR-04 | Comparison shows Planned and Realized columns with duration and TSS. | `tests/test_ui_calendar_detail.py:50-64` (`test_detalhe_compara_planejado_e_realizado_lado_a_lado`); `src/ui/screens/calendar_detail.py:323-355` (`_render_comparison`). | PASS |
| UIR-05 | Average/normalized power appear only under Realizado and are identified. | `tests/test_ui_calendar_detail.py:61-64` asserts `180 W` / `195 W` under Realizado; `src/ui/screens/calendar_detail.py:347-352`. | PASS |
| UIR-06 | Arithmetic deltas for duration/TSS shown factually (no classification). | `tests/test_training_review.py:56-67` (`day_comparison` deltas); `tests/test_ui_calendar_detail.py:61-64` asserts `-5 min`/`-7`; `src/ui/screens/calendar_detail.py:352-354`. | PASS |
| UIR-07 | Missing actual metric shows `—` while others remain visible. | `tests/test_ui_calendar_detail.py:66-77` (`test_comparacao_mantem_ausencia_como_traco`) asserts `—` count >= 3; `src/ui/screens/calendar_detail.py:346-354` per-field fallbacks. | PASS |
| UIR-08 | Weekly view totals planned/actual duration and TSS across 7 visible days. | `tests/test_training_review.py:99-115` (`week_summary`); `tests/test_ui_calendar_week.py:38-46`; `src/ui/training_review.py:172-215`, `src/ui/screens/calendar.py:506-596`. | PASS |
| UIR-09 | Weekly view counts completed/missed/pending/extra. | `tests/test_training_review.py:114`; `tests/test_ui_calendar_week.py:43-46`; `src/ui/training_review.py:196-206`, `src/ui/screens/calendar.py:587-591`. | PASS |
| UIR-10 | Planned/no-activity before today → missed. | `tests/test_training_review.py:101-114` (tuple `(1,0,2,1)` with `today=2026-11-03`); `src/ui/training_review.py:198-201`. | PASS |
| UIR-11 | Planned/no-activity today or later → pending. | `tests/test_training_review.py:101-114` (days 11-03/04/05); `src/ui/training_review.py:198-201`. | PASS |
| UIR-12 | Unplanned activity → extra and added to actual totals. | `tests/test_training_review.py:105,110-114` (entry `2026-11-05` done-only); `src/ui/training_review.py:202-206`. | PASS |
| UIR-13 | Planned zone distribution shown when plan parameters exist. | `tests/test_training_review.py:45-46,81-87`; `tests/test_ui_calendar_week.py:41-46`; `src/ui/training_review.py:93-113`, `src/ui/screens/calendar.py:531-596`. | PASS |
| UIR-14 | Actual zone distribution shown when weekly activity power streams available (passed via cache/callback). | `tests/test_training_review.py:135-143` (`week_summary` with `actual_zone_seconds`); detail computes via `zone_seconds_for_stream` and reports via `_zone_update_callback` to calendar (`src/ui/screens/calendar_detail.py:725-746`, `src/ui/screens/calendar.py:877-910`); week aggregates cached/stream zones (`src/ui/screens/calendar.py:507-526`). Implementation wired end-to-end without batch fetch. | PASS |
| UIR-15 | Without actual streams, actual distribution explicitly unavailable and not estimated. | `tests/test_training_review.py:128-133`; `tests/test_ui_calendar_week.py:44-46` asserts `indisponível`; `src/ui/training_review.py:207-215` returns `None` if no zones provided; `src/ui/screens/calendar.py:594-596`. | PASS |

**Coverage:** 15/15 mapped.

## Edge Cases
- [x] Zero/invalid duration/TSS treated as absent (not positive load): `tests/test_training_review.py:116-126`, `src/ui/training_review.py:62-76,205-206`.
- [x] Missing streams → actual zones unavailable: `tests/test_training_review.py:128-133`, `src/ui/screens/calendar.py:594-596`.
- [x] Stream read exceptions don't break detail: `src/ui/screens/calendar_detail.py:393-440` (returns empty/defaults).
- [x] Planned-only with absent optional fields omits dependent lines: `tests/test_ui_calendar_detail.py:90-103`.

## Gates

| Gate | Result |
| --- | --- |
| Whitespace/check | `git diff --check` clean (no output). |
| Focused | `python3 -m unittest tests.test_training_review tests.test_ui_calendar tests.test_ui_calendar_detail tests.test_ui_calendar_week -v` → **19 tests OK**. |
| Build/CI-equivalent | `python3 -m unittest discover -s tests -v` → **1601 tests OK, 0 failed, 0 skipped**. |

## Discrimination Sensor (isolated, no `git stash`, no changes left)

Executed in detached temp worktree `/tmp/opencode/ui-training-review-sensor` from `HEAD`. Real tree restored to original state after cleanup.

| Mutation | File:line | Focused test | Result |
| --- | --- | --- | --- |
| Reverse delta `actual-planned` → `planned-actual` | `src/ui/training_review.py:148` | `tests.test_training_review.DayComparisonTest.test_compara_duracao_tss_e_potencias_reais` | Killed (expected -300, got +300). |
| Count today as missed `day < today` → `day <= today` | `src/ui/training_review.py:198` | `tests.test_training_review.WeekSummaryTest.test_classifica_status_e_soma_totais_da_semana` | Killed (status tuple changed). |
| Force planned segments to Z2 in `zone_for_intensity`/mapping | `src/ui/training_review.py:78-113` | `tests.test_training_review.PlannedWorkoutSummaryTest.test_expoe_blocos_existentes_e_zonas_do_plano` | Killed (zone distribution / expectations fail). |

**Sensor:** 3/3 killed.

## Design/Quality Compliance
- Pure projections in `src/ui/training_review.py` shared by screens; screens render returned values.
- Weekly does not batch-fetch streams — uses cached zones reported by detail screen via callback (`src/ui/screens/calendar.py:507-526,877-910`).
- Zone classification uses `ZONE_BANDS`/focus constants; no estimation when streams unavailable.
- No production mutation by verifier; all changes are in working tree as-is (feature already implemented/tests added).

## Verdict
**PASS** — all requirements UIR-01..UIR-15 covered with evidence, focused gates green, full suite green (1601 passed), discrimination sensor killed 3/3 mutations.

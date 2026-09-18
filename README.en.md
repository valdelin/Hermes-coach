# Hermes Coach — indoor cycling training agent

[![CI](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml/badge.svg)](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml)

> **Versão em português:** [README.md](README.md)

Agent that queries the **Intervals.icu** API, computes the **TSB** (fitness
vs. fatigue), decides the focus of the day and publishes the workout to the
Intervals.icu calendar (`.zwo` files are downloaded directly in the app).

## Model cost: R$ 0

- **Authoring here:** opencode CLI, free tier (`big-pickle` on the CLI).
- **Orchestration (Hermes):** short turns; the heavy lifting is delegated to
  the opencode CLI via the `hermes/skills/cycling-coach/` skill (see below).
- **Workout execution:** `training_plan.py` is deterministic — runs without an
  LLM.

## Structure

```
hermes-coach/
├── .opencode/agent/cycling-coach.md   # opencode agent (coach)
├── hermes/skills/cycling-coach/       # Hermes delegation skill
├── src/
│   ├── intervals_client.py            # Intervals.icu API client
│   ├── coach.py                       # TSB -> focus -> load (TSS)
│   ├── plan.py                        # weekly plan (build/reconcile)
│   └── training_plan.py               # plan CLI (info/build/reconcile/push)
└── tests/                             # tests (stdlib unittest)
```

## Setup

1. Copy the credentials:
   ```
   cp .env.example .env
   # fill in INTERVALS_ATHLETE_ID, INTERVALS_API_KEY, FTP
   # optional: CUE_LANG=pt (default) or en — workout message language
   ```
   (The Intervals.icu API uses HTTP Basic Auth with user = password = API_KEY.)

2. Define your training schedule in `.env` (optional):
   ```
   TRAINING_DAYS=seg,ter,qua,qui,sex
   ```
   Accepts Portuguese (`seg,ter,...`) or English (`mon,tue,...`) day names.
   Missing or invalid -> Monday-Friday by default. It can also be configured
   by chatting with the agent on first use.

2. Install the agent in opencode (already linked in `~/.config/opencode/agent/`):
   ```
   mkdir -p ~/.config/opencode/agent
   ln -s /home/valdelin/Work/hermes-coach/.opencode/agent/cycling-coach.md \
         ~/.config/opencode/agent/cycling-coach.md
   ```

3. Install the skill in Hermes (already linked in `~/.hermes/skills/`):
   ```
   mkdir -p ~/.hermes/skills
   ln -s /home/valdelin/Work/hermes-coach/hermes/skills/cycling-coach \
         ~/.hermes/skills/cycling-coach
   ```

## Usage

Adaptive training plan (history -> Intervals calendar):
```
python3 src/training_plan.py info                        # current TSB/CTL/ATL
python3 src/training_plan.py build --days 60 --days-plan 14   # generate plan
python3 src/training_plan.py reconcile --show         # detect missed workouts
python3 src/training_plan.py push --start 2026-09-16  # publish to Intervals (upsert)
python3 src/training_plan.py all                      # full flow
```
The `external_id` is the upsert key: running again does not duplicate events
on Intervals. `push` also automatically removes `hermes-plan*` events that are
no longer in the plan (e.g. dates that changed on a rebuild). Today's workouts
are published with `push --start <today>`; the matching `.zwo` files are
downloaded in the Intervals.icu app.

Via Hermes (delegates to the opencode agent — free tier):
> "run the cycling-coach: generate today's workout"

Via opencode directly:
```
opencode run --agent cycling-coach "Generate today's workout"
```

Tests:
```
python3 -m unittest discover -s tests -v
```
(50 tests, stdlib-only — CI runs the same suite on every push/PR.)

## Daily automation (optional)

The whole flow can run automatically at midnight, without depending on
Hermes/opencode:
- The **systemd timer** `cycling-coach-daily.timer` fires
  `scripts/daily_reconcile.sh` (reconcile + push for the day).
- Logs live in `logs/daily_reconcile.log`.
- **Failure alert:** if any step fails, the script sends a desktop
  notification (`notify-send`) and exits with a non-zero code — so a silent
  failure does not go unnoticed.

## TSB decision rules

Workouts are planned only on the days set in `TRAINING_DAYS` (default:
**Monday to Friday**); the remaining days are rest days (off-schedule workouts
are only added on request to Hermes). The daily focus follows its **position**
within the schedule (the table below assumes a full 5-day week; with a shorter
schedule the first foci of the cycle are used). Load respects a **weekly
budget**: the rolling TSS sum of the last 7 days must stay within
`daily_cap * 7`; if it goes over, the day's workout is reduced (shortens
`on_sec` >= 120s, then `on_power` >= 55%) and the following days inherit the
slack. When the plan is regenerated, an already-existing workout for today in
`plan.json` is preserved.

**Off-plan extra workouts:** if the athlete rides on an unscheduled day, the
reconcile step considers the load of those workouts (events with
`paired_activity_id` and a non-hermes `external_id`) over the last 7 days. If
their sum reaches a full training day (`>= daily_cap`, computed from the real
load), the next training day becomes a recovery and the next threshold workout
is reduced by 5%. Light work does not change the plan. The same applies to
**missed workouts** (planned but not completed): the next threshold is reduced
at most once per reconcile — the `reduced_ids` guard prevents two events in
the same window from reducing the same workout twice, and recovery is never
inserted on past days.

The schedule in use is printed by `build` and `reconcile`
(`Agenda: seg,ter,qua,qui,sex`), with a warning when `TRAINING_DAYS` is not
set in `.env`.

Each event name in Intervals carries the date in front:
`YYYY-MM-DD - Treino de <Focus>` (e.g. `2026-09-21 - Treino de Zona 2`).

| TSB          | Weekly cycle (5 training days)                  |
|--------------|-----------------------------------------------|
| < -15        | Z2, Z2, Sweet Spot, Z2, Sweet Spot            |
| -15 to 0     | Z2, Sweet Spot, Z2, Sweet Spot, VO2 Max       |
| 0 to 5       | Sweet Spot, Threshold, Sweet Spot, Threshold, VO2 |
| >= +5        | Threshold, VO2 Max, Sweet Spot, Threshold, VO2 Max |

Every workout has a 10 min warm-up (45% -> 75%) and a 10 min cool-down
(70% -> 45%). The published description uses the native workout-builder
notation of Intervals (watts are shown computed by the app) and includes
**coaching messages** before every step: the warm-up explains the training zone
and the day's structure (plus progress vs. the previous same-focus workout), and
each interval gets a "Now you'll ride X minutes at Y percent of your FTP"
cue. The message language is set via `CUE_LANG` in `.env` (`pt`|`en`).

## Notes / scaffold limitations

- Fields returned by the `/events` endpoint of Intervals.icu may vary
  (`tsb`/`ctl`/`atl` come from `?summary=1` per event, or inside `summary`).
  `src/coach.py::latest_metrics` tolerates both; adjust if your plan returns
  another shape.
- The TSS estimate is approximate (`sum of sec*frac^3 / 36`), good enough to
  compare day-to-day load, not for scientific planning.
- Out of scope: local `.zwo` generation. Download the workouts in
  **Custom Workouts / export** in the Intervals app to use them in Zwift.
# -*- coding: utf-8 -*-
import os
import unittest
from datetime import date, timedelta

from src import plan
from src import plan_sanity
from src.coach import WorkoutParams


class PlanSanityTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _mk(self, day, focus, duration_sec, warmup_sec=600, cooldown_sec=600, repeats=1, on_sec=1800, off_sec=0, on_power=0.9):
        p = WorkoutParams(
            focus=focus,
            warmup_sec=warmup_sec,
            cooldown_sec=cooldown_sec,
            repeats=repeats,
            on_sec=on_sec,
            off_sec=off_sec,
            on_power=on_power,
            off_power=0.55,
        )
        return {
            "day": day,
            "focus": focus,
            "name": f"{day.isoformat()} - Teste",
            "planned_duration": duration_sec,
            "params": p,
            "tss": 40.0,
        }

    def test_san02_blocks_over_max_duration(self):
        os.environ["MAX_WORKOUT_DURATION_MINUTES"] = "60"
        w = self._mk(date.today(), plan.FOCUS_SWEETSPOT, 75 * 60)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_block())
        self.assertTrue(any(i.code == "SAN-02" for i in rep.blocks()))

    def test_san03_blocks_quality_near_race(self):
        today = date.today()
        race = today + timedelta(days=1)
        os.environ["RACE_DATE"] = race.isoformat()
        os.environ.pop("MAX_WORKOUT_DURATION_MINUTES", None)
        w = self._mk(today, plan.FOCUS_THRESHOLD, 60 * 60)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_block())
        self.assertTrue(any(i.code == "SAN-03" for i in rep.blocks()))

    def test_san03_allows_zone2_near_race(self):
        today = date.today()
        race = today + timedelta(days=1)
        os.environ["RACE_DATE"] = race.isoformat()
        os.environ.pop("MAX_WORKOUT_DURATION_MINUTES", None)
        w = self._mk(today, plan.FOCUS_ZONE2, 60 * 60, on_power=0.70)
        rep = plan_sanity.check_push([w])
        self.assertFalse(any(i.code == "SAN-03" for i in rep.issues))

    def test_san04_blocks_bad_structure(self):
        os.environ.pop("MAX_WORKOUT_DURATION_MINUTES", None)
        w = self._mk(date.today(), plan.FOCUS_VO2, 60 * 60, warmup_sec=0)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_block())
        self.assertTrue(any(i.code == "SAN-04" for i in rep.blocks()))

    def test_san05_blocks_below_zone_floor(self):
        os.environ.pop("MAX_WORKOUT_DURATION_MINUTES", None)
        w = self._mk(date.today(), plan.FOCUS_THRESHOLD, 60 * 60, on_power=0.70)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_block())
        self.assertTrue(any(i.code == "SAN-05" for i in rep.blocks()))

    def test_san06_warns_below_individual_minimum(self):
        os.environ["MIN_REGULAR_DURATION_MINUTES"] = "60"
        os.environ.pop("MAX_WORKOUT_DURATION_MINUTES", None)
        w = self._mk(date.today(), plan.FOCUS_SWEETSPOT, 40 * 60)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_warn())
        self.assertTrue(any(i.code == "SAN-06" for i in rep.warns()))
        self.assertFalse(rep.has_block())

    def test_dry_run_does_not_mutate(self):
        os.environ["MAX_WORKOUT_DURATION_MINUTES"] = "60"
        w = self._mk(date.today(), plan.FOCUS_SWEETSPOT, 75 * 60)
        rep = plan_sanity.check_push([w])
        self.assertTrue(rep.has_block())
        self.assertEqual(w["planned_duration"], 75 * 60)


if __name__ == "__main__":
    unittest.main()

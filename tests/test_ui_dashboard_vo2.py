"""Origem e seleção de VO₂ no dashboard."""

import unittest
from unittest.mock import patch

from src.intervals_adapter import _wellness_snapshot
from src.ui.utils import load_dashboard_data


class DashboardVo2Test(unittest.TestCase):
    def test_usa_registro_mais_recente_independentemente_da_ordem(self):
        rows = [_wellness_snapshot({"id": "2026-08-17", "vo2max": 47}),
                _wellness_snapshot({"id": "2026-10-30", "vo2max": 42}),
                _wellness_snapshot({"id": "2026-10-01", "vo2max": 43})]
        with patch("src.ui.utils.get_app") as app, patch("src.ui.utils.load_env"), \
             patch("src.ui.utils._build_pmc_rows", return_value=[]), \
             patch("src.ui.utils.load_plan", return_value=[]), \
             patch.dict("os.environ", {"VO2MAX": "55"}):
            app.return_value.client.return_value.wellness.return_value = rows
            app.return_value.client.return_value.events.return_value = []
            data = load_dashboard_data()
        self.assertEqual(data["vo2"], "42")
        self.assertEqual(data["vo2_date"], "2026-10-30")

    def test_sem_dados_nao_usa_env(self):
        with patch("src.ui.utils.get_app") as app, patch("src.ui.utils.load_env"), \
             patch("src.ui.utils._build_pmc_rows", return_value=[]), \
             patch("src.ui.utils.load_plan", return_value=[]), \
             patch.dict("os.environ", {"VO2MAX": "55"}):
            app.return_value.client.return_value.wellness.side_effect = OSError("offline")
            app.return_value.client.return_value.events.return_value = []
            data = load_dashboard_data()
        self.assertEqual(data["vo2"], "—")
        self.assertIsNone(data["vo2_date"])

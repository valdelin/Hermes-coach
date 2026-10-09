"""PMC-1 — Form relativo derivado (`form_pct`), view-only.

`form_pct = TSB / CTL x 100`, derivacao PURA do Hermes sobre CTL/TSB
**observados** do provider. Nao recalcula PMC, nao tem efeito prescritivo e nao
depende de provider/rede.
"""
import io
import json
import tempfile
import tokenize
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src import ui_state
from src.application import Application
from src.snapshot import SyncFreshness, TrainingSnapshot
from src.ui_state import PmcView, build_pmc_view, derive_form_pct

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 3)


def _boom():
    raise AssertionError("derivacao nao pode pedir provider")


def _code_only(path):
    src = Path(path).read_text(encoding="utf-8")
    return " ".join(
        tok.string for tok in tokenize.generate_tokens(io.StringIO(src).readline)
        if tok.type not in (tokenize.COMMENT, tokenize.STRING))


class FormulaTest(unittest.TestCase):
    def test_casos_principais(self):
        casos = [
            ((100, -25), -25.0),
            ((100, -30), -30.0),
            ((100, -32), -32.0),
            ((250, -25), -10.0),
            ((100, 0), 0.0),
            ((100, 10), 10.0),
        ]
        for (ctl, tsb), esperado in casos:
            with self.subTest(ctl=ctl, tsb=tsb):
                self.assertEqual(derive_form_pct(ctl, tsb), esperado)

    def test_tsb_positivo_e_form_positivo(self):
        self.assertGreater(derive_form_pct(100.0, 15.0), 0.0)

    def test_floats_e_ints(self):
        self.assertAlmostEqual(derive_form_pct(87.5, -12.25), -14.0, places=9)
        self.assertAlmostEqual(derive_form_pct(87.5, -12.25),
                               derive_form_pct(87.5, -12.25), places=12)


class UndefinedTest(unittest.TestCase):
    """Razao indefinida -> None. Nunca 0 (0 e um valor legitimo)."""

    def test_ctl_zero(self):
        self.assertIsNone(derive_form_pct(0.0, -25.0))

    def test_ctl_none(self):
        self.assertIsNone(derive_form_pct(None, -25.0))

    def test_tsb_none(self):
        self.assertIsNone(derive_form_pct(100.0, None))

    def test_ambos_none(self):
        self.assertIsNone(derive_form_pct(None, None))

    def test_ctl_negativo(self):
        self.assertIsNone(derive_form_pct(-10.0, -25.0))

    def test_ctl_muito_pequeno_nao_e_clampado(self):
        self.assertIsNotNone(derive_form_pct(1e-9, -25.0))
        self.assertLess(derive_form_pct(1e-9, -25.0), -1e9)

    def test_tsb_zero_nao_vira_none(self):
        self.assertEqual(derive_form_pct(0.0001, 0.0), 0.0)

    def test_valor_nao_numerico(self):
        self.assertIsNone(derive_form_pct("n/a", -25.0))
        self.assertIsNone(derive_form_pct(100.0, "n/a"))


class PrecisionTest(unittest.TestCase):
    def test_sem_arredondamento_interno(self):
        self.assertEqual(derive_form_pct(3.0, -1.0), (-1.0 / 3.0) * 100.0)
        self.assertEqual(derive_form_pct(100.0, -25.5), -25.5)
        self.assertEqual(derive_form_pct(87.5, -12.25),
                         (-12.25 / 87.5) * 100.0)

    def test_formatacao_e_do_consumidor(self):
        valor = derive_form_pct(101.0, -25.5)
        self.assertIsInstance(valor, float)
        self.assertEqual(f"{valor:.1f}%", "-25.2%")


class DerivationIsPureTest(unittest.TestCase):
    def test_nao_muta_argumentos(self):
        ctl, tsb = 100.0, -25.0
        self.assertEqual(derive_form_pct(ctl, tsb), -25.0)
        self.assertEqual((ctl, tsb), (100.0, -25.0))

    def test_ctl_atl_tsb_preservados_observados(self):
        metrics = {"ctl": 100.0, "atl": 125.0, "tsb": -25.0, "tss": 320.0,
                   "ftp": 200.0, "day": "2026-10-03"}
        copia = dict(metrics)
        pmc = build_pmc_view(metrics)
        self.assertEqual((pmc.ctl, pmc.atl, pmc.tsb), (100.0, 125.0, -25.0))
        self.assertEqual(pmc.form_pct, -25.0)
        self.assertEqual(pmc.tss, 320.0)
        self.assertEqual(pmc.ftp, 200.0)
        self.assertEqual(pmc.day, "2026-10-03")
        self.assertEqual(metrics, copia)

    def test_form_pct_none_mantem_observados(self):
        pmc = build_pmc_view({"ctl": 0.0, "atl": 50.0, "tsb": -10.0})
        self.assertIsNone(pmc.form_pct)
        self.assertEqual(pmc.ctl, 0.0)
        self.assertEqual(pmc.atl, 50.0)
        self.assertEqual(pmc.tsb, -10.0)

    def test_sem_pmc_nao_cria_objeto_artificial(self):
        self.assertIsNone(build_pmc_view(None))
        self.assertIsNone(build_pmc_view({}))
        self.assertIsNone(build_pmc_view({"day": "2026-10-03"}))


class ApplicationStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.snap_file = self.root / "training_snapshot.json"
        self.app = Application(plan_path=self.plan_file,
                               env_path=self.root / ".env",
                               client_factory=_boom,
                               snapshot_path=self.snap_file)

    def tearDown(self):
        self.tmp.cleanup()

    def _sync(self, metrics, now=T0):
        snap = TrainingSnapshot(
            events=[{"training_load": 55.0}], wellness=[],
            activities=[], metrics=metrics,
            captured_at=now.isoformat(), provider="intervals",
            freshness=SyncFreshness.captured(now=now, provider="intervals"))
        self.app.save_training_snapshot(snap)
        return snap

    def test_form_pct_lido_do_estado_local(self):
        self._sync({"ctl": 100.0, "atl": 125.0, "tsb": -25.0})
        state = self.app.get_application_state(today=TODAY, now=T0)
        pmc = state.snapshot.pmc
        self.assertEqual((pmc.ctl, pmc.atl, pmc.tsb, pmc.form_pct),
                         (100.0, 125.0, -25.0, -25.0))

    def test_provider_independence(self):
        self._sync({"ctl": 250.0, "atl": 275.0, "tsb": -25.0})
        antes = self.snap_file.read_text(encoding="utf-8")
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertEqual(state.snapshot.pmc.form_pct, -10.0)
        self.assertEqual(self.snap_file.read_text(encoding="utf-8"), antes)

    def test_snapshot_stale_ainda_calcula_form_pct(self):
        self._sync({"ctl": 100.0, "atl": 125.0, "tsb": -25.0})
        depois = T0 + timedelta(days=5)
        state = self.app.get_application_state(today=TODAY, now=depois)
        self.assertEqual(state.snapshot.freshness.status, "stale")
        self.assertEqual(state.snapshot.pmc.form_pct, -25.0)

    def test_snapshot_fresh_form_pct_tambem(self):
        self._sync({"ctl": 100.0, "atl": 100.0, "tsb": 0.0})
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertEqual(state.snapshot.freshness.status, "fresh")
        self.assertEqual(state.snapshot.pmc.form_pct, 0.0)

    def test_sem_snapshot_nao_exponte_form_pct(self):
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertIsNone(state.snapshot)
        self.assertNotIn("form_pct", json.dumps(state.to_dict()))

    def test_snapshot_sem_pmc(self):
        snap = TrainingSnapshot(
            events=[{"training_load": 10.0}], wellness=[], activities=[],
            metrics=None, captured_at=T0.isoformat(), provider="intervals",
            freshness=SyncFreshness.captured(now=T0, provider="intervals"))
        self.app.save_training_snapshot(snap)
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertIsInstance(state.snapshot, ui_state.SnapshotView)
        self.assertIsNone(state.snapshot.pmc)
        self.assertIsNone(state.snapshot.to_dict()["pmc"])


class SerializationTest(unittest.TestCase):
    def test_to_dict_inclui_form_pct(self):
        pmc = PmcView(ctl=100.0, atl=125.0, tsb=-25.0, form_pct=-25.0)
        payload = pmc.to_dict()
        self.assertEqual(payload["ctl"], 100.0)
        self.assertEqual(payload["atl"], 125.0)
        self.assertEqual(payload["tsb"], -25.0)
        self.assertEqual(payload["form_pct"], -25.0)
        json.dumps(payload)

    def test_form_pct_none_serializa_como_null(self):
        payload = PmcView(ctl=0.0, atl=10.0, tsb=-5.0).to_dict()
        self.assertIsNone(payload["form_pct"])
        self.assertEqual(json.loads(json.dumps(payload))["form_pct"], None)

    def test_deterministico(self):
        metrics = {"ctl": 100.0, "atl": 125.0, "tsb": -25.0}
        self.assertEqual(build_pmc_view(metrics).to_dict(),
                         build_pmc_view(metrics).to_dict())


class GuardrailTest(unittest.TestCase):
    """`form_pct` e representacao derivada, nao policy."""

    def test_sem_policy_ou_threshold_no_codigo(self):
        codigo = _code_only(ui_state.__file__)
        for token in ("NORMAL", "CAUTION", "HIGH_NEGATIVE_FORM", "deload"):
            self.assertNotIn(token, codigo)

    def test_form_pct_nao_esta_no_adapter_nem_no_provider(self):
        import src.intervals_adapter as adapter
        import src.provider as provider
        for modulo in (adapter, provider):
            self.assertNotIn("form_pct",
                             _code_only(Path(modulo.__file__)))

    def test_derivation_e_pura_sem_io(self):
        codigo = _code_only(ui_state.__file__)
        self.assertNotIn("open", codigo)
        self.assertNotIn("requests", codigo)

    def test_rota_legacy_continua_valida(self):
        """`derive_form_pct` nao substitui TSB: TSB segue exposto em % reais."""
        pmc = build_pmc_view({"ctl": 100.0, "tsb": -25.0})
        self.assertEqual(pmc.tsb, -25.0)
        self.assertEqual(pmc.form_pct, -25.0)


if __name__ == "__main__":
    unittest.main()

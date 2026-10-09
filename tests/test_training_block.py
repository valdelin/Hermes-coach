import json
import tempfile
import unittest
from pathlib import Path

from src.application import Application
from src.plan import load_plan_meta, save_plan
from src.training_block import BlockContext


class BlockContextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "plan.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_legado_nao_inventa_bloco(self):
        self.path.write_text('[{"day": "2026-10-08"}]', encoding="utf-8")
        self.assertIsNone(load_plan_meta(self.path)["block_context"])

    def test_contexto_tem_schema_explicito_e_preserva_workouts(self):
        block = BlockContext("block-2026-10", "2026-10-08", "ftp-builder")
        save_plan([{"day": "2026-10-08", "name": "Z2"}], self.path,
                  goal="ftp-builder", block_context=block)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["block_context"], {
            "schema_version": 1, "id": "block-2026-10",
            "started_on": "2026-10-08", "goal": "ftp-builder"})
        self.assertEqual(raw["workouts"], [{"day": "2026-10-08", "name": "Z2"}])
        self.assertEqual(load_plan_meta(self.path)["block_context"], block)

    def test_contexto_invalido_falha_fechado_no_load(self):
        self.path.write_text(json.dumps({"workouts": [], "block_context": {
            "schema_version": 1, "id": "", "started_on": "ontem"}}),
            encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "block context"):
            load_plan_meta(self.path)

    def test_inicio_explicito_na_application_nao_muda_prescricao(self):
        app = Application(plan_path=self.path)
        app.save_plan([{"day": "2026-10-08", "name": "Z2"}], goal="ftp-builder")
        block = BlockContext("block-1", "2026-10-08", "ftp-builder")
        app.start_training_block(block)
        self.assertEqual(app.load_plan()[0]["name"], "Z2")
        self.assertEqual(app.load_plan_meta()["block_context"], block)

    def test_writer_legado_preserva_contexto_quando_nao_o_recebe(self):
        block = BlockContext("block-1", "2026-10-08")
        save_plan([{"day": "2026-10-08"}], self.path, block_context=block)
        save_plan([{"day": "2026-10-09"}], self.path)
        self.assertEqual(load_plan_meta(self.path)["block_context"], block)

    def test_substituicao_exige_opt_in(self):
        app = Application(plan_path=self.path)
        app.start_training_block(BlockContext("block-1", "2026-10-08"))
        with self.assertRaisesRegex(ValueError, "replace explicitamente"):
            app.start_training_block(BlockContext("block-2", "2026-10-15"))
        app.start_training_block(BlockContext("block-2", "2026-10-15"), replace=True)
        self.assertEqual(app.load_plan_meta()["block_context"].id, "block-2")

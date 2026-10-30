"""Contrato de execução protegida das operações da TUI."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.ui.operations import (
    FacadeRunner, OperationFlow, OperationName, OperationPhase, OperationResult,
    operation_spec,
)


class OperationCatalogTest(unittest.TestCase):
    def test_previews_sao_consultivas_e_nao_recebem_yes(self):
        expected = {
            OperationName.BUILD: ("build", "--dry-run"),
            OperationName.CHECK: ("check", "--dry-run"),
            OperationName.RECONCILE: ("reconcile", "--show"),
            OperationName.PUSH: ("publicar", "--dry-run"),
        }
        for operation, argv in expected.items():
            with self.subTest(operation=operation):
                self.assertEqual(operation_spec(operation).preview_argv, argv)
                self.assertNotIn("--yes", argv)

    def test_aplicacoes_sao_fechadas_e_somente_push_exige_texto(self):
        self.assertEqual(operation_spec(OperationName.BUILD).apply_argv,
                         ("build", "--yes"))
        self.assertEqual(operation_spec(OperationName.CHECK).apply_argv,
                         ("check", "--apply", "--yes"))
        self.assertEqual(operation_spec(OperationName.RECONCILE).apply_argv,
                         ("reconcile", "--yes"))
        self.assertEqual(operation_spec(OperationName.PUSH).apply_argv,
                         ("publicar", "--yes"))
        self.assertEqual(operation_spec(OperationName.PUSH).typed_confirmation,
                         "PUBLICAR")
        self.assertIsNone(operation_spec(OperationName.BUILD).typed_confirmation)


class FacadeRunnerTest(unittest.TestCase):
    def test_executa_lista_na_raiz_e_captura_todas_as_saidas(self):
        process = Mock(stdout="resultado", stderr="aviso", returncode=0)
        execute = Mock(return_value=process)
        root = Path("/tmp/hermes")
        runner = FacadeRunner(root=root, execute=execute)

        result = runner.run(("build", "--dry-run"))

        self.assertEqual(result.argv, ("build", "--dry-run"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "resultado")
        self.assertEqual(result.stderr, "aviso")
        argv = execute.call_args.args[0]
        self.assertEqual(argv[1:], ["scripts/hermes_agent.py", "build", "--dry-run"])
        self.assertEqual(execute.call_args.kwargs["cwd"], str(root))
        self.assertFalse(execute.call_args.kwargs["shell"])
        self.assertTrue(execute.call_args.kwargs["text"])
        self.assertTrue(execute.call_args.kwargs["capture_output"])

    def test_erro_para_iniciar_facade_vira_resultado_de_falha(self):
        runner = FacadeRunner(
            root=Path("/tmp/hermes"),
            execute=Mock(side_effect=OSError("arquivo ausente")),
        )

        result = runner.run(("check", "--dry-run"))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("arquivo ausente", result.stderr)


class OperationFlowTest(unittest.TestCase):
    def _runner(self, *results):
        runner = Mock()
        runner.run.side_effect = results
        return runner

    def test_previa_com_sucesso_habilita_apply_normal_so_apos_confirmar(self):
        runner = self._runner(
            OperationResult(("build", "--dry-run"), 0, "prévia", ""),
            OperationResult(("build", "--yes"), 0, "aplicado", ""),
        )
        flow = OperationFlow(OperationName.BUILD, runner)

        self.assertTrue(flow.preview().succeeded)
        self.assertIsNone(flow.apply())
        self.assertTrue(flow.continue_after_preview())
        self.assertEqual(flow.apply().argv, ("build", "--yes"))
        self.assertEqual(flow.phase, OperationPhase.SUCCEEDED)

    def test_falha_na_previa_nao_permite_apply(self):
        runner = self._runner(OperationResult(("check", "--dry-run"), 2, "", "falhou"))
        flow = OperationFlow(OperationName.CHECK, runner)

        self.assertFalse(flow.preview().succeeded)
        self.assertEqual(flow.phase, OperationPhase.FAILED)
        self.assertFalse(flow.continue_after_preview())
        self.assertIsNone(flow.apply())
        self.assertEqual(runner.run.call_count, 1)

    def test_push_exige_texto_exato_antes_de_apply(self):
        runner = self._runner(
            OperationResult(("publicar", "--dry-run"), 0, "prévia", ""),
            OperationResult(("publicar", "--yes"), 0, "publicado", ""),
        )
        flow = OperationFlow(OperationName.PUSH, runner)

        flow.preview()
        self.assertTrue(flow.continue_after_preview())
        self.assertEqual(flow.phase, OperationPhase.TYPED_CONFIRM)
        self.assertFalse(flow.confirm_typed("publicar"))
        self.assertIsNone(flow.apply())
        self.assertTrue(flow.confirm_typed("PUBLICAR"))
        self.assertEqual(flow.apply().argv, ("publicar", "--yes"))

    def test_cancelamento_nunca_chama_apply(self):
        runner = self._runner(OperationResult(("reconcile", "--show"), 0, "prévia", ""))
        flow = OperationFlow(OperationName.RECONCILE, runner)

        flow.preview()
        flow.cancel()
        self.assertEqual(flow.phase, OperationPhase.CANCELLED)
        self.assertIsNone(flow.apply())
        self.assertEqual(runner.run.call_count, 1)


if __name__ == "__main__":
    unittest.main()

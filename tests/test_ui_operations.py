"""Contrato de execução protegida das operações da TUI."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.ui.operations import FacadeRunner, OperationName, operation_spec


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


if __name__ == "__main__":
    unittest.main()

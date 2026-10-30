"""Contrato de execução protegida das operações da TUI."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

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
            OperationName.PUSH: ("push", "--dry-run"),
        }
        for operation, argv in expected.items():
            with self.subTest(operation=operation):
                self.assertEqual(operation_spec(operation).preview_argv, argv)
                self.assertNotIn("--yes", argv)

    def test_aplicacoes_sao_fechadas_e_somente_push_exige_texto(self):
        self.assertEqual(operation_spec(OperationName.BUILD).apply_argv,
                         ("--yes", "build"))
        self.assertEqual(operation_spec(OperationName.CHECK).apply_argv,
                         ("--yes", "check", "--apply"))
        self.assertEqual(operation_spec(OperationName.RECONCILE).apply_argv,
                         ("--yes", "reconcile"))
        self.assertEqual(operation_spec(OperationName.PUSH).apply_argv,
                         ("--yes", "push"))
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
            OperationResult(("--yes", "build"), 0, "aplicado", ""),
        )
        flow = OperationFlow(OperationName.BUILD, runner)

        self.assertTrue(flow.preview().succeeded)
        self.assertIsNone(flow.apply())
        self.assertTrue(flow.continue_after_preview())
        self.assertEqual(flow.apply().argv, ("--yes", "build"))
        self.assertEqual(flow.phase, OperationPhase.SUCCEEDED)

    def test_falha_na_previa_nao_permite_apply(self):
        runner = self._runner(OperationResult(("check", "--dry-run"), 2, "", "falhou"))
        flow = OperationFlow(OperationName.CHECK, runner)

        self.assertFalse(flow.preview().succeeded)
        self.assertEqual(flow.phase, OperationPhase.FAILED)
        self.assertFalse(flow.continue_after_preview())
        self.assertIsNone(flow.apply())
        self.assertEqual(runner.run.call_count, 1)


class DashboardOperationTest(unittest.TestCase):
    def _runner(self, *results):
        runner = Mock()
        runner.run.side_effect = results
        return runner

    def test_dashboard_abre_modal_para_operacoes_declaradas(self):
        from textual.screen import Screen
        from src.ui.screens.dashboard import DashboardScreen

        app = Mock()
        screen = DashboardScreen()
        with patch.object(Screen, "app", new_callable=PropertyMock, return_value=app):
            screen.action_generate()
            screen.action_reconcile()
            screen.action_publish()

        operations = [call.args[0]._flow.operation for call in app.push_screen.call_args_list]
        self.assertEqual(operations, [OperationName.BUILD, OperationName.RECONCILE, OperationName.PUSH])

    def test_prontidao_abre_modal_de_check(self):
        from textual.screen import Screen
        from src.ui.screens.readiness import ReadinessScreen

        app = Mock()
        screen = ReadinessScreen()
        with patch.object(Screen, "app", new_callable=PropertyMock, return_value=app):
            screen.action_check()

        self.assertEqual(app.push_screen.call_args.args[0]._flow.operation, OperationName.CHECK)

    def test_push_exige_texto_exato_antes_de_apply(self):
        runner = self._runner(
            OperationResult(("push", "--dry-run"), 0, "prévia", ""),
            OperationResult(("--yes", "push"), 0, "publicado", ""),
        )
        flow = OperationFlow(OperationName.PUSH, runner)

        flow.preview()
        self.assertTrue(flow.continue_after_preview())
        self.assertEqual(flow.phase, OperationPhase.TYPED_CONFIRM)
        self.assertFalse(flow.confirm_typed("publicar"))
        self.assertIsNone(flow.apply())
        self.assertTrue(flow.confirm_typed("PUBLICAR"))
        self.assertEqual(flow.apply().argv, ("--yes", "push"))

    def test_catalogo_e_aceito_pelo_parser_da_facade(self):
        from scripts.hermes_agent import build_parser

        parser = build_parser()
        for operation in OperationName:
            spec = operation_spec(operation)
            for argv in (spec.preview_argv, spec.apply_argv):
                with self.subTest(operation=operation, argv=argv):
                    self.assertIsNotNone(parser.parse_args(list(argv)))

    def test_sucesso_do_modal_chama_refresh_uma_vez(self):
        from src.ui.screens.operation import OperationModal

        refresh = Mock()
        modal = OperationModal(OperationName.BUILD, refresh)
        modal._complete_success()
        self.assertEqual(refresh.call_count, 1)

    def test_saida_do_modal_inclui_comando_e_exit_code(self):
        from src.ui.screens.operation import OperationModal

        modal = OperationModal(OperationName.BUILD)
        result = OperationResult(("build", "--dry-run"), 0, "ok", "")
        text = modal._format_output(result)
        self.assertIn("$ hermes_agent.py build --dry-run", text)
        self.assertIn("exit code: 0", text)

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

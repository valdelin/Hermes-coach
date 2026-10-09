"""Testes do orquestrador local (scripts/hermes_agent.py).

Nenhum teste executa o CLI real: ``subprocess.run`` é mockado. Não há network,
nem push, nem escrita em ``plan.json`` (PROMPT 66 §37).
"""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "hermes_agent.py"
SPEC = importlib.util.spec_from_file_location("hermes_agent", SCRIPT)
agent = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = agent
SPEC.loader.exec_module(agent)

EXE = sys.executable
TRAINING = "src/training_plan.py"


def run_cmd(*parts):
    return [EXE, TRAINING, *parts]


def ok_result():
    return subprocess.CompletedProcess(args=[], returncode=0)


def patch_run(returncode=0):
    return mock.patch.object(
        agent.subprocess, "run",
        return_value=subprocess.CompletedProcess(args=[], returncode=returncode))


def patch_input(return_value="s", side_effect=None):
    return mock.patch("builtins.input", return_value=return_value,
                      side_effect=side_effect)


class BuildCommandsTest(unittest.TestCase):
    """§36.1 — montagem e despacho dos comandos."""

    def test_training(self):
        self.assertEqual(agent.training("info", "--days", "60"),
                         run_cmd("info", "--days", "60"))

    def test_build_dry_run_sem_confirmacao(self):
        args = agent._ns(days=60, days_plan=14, ftp_test=None,
                         no_power=False, dry_run=True)
        with patch_run() as run:
            code = agent.cmd_build(args)
        self.assertEqual(code, 0)
        run.assert_called_once_with(
            run_cmd("build", "--days", "60", "--days-plan", "14", "--dry-run"),
            cwd=str(agent.ROOT), check=False)

    def test_build_sem_dry_run_confirma(self):
        args = agent._ns(days=60, days_plan=14, ftp_test="2026-11-01",
                         no_power=True, dry_run=False)
        with patch_run() as run, patch_input("s"):
            code = agent.cmd_build(args)
        self.assertEqual(code, 0)
        run.assert_called_once_with(
            run_cmd("build", "--days", "60", "--days-plan", "14",
                    "--ftp-test", "2026-11-01", "--no-power"),
            cwd=str(agent.ROOT), check=False)

    def test_info_model_adherence_ftp_check(self):
        cases = [
            (agent.cmd_info, agent._ns(days=60), run_cmd("info", "--days", "60")),
            (agent.cmd_model, agent._ns(days=60), run_cmd("model", "--days", "60")),
            (agent.cmd_adherence, agent._ns(days=45),
             run_cmd("adherence", "--days", "45")),
            (agent.cmd_ftp_check, agent._ns(days=120, weeks=8),
             run_cmd("ftp-check", "--days", "120", "--weeks", "8")),
        ]
        for func, args, expected in cases:
            with self.subTest(func=func.__name__):
                with patch_run() as run:
                    self.assertEqual(func(args), 0)
                run.assert_called_once_with(expected, cwd=str(agent.ROOT),
                                            check=False)

    def test_recovery_so_flags_reais(self):
        args = agent._ns(weeks=12, ramp_pts=9)
        with patch_run() as run:
            self.assertEqual(agent.cmd_recovery(args), 0)
        run.assert_called_once_with(
            run_cmd("recovery", "--weeks", "12", "--ramp-pts", "9"),
            cwd=str(agent.ROOT), check=False)

    def test_summary_periodo_custom(self):
        args = agent._ns(period="custom", date=None, start="2026-08-18",
                         end="2026-09-24", chart="none", export=None, theme=None)
        with patch_run() as run:
            self.assertEqual(agent.cmd_sync_summary(args), 0)
        run.assert_called_once_with(
            run_cmd("summary", "--period", "custom", "--start", "2026-08-18",
                    "--end", "2026-09-24", "--chart", "none"),
            cwd=str(agent.ROOT), check=False)


class RawTest(unittest.TestCase):
    """`raw` reaplica o gate de efeito antes do passthrough ao CLI."""

    def test_raw_encaminha_argumentos(self):
        args = agent._ns(rest=["ftp-check", "--days", "90", "--weeks", "6"])
        with patch_run() as run:
            self.assertEqual(agent.cmd_raw(args), 0)
        run.assert_called_once_with(
            run_cmd("ftp-check", "--days", "90", "--weeks", "6"),
            cwd=str(agent.ROOT), check=False)

    def test_raw_faz_prefixo_sys_executable(self):
        self.assertTrue(agent.training("x")[0] == sys.executable)

    def test_raw_mutaveis_exigem_confirmacao(self):
        for rest in (
                ["push"], ["all"], ["build"], ["reconcile"]):
            with self.subTest(rest=rest):
                with patch_run() as run, patch_input("n"):
                    self.assertEqual(agent.cmd_raw(agent._ns(rest=rest)), 0)
                run.assert_not_called()

    def test_raw_reconcile_show_e_consultivo(self):
        args = agent._ns(rest=["reconcile", "--show"])
        with patch_run() as run, patch_input("n") as inp:
            self.assertEqual(agent.cmd_raw(args), 0)
        inp.assert_not_called()
        run.assert_called_once_with(
            run_cmd("reconcile", "--show"), cwd=str(agent.ROOT), check=False)

    def test_raw_desconhecido_e_conservador(self):
        args = agent._ns(rest=["futuro-comando", "--apply"])
        with patch_run() as run, patch_input("n"):
            self.assertEqual(agent.cmd_raw(args), 0)
        run.assert_not_called()

    def test_raw_vazio_nao_despacha(self):
        with patch_run() as run:
            self.assertEqual(agent.cmd_raw(agent._ns(rest=[])), 2)
        run.assert_not_called()


class ConfirmationTest(unittest.TestCase):
    """§36.3 e §36.4 — confirmação negativa e --yes."""

    def test_confirmacao_negativa_nao_executa_push(self):
        args = agent._ns(start=None, dry_run=False)
        with patch_run() as run, patch_input("n"):
            code = agent.cmd_push(args)
        self.assertEqual(code, 0)
        run.assert_not_called()

    def test_confirmacao_sim_executa_push(self):
        args = agent._ns(start="2026-09-16", dry_run=False)
        with patch_run() as run, patch_input("sim"):
            self.assertEqual(agent.cmd_push(args), 0)
        run.assert_called_once_with(
            run_cmd("push", "--start", "2026-09-16"),
            cwd=str(agent.ROOT), check=False)

    def test_yes_nao_pergunta(self):
        args = agent._ns(start=None, dry_run=False, yes=True)
        with patch_run() as run, patch_input("n") as inp:
            self.assertEqual(agent.cmd_push(args), 0)
        inp.assert_not_called()
        run.assert_called_once()
        call = run.call_args[0][0]
        self.assertEqual(call, run_cmd("push"))

    def test_eof_e_resposta_invalida_cancelam_sem_efeito(self):
        args = agent._ns(start=None, dry_run=False)
        for answer, side_effect in (("", EOFError), ("", OSError),
                                    ("", RuntimeError), ("talvez", None)):
            with self.subTest(answer=answer), patch_run() as run, \
                    patch_input(answer, side_effect=side_effect):
                self.assertEqual(agent.cmd_push(args), 0)
            run.assert_not_called()

    def test_daily_negativo_nao_executa(self):
        with patch_run() as run, patch_input("n"):
            code = agent.cmd_daily(agent._ns())
        self.assertEqual(code, 0)
        run.assert_not_called()

    def test_daily_positivo_chama_bash(self):
        with patch_run() as run, patch_input("s"):
            self.assertEqual(agent.cmd_daily(agent._ns()), 0)
        run.assert_called_once_with(
            ["bash", agent.DAILY_SCRIPT], cwd=str(agent.ROOT), check=False)

    def test_ftp_scan_exige_confirmacao_para_registrar_evidencia(self):
        args = agent._ns(days=45)
        with patch_run() as run, patch_input("n"):
            self.assertEqual(agent.cmd_ftp_scan(args), 0)
        run.assert_not_called()

        with patch_run() as run, patch_input("s"):
            self.assertEqual(agent.cmd_ftp_scan(args), 0)
        run.assert_called_once_with(
            run_cmd("ftp-scan", "--days", "45"), cwd=str(agent.ROOT),
            check=False)

    def test_yes_no_ftp_scan_nao_e_encaminhado_ao_cli(self):
        args = agent._ns(days=45, yes=True)
        with patch_run() as run, patch_input("n") as inp:
            self.assertEqual(agent.cmd_ftp_scan(args), 0)
        inp.assert_not_called()
        run.assert_called_once_with(
            run_cmd("ftp-scan", "--days", "45"), cwd=str(agent.ROOT),
            check=False)


class TodayTest(unittest.TestCase):
    """§36.6 e §36.7 — today read-only e today --apply."""

    def test_today_read_only(self):
        with patch_run() as run:
            self.assertEqual(agent.cmd_today(agent._ns(apply=False)), 0)
        self.assertEqual(
            run.call_args_list,
            [mock.call(run_cmd("check", "--dry-run"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("reconcile", "--show"), cwd=str(agent.ROOT),
                       check=False)])

    def test_today_apply_confirma(self):
        with patch_run() as run, patch_input("n"):
            self.assertEqual(agent.cmd_today(agent._ns(apply=True)), 0)
        run.assert_not_called()

    def test_today_apply_grava(self):
        with patch_run() as run, patch_input("s"):
            self.assertEqual(agent.cmd_today(agent._ns(apply=True)), 0)
        self.assertEqual(
            run.call_args_list,
            [mock.call(run_cmd("check", "--apply"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("reconcile", "--show"), cwd=str(agent.ROOT),
                       check=False)])

    def test_check_apply_exige_confirmacao(self):
        with patch_run() as run, patch_input("n"):
            code = agent.cmd_check(
                agent._ns(days=14, apply=True, dry_run=False))
        self.assertEqual(code, 0)
        run.assert_not_called()


class PushTest(unittest.TestCase):
    """§36.8 e §36.9 — push dry-run vs push mutável."""

    def test_push_dry_run_sem_confirmacao(self):
        args = agent._ns(start="2026-09-16", dry_run=True)
        with patch_run() as run, patch_input("n") as inp:
            self.assertEqual(agent.cmd_push(args), 0)
        inp.assert_not_called()
        run.assert_called_once_with(
            run_cmd("push", "--start", "2026-09-16", "--dry-run"),
            cwd=str(agent.ROOT), check=False)

    def test_push_mutavel_com_confirmacao(self):
        with patch_run() as run, patch_input("s"):
            self.assertEqual(agent.cmd_push(agent._ns(start=None, dry_run=False)), 0)
        run.assert_called_once_with(run_cmd("push"),
                                    cwd=str(agent.ROOT), check=False)


class EffectClassificationTest(unittest.TestCase):
    def test_ftp_scan_tem_efeito_externo_potencial(self):
        self.assertIs(agent.training_effect("ftp-scan"),
                      agent.CommandEffect.EXTERNAL_WRITE)

    def test_ftp_confirm_e_reference_change(self):
        self.assertIs(agent.training_effect("ftp-confirm", ("scan-a",)),
                      agent.CommandEffect.REFERENCE_CHANGE)

    def test_summary_export_e_escrita_local(self):
        self.assertIs(
            agent.training_effect("summary", ("--export", "resumo.html")),
            agent.CommandEffect.LOCAL_WRITE)
        args = agent._ns(period="day", date=None, start=None, end=None,
                         chart=None, export="resumo.html", theme=None)
        with patch_run() as run, patch_input("n"):
            self.assertEqual(agent.cmd_sync_summary(args), 0)
        run.assert_not_called()

    def test_reconcile_show_e_today_sem_apply_sao_consultivos(self):
        self.assertIs(agent.training_effect("reconcile", ("--show",)),
                      agent.CommandEffect.READ_ONLY)
        self.assertIs(agent.training_effect("check", ("--dry-run",)),
                      agent.CommandEffect.READ_ONLY)

    def test_comando_desconhecido_e_escrita_local_conservadora(self):
        self.assertIs(agent.training_effect("futuro-comando"),
                      agent.CommandEffect.LOCAL_WRITE)


class VaultTest(unittest.TestCase):
    """§36.11 — vault-check e vault-sync."""

    def test_vault_check_read_only(self):
        with patch_run() as run:
            self.assertEqual(agent.cmd_vault_check(agent._ns()), 0)
        run.assert_called_once_with(
            [sys.executable, agent.SYNC_VAULT_SCRIPT, "--check"],
            cwd=str(agent.ROOT), check=False)

    def test_vault_sync_negativo_nao_executa(self):
        with patch_run() as run, patch_input("n"):
            self.assertEqual(
                agent.cmd_vault_sync(agent._ns(doc=["docs/ROADMAP.md"])), 0)
        run.assert_not_called()

    def test_vault_sync_positivo(self):
        with patch_run() as run, patch_input("s"):
            self.assertEqual(
                agent.cmd_vault_sync(agent._ns(doc=["docs/ROADMAP.md"])), 0)
        run.assert_called_once_with(
            [sys.executable, agent.SYNC_VAULT_SCRIPT, "--sync",
             "docs/ROADMAP.md"],
            cwd=str(agent.ROOT), check=False)


class TestsCommandTest(unittest.TestCase):
    """§36.12 — comando tests, com e sem target."""

    def test_default_descobre_suite(self):
        with patch_run() as run:
            self.assertEqual(agent.cmd_tests(agent._ns(target=None)), 0)
        run.assert_called_once_with(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=str(agent.ROOT), check=False)

    def test_target_focado(self):
        with patch_run() as run:
            self.assertEqual(
                agent.cmd_tests(agent._ns(target="tests.test_vault_sync")), 0)
        run.assert_called_once_with(
            [sys.executable, "-m", "unittest", "tests.test_vault_sync", "-v"],
            cwd=str(agent.ROOT), check=False)


class StatusTest(unittest.TestCase):
    """§36.5 — status encadeia os quatro comandos read-only."""

    def test_status_encadeia_quatro_comandos(self):
        with patch_run() as run:
            self.assertEqual(agent.cmd_status(agent._ns()), 0)
        self.assertEqual(
            run.call_args_list,
            [mock.call(run_cmd("info", "--days", "60"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("model", "--days", "60"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("adherence", "--days", "45"),
                       cwd=str(agent.ROOT), check=False),
             mock.call(run_cmd("ftp-check", "--days", "120", "--weeks", "8"),
                       cwd=str(agent.ROOT), check=False)])


class CwdTest(unittest.TestCase):
    """§36.15 — todos os subprocessos rodam na raiz do repo."""

    def test_cwd_e_sempre_o_root(self):
        for _ in range(3):
            with patch_run() as run:
                agent.cmd_info(agent._ns(days=60))
                agent.cmd_today(agent._ns(apply=False))
                agent.cmd_vault_check(agent._ns())
            for call in run.call_args_list:
                self.assertEqual(call.kwargs["cwd"], str(agent.ROOT))


class ReturnCodeTest(unittest.TestCase):
    """§36.14 — propagação do exit code."""

    def test_run_propaga_exit_code(self):
        with mock.patch.object(
                agent.subprocess, "run",
                return_value=subprocess.CompletedProcess(args=[], returncode=7)):
            self.assertEqual(
                agent.cmd_build(agent._ns(days=60, days_plan=14,
                                          ftp_test=None, no_power=False,
                                          dry_run=True)), 7)

    def test_status_para_no_primeiro_erro(self):
        with mock.patch.object(
                agent.subprocess, "run",
                return_value=subprocess.CompletedProcess(args=[],
                                                         returncode=3)):
            self.assertEqual(agent.cmd_status(agent._ns()), 3)


class InteractiveTest(unittest.TestCase):
    """§36.13 — aliases principais do modo interativo."""

    def test_aliases_principais(self):
        with patch_run() as run, \
                mock.patch("builtins.input", side_effect=["status", "sair"]):
            self.assertEqual(agent.interactive(), 0)
        self.assertEqual(
            run.call_args_list,
            [mock.call(run_cmd("info", "--days", "60"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("model", "--days", "60"), cwd=str(agent.ROOT),
                       check=False),
             mock.call(run_cmd("adherence", "--days", "45"),
                       cwd=str(agent.ROOT), check=False),
             mock.call(run_cmd("ftp-check", "--days", "120", "--weeks", "8"),
                       cwd=str(agent.ROOT), check=False)])

    def test_aliases_hoje_aplicar_confirma(self):
        with patch_run() as run, \
                mock.patch("builtins.input", side_effect=[
                    "hoje aplicar", "s", "sair"]):
            self.assertEqual(agent.interactive(), 0)
        self.assertEqual(
            run.call_args_list[:1],
            [mock.call(run_cmd("check", "--apply"), cwd=str(agent.ROOT),
                       check=False)])

    def test_eof_sai_limpo(self):
        with patch_run(), mock.patch("builtins.input", side_effect=EOFError):
            self.assertEqual(agent.interactive(), 0)

    def test_comando_desconhecido_continua(self):
        with patch_run() as run, \
                mock.patch("builtins.input",
                           side_effect=["foo", "testes", "sair"]):
            self.assertEqual(agent.interactive(), 0)
        self.assertEqual(
            run.call_args_list,
            [mock.call([sys.executable, "-m", "unittest", "discover",
                        "-s", "tests", "-v"], cwd=str(agent.ROOT),
                       check=False)])


if __name__ == "__main__":
    unittest.main()

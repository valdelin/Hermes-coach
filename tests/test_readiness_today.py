"""Issue #58 Passo A, resolucao da pendencia §15: a leitura de HOJE.

Este arquivo fecha a lacuna documentada em
`docs/SPEC-passo-A-readiness.md` §15: a avaliacao de prontidao funcionava em
`build_plan` chamado diretamente, mas o uso diario pela CLI nunca a acionava,
porque `build` comeca o plano AMANHA e a sessao de hoje e preservada verbatim.

O que estes testes exercitam:

- o ponto de entrada REAL (`tp.main([...])`, o mesmo dispatcher do CLI), nao
  `cmd_*` nem `build_plan` em isolamento;
- `scripts/daily_reconcile.sh`, que e o fluxo diario de verdade (systemd
  `cycling-coach-daily.timer`, 00:00), para provar que `check` nao e um comando
  orfao;
- as fronteiras externas por mock (`get_client`, `latest_metrics`, disco em
  diretorio temporario, `_agora`), sem rede e sem escrever fora do tmp.

**Data congelada.** O CLI nao tem injecao de data (criá-la seria refatorar
`date.today()` no projeto inteiro), entao os testes substituem o symbol `date`
dos dois modulos por uma subclasse cujo `today()` e fixo. `_agora()` ja existe
como ponto unico de leitura do relogio em `cmd_check`, e e o que torna a
fronteira "a sessao de hoje ja comecou?" deterministica.
"""
import contextlib
import io
import json
import subprocess
import tempfile
import types
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from src import plan as plan_mod
from src import training_plan as tp
from src.plan import build_plan, save_plan
from src.readiness import (ReadinessAction, ReadinessDecision,
                           assess_readiness_assessment, readiness_decision)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FTP = 182
START_TIME_H = 7
START_TIME_M = 30


def _wh(iso, rhr=62, hrv=30, sleep=5 * 3600, readiness=30):
    """Leitura de wellness que dispara REDUCE (classe YELLOW)."""
    return [{"day": iso, "restingHR": rhr, "hrv": hrv, "sleepSecs": sleep,
             "readiness": readiness}]


def _wh_saudavel(iso):
    """Leitura que NAO pede adaptacao (classe GREEN)."""
    return [{"day": iso, "restingHR": 48, "hrv": 85, "sleepSecs": 8 * 3600,
             "readiness": 88}]


class _FrontFake:
    """Cliente Intervals fake: so o que o CLI realmente consulta.

    `create_events` e fronteira de PUBLICACAO: registra o que tentaram enviar,
    para que o teste falhe se `check` falar com o calendario.
    """

    def __init__(self, eventos, wellness):
        self._eventos = eventos
        self._wellness = wellness
        self.chamadas = {"events": 0, "wellness": 0, "criados": []}

    def events(self, **params):
        self.chamadas["events"] += 1
        return self._eventos

    def wellness(self, **params):
        self.chamadas["wellness"] += 1
        return self._wellness

    def create_events(self, batch):
        self.chamadas["criados"].extend(batch)
        return 200, {"eventsCreated": len(batch)}

    def delete_events(self, ids):
        raise AssertionError("check nao pode apagar eventos")

    def delete_event(self, i):
        raise AssertionError("check nao pode apagar evento")


class FluxoDiarioTest(unittest.TestCase):
    """Base: CLI real, data congelada, disco temporario, fronteiras mockadas."""

    # Quarta-feira de um dia de treino, longe de inicio de mes e de fim de ano.
    HOJE = date(2026, 9, 16)
    ANTES = datetime(2026, 9, 16, 6, 0)     # antes de START_TIME (07:30)
    DEPOIS = datetime(2026, 9, 16, 19, 0)   # depois de START_TIME

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        env = self.root / ".env"
        env.write_text("FTP=182\nGOAL=ftp-builder\n", encoding="utf-8")
        self.plan_file = self.root / "plan.json"

        self.orig = {
            "PLAN_FILE": tp.PLAN_FILE, "ENV_FILE": tp.ENV_FILE,
            "PROJECT_ROOT": tp.PROJECT_ROOT, "get_client": tp.get_client,
            "get_ftp": tp.get_ftp, "get_goal": tp.get_goal,
            "get_training_days": tp.get_training_days,
            "get_weekly_hours": tp.get_weekly_hours,
            "get_long_day": tp.get_long_day,
            "get_periodization": tp.get_periodization,
            "latest_metrics": tp.latest_metrics,
            "_agora": tp._agora,
            "_notify": tp._notify_coach_if_configured,
            "tp_date": tp.date, "plan_date": plan_mod.date,
        }
        tp.PLAN_FILE = self.plan_file
        tp.ENV_FILE = env
        tp.PROJECT_ROOT = self.root
        tp.get_ftp = lambda: FTP
        tp.get_goal = lambda: "ftp-builder"
        tp.get_training_days = lambda: (0, 1, 2, 3, 4)
        tp.get_weekly_hours = lambda: None
        tp.get_long_day = lambda: None
        tp.get_periodization = lambda: None
        # TSB neutro por padrao; cenarios de precedencia sobrescrevem.
        tp.latest_metrics = lambda events: types.SimpleNamespace(
            tsb=0.0, ctl=50.0, atl=50.0)
        tp._agora = lambda: self.ANTES
        tp._notify_coach_if_configured = lambda *a, **k: None

        # Congela `date.today()` nos dois modulos sem tocar no resto do projeto.
        self._data_real = date

        class _DataFalsa(date):
            _frozen = None

            @classmethod
            def today(cls):
                return cls._frozen

        _DataFalsa._frozen = self.HOJE
        tp.date = _DataFalsa
        plan_mod.date = _DataFalsa
        self._DataFalsa = _DataFalsa

        self.cliente = None

    def tearDown(self):
        tp.PLAN_FILE = self.orig["PLAN_FILE"]
        tp.ENV_FILE = self.orig["ENV_FILE"]
        tp.PROJECT_ROOT = self.orig["PROJECT_ROOT"]
        tp.get_client = self.orig["get_client"]
        tp.get_ftp = self.orig["get_ftp"]
        tp.get_goal = self.orig["get_goal"]
        tp.get_training_days = self.orig["get_training_days"]
        tp.get_weekly_hours = self.orig["get_weekly_hours"]
        tp.get_long_day = self.orig["get_long_day"]
        tp.get_periodization = self.orig["get_periodization"]
        tp.latest_metrics = self.orig["latest_metrics"]
        tp._agora = self.orig["_agora"]
        tp._notify_coach_if_configured = self.orig["_notify"]
        tp.date = self.orig["tp_date"]
        plan_mod.date = self.orig["plan_date"]
        self.tmp.cleanup()

    # -- cenarios de estado da sessao -------------------------------------
    def _evento(self, estado="publicada"):
        iso = self.HOJE.isoformat()
        base = {"external_id": f"hermes-plan-{iso}",
                "start_date_local": f"{iso}T{START_TIME_H:02d}:"
                                    f"{START_TIME_M:02d}:00",
                "category": "WORKOUT", "type": "Ride"}
        if estado == "publicada":
            return [base]
        if estado == "concluida":
            return [dict(base, paired_activity_id=4242, activity_id=4242)]
        if estado == "nao_publicada":
            return []
        raise ValueError(estado)

    def _plano(self, start=None, dias=14):
        plano = build_plan([], 0, ftp=FTP, days=dias,
                           start=start or self.HOJE, goal="ftp-builder")
        save_plan(plano, self.plan_file, goal="ftp-builder", race_date=None,
                  ftp_test_date=None, ftp_candidates=[])
        return plano

    def _rodar(self, argv, estado="publicada", wellness=None):
        """Invoca o dispatcher real do CLI e devolve (stdout, plan.json)."""
        self.cliente = _FrontFake(
            self._evento(estado),
            _wh(self.HOJE.isoformat()) if wellness is None else wellness)
        tp.get_client = lambda: self.cliente
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tp.main(list(argv))
        disco = None
        if self.plan_file.exists():
            disco = json.loads(self.plan_file.read_text(encoding="utf-8"))
        return buf.getvalue(), disco

    def _hoje(self, disco):
        iso = self.HOJE.isoformat()
        return next(w for w in disco["workouts"] if w["day"] == iso)

    def _referencia(self, readiness=None):
        return build_plan([], 0, ftp=FTP, days=14, start=self.HOJE,
                          goal="ftp-builder", readiness=readiness)[0]


# ===========================================================================
# 1. A avaliacao diaria produz proposta; e o fluxo diario que a invoca.
# ===========================================================================
class SessaoDeHojeTest(FluxoDiarioTest):

    def test_leitura_de_hoje_com_sessao_elegivel_propoe_reducao(self):
        self._plano()
        saida, disco = self._rodar(["check"])
        self.assertIn("Estado da sessao: publicada", saida)
        self.assertIn("PROPOSTA (prontidao)", saida)
        # Proposta NAO e aplicacao.
        self.assertIn("Nada foi gravado", saida)
        self.assertEqual(self._hoje(disco)["params"],
                         self._referencia()["params"])
        self.assertEqual(self.cliente.chamadas["criados"], [],
                         "check nao pode publicar")

    def test_apply_grava_somente_no_plan_json_local(self):
        self._plano()
        saida, disco = self._rodar(["check", "--apply"])
        self.assertIn("Aplicado no plan.json", saida)
        self.assertIn("NAO foi publicado no calendario", saida)
        self.assertIn("Rode `push` para publicar", saida)
        self.assertEqual(self.cliente.chamadas["criados"], [])
        self.assertLess(float(self._hoje(disco)["tss"]),
                        float(self._referencia()["tss"]))

    def test_dry_run_nao_persiste_nem_publica(self):
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        saida, _ = self._rodar(["check", "--apply", "--dry-run"])
        self.assertIn("[dry-run]", saida)
        self.assertIn("NAO gravada", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)
        self.assertEqual(self.cliente.chamadas["criados"], [])

    def test_reduce_preserva_foco_e_nao_rebaixa_a_zona(self):
        self._plano()
        _, disco = self._rodar(["check", "--apply"])
        depois, antes = self._hoje(disco), self._referencia()
        self.assertEqual(depois["focus"], antes["focus"])
        self.assertGreaterEqual(depois["params"]["on_power"],
                                antes["params"]["on_power"])
        self.assertLess(depois["planned_duration"], antes["planned_duration"])

    def test_fluxo_diario_real_chama_check_antes_de_reconciliar_e_publicar(self):
        """`check` nao pode ser o "comando opcional que o fluxo nunca chama".

        O script `scripts/daily_reconcile.sh` e o que o timer systemd
        `cycling-coach-daily.timer` dispara a 00:00. Se `check` nao estiver
        nele, a §15 continua aberta por construcao.
        """
        script = PROJECT_ROOT / "scripts" / "daily_reconcile.sh"
        texto = script.read_text(encoding="utf-8")
        comandos = [ln.strip() for ln in texto.splitlines()
                    if ln.strip().startswith("step ")
                    and "training_plan.py" in ln]
        nomes = [c.split("training_plan.py")[1].split()[0] for c in comandos]
        self.assertIn("check", nomes,
                      f"daily_reconcile.sh nao chama check: {nomes}")
        self.assertLess(nomes.index("check"), nomes.index("reconcile"),
                        "check deve vir antes de reconcile")
        self.assertLess(nomes.index("reconcile"), nomes.index("push"))
        subprocess.run(["bash", "-n", str(script)], check=True,
                       capture_output=True)


# ===========================================================================
# 2. NONE / sem dado: nada muda.
# ===========================================================================
class SemIntervencaoTest(FluxoDiarioTest):

    def test_decisao_none_nao_altera_nada(self):
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        saida, _ = self._rodar(["check", "--apply"],
                               wellness=_wh_saudavel(self.HOJE.isoformat()))
        self.assertIn("Sem alteracao por prontidao", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)

    def test_sem_wellness_nao_altera_nada(self):
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        saida, _ = self._rodar(["check", "--apply"], wellness=[])
        self.assertIn("nao ha dado de wellness", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)

    def test_leitura_antiga_nao_adapta_hoje_nem_amanha(self):
        """A leitura descreve o dia em que foi medida; nao viaja."""
        self._plano()
        antes = json.loads(self.plan_file.read_text(encoding="utf-8"))
        ontem = (self.HOJE - timedelta(days=1)).isoformat()
        saida, disco = self._rodar(["check", "--apply"], wellness=_wh(ontem))
        self.assertIn("nao descreve hoje", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(disco, antes, "leitura antiga nao pode tocar em nada")
        iso_amanha = (self.HOJE + timedelta(days=1)).isoformat()
        self.assertEqual(
            next(w for w in disco["workouts"] if w["day"] == iso_amanha),
            next(w for w in antes["workouts"] if w["day"] == iso_amanha),
            "leitura de ontem nao pode adaptar a sessao de amanha")


# ===========================================================================
# 3. Elegibilidade: concluida / em andamento / ausente / nao qualitativa.
# ===========================================================================
class ElegibilidadeTest(FluxoDiarioTest):

    def test_sessao_concluida_e_preservada(self):
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        saida, _ = self._rodar(["check", "--apply"], estado="concluida")
        self.assertIn("ja foi realizado", saida)
        self.assertIn("preservado", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)

    def test_sessao_concluida_preservada_mesmo_apos_o_horario(self):
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        tp._agora = lambda: self.DEPOIS
        saida, _ = self._rodar(["check", "--apply"], estado="concluida")
        self.assertIn("ja foi realizado", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)

    def test_sessao_em_andamento_preservada_apos_o_horario(self):
        """Estado DESCONHECIDO: propoe, nao aplica.

        O Intervals nao distingue "começou e ainda nao sincronizou" de "nao
        começou" quando o evento nao tem `paired_activity_id`. Ler a ausencia
        como "nao iniciada" reescreveria uma sessao em andamento — que e
        exatamente o que a tarefa proibe.
        """
        self._plano()
        antes = self.plan_file.read_text(encoding="utf-8")
        tp._agora = lambda: self.DEPOIS
        saida, _ = self._rodar(["check", "--apply"], estado="publicada")
        self.assertIn("estado_desconhecido", saida)
        self.assertIn("sincronizacao pendente", saida)
        self.assertNotIn("Aplicado no plan.json", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes,
                         "proposta sem aplicacao automatica")

    def test_antes_do_horario_a_sessao_publicada_e_elegivel(self):
        """Fronteira de horario: antes de START_TIME, ainda nao iniciada."""
        self._plano()
        tp._agora = lambda: datetime.combine(
            self.HOJE, datetime.min.time()).replace(hour=START_TIME_H,
                                                    minute=START_TIME_M - 1)
        saida, disco = self._rodar(["check", "--apply"], estado="publicada")
        self.assertIn("ainda nao iniciada", saida)
        self.assertIn("Aplicado no plan.json", saida)

    def test_ausencia_de_sessao_hoje_nao_desloca_para_amanha(self):
        self._plano(start=self.HOJE + timedelta(days=1))
        antes = json.loads(self.plan_file.read_text(encoding="utf-8"))
        saida, disco = self._rodar(["check", "--apply"])
        self.assertIn("Hoje nao tem treino no plano", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(disco, antes)
        iso_amanha = (self.HOJE + timedelta(days=1)).isoformat()
        self.assertEqual(next(w for w in disco["workouts"]
                              if w["day"] == iso_amanha)["tss"],
                         next(w["tss"] for w in antes["workouts"]
                              if w["day"] == iso_amanha),
                         "a sessao de amanha nao pode ter sido adaptada")

    def test_sessao_nao_qualitativa_nao_entra(self):
        """REDUCE/REPLACE so existe para sessoes de qualidade."""
        plano = self._plano()
        iso = self.HOJE.isoformat()
        for w in plano:
            if w["day"] == iso:
                w["focus"] = "zone2"
        save_plan(plano, self.plan_file, goal="ftp-builder", race_date=None,
                  ftp_test_date=None, ftp_candidates=[])
        antes = self.plan_file.read_text(encoding="utf-8")
        saida, _ = self._rodar(["check", "--apply"])
        self.assertIn("nao uma sessao de qualidade", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), antes)


# ===========================================================================
# 4. Precedencia de TSB e credito da fonte.
# ===========================================================================
class PrecedenciaTest(FluxoDiarioTest):

    def test_tsb_vencedor_nao_credita_a_prontidao(self):
        """Com TSB abaixo do limite a regra mais restritiva e do TSB.

        REDUCE preservaria o `focus`; REPLACE (TSB) troca. Aqui a leitura nao
        pode acrescentar nada, nao pode receber credito no razao do orcamento,
        e a saida tem que dizer que quem manda e o TSB — nao um "nada a
        alterar" opaco.
        """
        self._plano()
        antes = json.loads(self.plan_file.read_text(encoding="utf-8"))
        tp.latest_metrics = lambda events: types.SimpleNamespace(
            tsb=-30.0, ctl=80.0, atl=50.0)
        saida, disco = self._rodar(["check", "--apply"])
        self.assertIn("nada atribuivel a prontidao", saida)
        self.assertIn("o TSB", saida)
        self.assertNotIn("PROPOSTA", saida)
        self.assertNotIn("Aplicado no plan.json", saida,
                         "TSB nao e alterado por `check`; `build` e a "
                         "autoridade do TSB")
        self.assertEqual(disco, antes, "nada muda quando a readiness nao age")

        iso = self.HOJE.isoformat()
        avaliacao, trace = assess_readiness_assessment(_wh(iso))
        decisao = readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low,
            trace.coverage, trace.observations, reference_day=iso)
        self.assertIs(decisao.action, ReadinessAction.REDUCE)
        st = plan_mod.training_plan_state("ftp-builder", None, self.HOJE,
                                         0.0, 0.0, -30.0, decisao)
        self.assertFalse(plan_mod._readiness_dirige(st, iso),
                         "TSB vencedor: a prontidao nao dirige e nao recebe "
                         "credito no razao")

    def test_ledger_por_fonte_preservado(self):
        """Os quatro cenarios do item 1 continuam valendo no motor."""
        iso = self.HOJE.isoformat()
        mk = lambda escore, tsb: plan_mod.training_plan_state(
            "ftp-builder", None, self.HOJE, 0.0, 0.0, tsb,
            ReadinessDecision(
                ReadinessAction.REDUCE if escore < 0.5 else ReadinessAction.NONE,
                "x", None, 0.4, False, False, (), iso))
        self.assertFalse(plan_mod._readiness_dirige(mk(0.8, 0.0), iso))
        self.assertFalse(plan_mod._readiness_dirige(mk(0.2, -30.0), iso))
        self.assertTrue(plan_mod._readiness_dirige(mk(0.2, 0.0), iso))
        # REDUCE real nao promove nenhum dia futuro.
        avaliacao, trace = assess_readiness_assessment(_wh(iso))
        decisao = readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low,
            trace.coverage, trace.observations, reference_day=iso)
        base = build_plan([], 0, ftp=FTP, days=14, start=self.HOJE,
                          goal="ftp-builder")
        adpt = build_plan([], 0, ftp=FTP, days=14, start=self.HOJE,
                          goal="ftp-builder", readiness=decisao)
        for b, a in zip(base, adpt):
            self.assertLessEqual(float(a["tss"]), float(b["tss"]) + 1e-9)


# ===========================================================================
# 5. Cumulatividade.
# ===========================================================================
class SemCumulatividadeTest(FluxoDiarioTest):

    def test_reexecucao_com_as_mesmas_entradas_nao_reduz_de_novo(self):
        self._plano()
        base = float(self._referencia()["tss"])
        saida1, d1 = self._rodar(["check", "--apply"])
        self.assertIn("Aplicado no plan.json", saida1)
        tss1 = float(self._hoje(d1)["tss"])
        saida2, d2 = self._rodar(["check", "--apply"])
        self.assertIn("ja aplicada", saida2)
        tss2 = float(self._hoje(d2)["tss"])
        saida3, d3 = self._rodar(["check", "--apply"])
        tss3 = float(self._hoje(d3)["tss"])
        self.assertLess(tss1, base, "a primeira execucao reduz")
        self.assertEqual(tss1, tss2, "a segunda nao pode reduzir de novo")
        self.assertEqual(tss2, tss3, "a terceira tampouco")
        del d3

    def test_check_e_build_conferem_a_mesma_sessao(self):
        """Motor unico: `check` nao pode divergir de `build`."""
        iso = self.HOJE.isoformat()
        avaliacao, trace = assess_readiness_assessment(_wh(iso))
        decisao = readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low,
            trace.coverage, trace.observations, reference_day=iso)
        via_build = build_plan([], 0, ftp=FTP, days=1, start=self.HOJE,
                               goal="ftp-builder", readiness=decisao)[0]
        self._plano()
        _, disco = self._rodar(["check", "--apply"])
        obtido = self._hoje(disco)
        self.assertEqual(obtido["params"], via_build["params"])
        self.assertAlmostEqual(float(obtido["tss"]),
                               float(via_build["tss"]), places=6)


# ===========================================================================
# 6. Separacao proposta / aplicacao / publicacao.
# ===========================================================================
class PublicacaoTest(FluxoDiarioTest):

    def test_all_nao_avalia_readiness_de_hoje(self):
        """`all` nao pode avaliar e publicar a sessao de hoje em uma tacada.

        `cmd_all` = build + reconcile + push. Se ele chamasse `check`, a
        proposta de prontidao entraria no mesmo comando que publica, sem
        nenhuma confirmacao no meio.
        """
        import inspect
        self.assertNotIn("cmd_check", inspect.getsource(tp.cmd_all))
        saida, _ = self._rodar(["all", "--dry-run"])
        self.assertIn("Apenas o planejamento foi simulado", saida)
        self.assertEqual(self.cliente.chamadas["criados"], [])

    def test_proposta_nao_aplicada_nao_chega_ao_push(self):
        """Proposta sem `--apply` nao altera o plan.json, entao um `push`
        subsequente publica o plano original, nunca a proposta."""
        self._plano()
        _, disco = self._rodar(["check"])
        original = self._hoje(disco)
        saida, _ = self._rodar(["push", "--start", self.HOJE.isoformat(),
                                "--dry-run"])
        self.assertIn("dry-run: enviaria", saida)
        self.assertEqual(self._hoje(disco), original)
        self.assertEqual(self.cliente.chamadas["criados"], [])

    def test_push_e_a_unica_etapa_que_publica(self):
        """`check` nao tem nenhuma fronteira de publicacao no caminho do CLI."""
        import inspect
        fonte = inspect.getsource(tp.cmd_check)
        for proibido in ("create_events", "delete_events", "client.push",
                         "cmd_push"):
            self.assertNotIn(proibido, fonte,
                             f"cmd_check nao pode conter {proibido}")


if __name__ == "__main__":
    unittest.main()
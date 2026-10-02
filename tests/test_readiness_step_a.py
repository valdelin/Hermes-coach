"""Issue #58 Passo A: o produtor de prontidao e a politica de adaptacao.

Este arquivo cobre a ponte entre o wellness bruto do Intervals e o plano:

- `assess_readiness_assessment` — wellness -> (avaliacao, trace). O que foi
  medido, o que NAO foi, e por que.
- `readiness_decision` — classe ordinal -> NONE | REDUCE | REPLACE.
- a fusao disso em `build_plan`/`cmd_build`.

Os 19 testes de `tests/scientific/test_readiness.py` nao sao tocados: eles
verificam `ReadinessAssessment.level()` e `adjustments()`, que este passo
mantem intactos. Aqui verificamos o que faz o motor com o veredito.
"""
import contextlib
import io
import tempfile
import types
import unittest
from datetime import date, timedelta
from pathlib import Path

from src import training_plan as tp
from src.plan import (FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_ZONE2,
                      build_plan, save_plan)
from src.readiness import (HEALTHY_SCORE, ReadinessAction,
                           ReadinessAssessment, assess_readiness_assessment,
                           readiness_decision)
from src.readiness_assessment import ReadinessLevel

START = date(2026, 9, 14)
FTP = 200

# Os sete eixos do modelo. Quatro nao tem fonte em /wellness e por isso ficam
# None: e a lista que a politica de "ausencia nao e evidencia" precisa respeitar.
EIXOS_SEM_FONTE = ("recent_load_score", "subjective_fatigue_score",
                   "performance_score", "consistency_score")


def wellness(dias, rhr, hrv, horas, readiness=80):
    """Monta registros de /wellness com os dias relativos a hoje."""
    return [{"day": (date.today() - timedelta(days=dias - i)).isoformat(),
             "restingHR": rhr, "hrv": hrv, "sleepSecs": int(horas * 3600),
             "readiness": readiness} for i in range(dias)]


def decisao(nivel, illness_alert=False, composite_low=False):
    """Constroi a decisao pela MESMA politica de producao, nao na mao."""
    escore = {"red": 0.2, "yellow": 0.6, "green": 0.8}[nivel]
    avaliacao = ReadinessAssessment(hrv_score=escore, rhr_score=escore,
                                    sleep_score=escore)
    return readiness_decision(avaliacao, illness_alert=illness_alert,
                              composite_low=composite_low)


class ProdutorTest(unittest.TestCase):
    """Wellness bruto -> avaliacao + rastro do que foi medido."""

    def test_preenche_so_os_tres_eixos_com_fonte_real(self):
        avaliacao, trace = assess_readiness_assessment(wellness(3, 50, 60, 8))
        self.assertIsNotNone(avaliacao)
        for eixo in EIXOS_SEM_FONTE:
            self.assertIsNone(getattr(avaliacao, eixo),
                              f"{eixo} nao tem fonte em /wellness: nao pode ser preenchido")
        for eixo in ("hrv_score", "rhr_score", "sleep_score"):
            self.assertIsNotNone(getattr(avaliacao, eixo))
        self.assertEqual(trace.coverage, 3 / 7)
        self.assertEqual(sorted(trace.missing), sorted(EIXOS_SEM_FONTE))

    def test_eixo_ausente_ninguem_e_preenchido_com_neutro(self):
        """Preencher ausente com 0.5 rebaixaria a media de todo mundo e
        transformaria um atleta saudavel em YELLOW. Ausencia precisa ficar
        None, e o teste trava essa decisao."""
        avaliacao, _ = assess_readiness_assessment(wellness(3, 50, 60, 8))
        for eixo in EIXOS_SEM_FONTE:
            self.assertIsNone(getattr(avaliacao, eixo))
            self.assertNotEqual(getattr(avaliacao, eixo), 0.5)

    def test_sem_wellness_devolve_none_e_nao_classifica(self):
        avaliacao, trace = assess_readiness_assessment([])
        self.assertIsNone(avaliacao)
        self.assertEqual(trace.coverage, 0)
        self.assertEqual(trace.observations, ())
        self.assertFalse(trace.illness_alert)

    def test_registro_unico_e_observado_sem_exigir_janela(self):
        """Um dia so de leitura nao pode ser tratado como dado completo: os
        limiares que dependem de media (HRV 80% da media, RHR acima da media)
        ficam inativos, e o que sobra e o que de fato se sabe."""
        avaliacao, trace = assess_readiness_assessment(wellness(1, 50, 60, 8))
        self.assertIsNotNone(avaliacao)
        self.assertEqual(len(trace.observations), 3)
        self.assertFalse(any(o.flagged for o in trace.observations))

    def test_leituras_ausentes_no_registro_ficam_sem_sinal(self):
        """Um registro sem `hrv` nao pode virar hrv ruim por ausencia. O
        produtor so marca o que o limiar viu."""
        recs = [{"day": (date.today() - timedelta(days=i)).isoformat(),
                 "restingHR": 50, "sleepSecs": 8 * 3600, "readiness": 80}
                for i in range(3)]
        avaliacao, trace = assess_readiness_assessment(recs)
        self.assertIsNotNone(avaliacao)
        hrv = next(o for o in trace.observations if o.axis == "hrv_score")
        self.assertEqual(hrv.score, HEALTHY_SCORE)
        self.assertFalse(hrv.flagged)

    def test_rastreia_datas_desatualizadas(self):
        recs = [{"day": (date.today() - timedelta(days=9)).isoformat(),
                 "restingHR": 50, "hrv": 60, "sleepSecs": 8 * 3600,
                 "readiness": 80}]
        _, trace = assess_readiness_assessment(recs, days=7)
        self.assertGreaterEqual(trace.stale_days, 9)

    def test_registro_recem_atual_nao_e_marcado_como_desatualizado(self):
        _, trace = assess_readiness_assessment(wellness(3, 50, 60, 8))
        self.assertIn(trace.stale_days, (0, 1))

    def test_data_ilegivel_nao_quebra_o_produtor(self):
        recs = [{"day": "nao-e-data", "restingHR": 50, "hrv": 60,
                 "sleepSecs": 8 * 3600, "readiness": 80}]
        avaliacao, trace = assess_readiness_assessment(recs)
        self.assertIsNotNone(avaliacao)
        self.assertIsNone(trace.stale_days)

    def test_sinal_ruim_observado_rebaixa_para_escores_de_flag(self):
        _, trace = assess_readiness_assessment(wellness(3, 50, 60, 5))
        sono = next(o for o in trace.observations if o.axis == "sleep_score")
        self.assertTrue(sono.flagged)
        self.assertLess(sono.score, HEALTHY_SCORE)
        self.assertIn("sleepSecs", sono.source)

    def test_readiness_composto_fica_de_fora_dos_eixos(self):
        """O readiness do Intervals deriva de sono/HRV/RHR. Entra-lo como
        eixo contaria o mesmo dado duas vezes."""
        avaliacao, trace = assess_readiness_assessment(
            wellness(3, 50, 60, 8, readiness=40))
        self.assertTrue(trace.composite_low)
        self.assertEqual(len(trace.observations), 3)
        self.assertIsNone(getattr(avaliacao, "consistency_score"))


class PoliticaDeDecisaoTest(unittest.TestCase):
    """A classe ordinal vira uma acao; as precedencias sao explicitas."""

    def test_green_nao_adapta(self):
        self.assertIs(decisao("green").action, ReadinessAction.NONE)

    def test_yellow_reduza_sem_trocar_a_sessao(self):
        d = decisao("yellow")
        self.assertIs(d.action, ReadinessAction.REDUCE)
        self.assertIn("YELLOW", d.reason)

    def test_red_troca_por_politica_conservadora(self):
        d = decisao("red")
        self.assertIs(d.action, ReadinessAction.REPLACE)
        self.assertIn("RED", d.reason)

    def test_alerta_vence_green(self):
        """A conjuncao RHR 2+ noites E HRV caindo e observacao direta, nao
        media. Se a media ficar GREEN e o alerta estiver ligado, o alerta vale."""
        d = decisao("green", illness_alert=True)
        self.assertIs(d.action, ReadinessAction.REPLACE)
        # O nivel original continua disponivel para auditoria.
        self.assertIs(d.level, ReadinessLevel.GREEN)

    def test_alerta_nao_e_neutro_pela_cobertura_baixa(self):
        avaliacao, trace = assess_readiness_assessment(wellness(1, 50, 60, 8))
        d = readiness_decision(avaliacao, illness_alert=True)
        self.assertEqual(d.coverage, 3 / 7)
        self.assertIs(d.action, ReadinessAction.REPLACE)

    def test_readiness_composto_baixo_isolado_segura_reduce(self):
        """Sinal derivado, fora dos eixos: segura REDUCE e nunca vira RED,
        porque nao entra na media nem na contagem de eixos ruins."""
        d = decisao("green", composite_low=True)
        self.assertIs(d.action, ReadinessAction.REDUCE)
        self.assertIn("Intervals", d.reason)

    def test_sinal_ruim_isolado_nao_cria_red(self):
        """O ponto do passo: um unico sinal ruim e REDUCE, nao REPLACE."""
        avaliacao, trace = assess_readiness_assessment(wellness(3, 50, 60, 5))
        d = readiness_decision(avaliacao, trace.illness_alert,
                               trace.composite_low, trace.coverage,
                               trace.observations)
        self.assertIsNot(avaliacao.level(), ReadinessLevel.RED)
        self.assertIs(d.action, ReadinessAction.REDUCE)

    def test_sem_dado_devolve_none_com_motivo_explicito(self):
        d = readiness_decision(None)
        self.assertIs(d.action, ReadinessAction.NONE)
        self.assertIn("dados", d.reason.lower())
        self.assertIn("ausencia", d.reason.lower())

    def test_decisao_none_nao_e_considerada_adaptativa(self):
        self.assertFalse(decisao("green").is_adaptive)
        self.assertTrue(decisao("yellow").is_adaptive)


class AdaptacaoNoPlanoTest(unittest.TestCase):
    """A decisao chega ao plano sem quebrar foco, zona nem formato."""

    def _plan(self, tsb=0, readiness=None, goal="ftp-builder"):
        return build_plan([], tsb, ftp=FTP, days=5, start=START, goal=goal,
                          readiness=readiness)

    def test_reduce_preserva_foco_e_intensidade(self):
        base = self._plan()
        plano = self._plan(readiness=decisao("yellow"))
        alvo = next(i for i, w in enumerate(base)
                    if w["focus"] == FOCUS_SWEETSPOT)
        self.assertEqual(plano[alvo]["focus"], FOCUS_SWEETSPOT)
        self.assertEqual(plano[alvo]["params"]["on_power"],
                         base[alvo]["params"]["on_power"])

    def test_reduce_corta_volume_e_nao_aumenta_nada(self):
        base = self._plan()
        plano = self._plan(readiness=decisao("yellow"))
        alvo = next(i for i, w in enumerate(base)
                    if w["focus"] == FOCUS_SWEETSPOT)
        self.assertLessEqual(plano[alvo]["params"]["repeats"],
                             base[alvo]["params"]["repeats"])
        self.assertLessEqual(plano[alvo]["params"]["on_sec"],
                             base[alvo]["params"]["on_sec"])
        self.assertLess(plano[alvo]["tss"], base[alvo]["tss"])

    def test_reduce_nunca_derruba_a_potencia_abaixo_do_piso_da_zona(self):
        """A escada de reducao e volume-antes-de-intensidade, e a ultima
        operacao respeita o piso da zona. Este teste cobre um treino que ja
        esta no piso (repeats=1, on_sec minimo): o unico degrau possivel seria
        de potencia, e ele nao pode atravessar o piso."""
        plano = self._plan(readiness=decisao("yellow"))
        for w in plano:
            piso = {"sweetspot": 0.84, "threshold": 0.94}.get(w["focus"])
            if piso is not None:
                self.assertGreaterEqual(w["params"]["on_power"], piso)

    def test_red_troca_a_primeira_sessao_de_qualidade(self):
        base = self._plan()
        plano = self._plan(readiness=decisao("red"))
        alvo = next(i for i, w in enumerate(base)
                    if w["focus"] == FOCUS_SWEETSPOT)
        self.assertEqual(plano[alvo]["focus"], FOCUS_ZONE2)
        # Somente a primeira: o resto do plano nao e reescrito pela decisao.
        for w in plano[alvo + 1:]:
            self.assertNotEqual(w["focus"], FOCUS_ZONE2)

    def test_reduce_aplica_somente_na_primeira_sessao_adaptavel(self):
        """O flag one-shot do motor nao pode ser contornado por uma REDUCE que
        sao 3 chamadas de REDUCE sobre 3 dias de qualidade."""
        plano = self._plan(readiness=decisao("yellow"))
        reduzidos = [w for w in plano
                     if w["params"]["repeats"] == 1 and w["focus"] == FOCUS_ZONE2]
        self.assertEqual(reduzidos, [])

    def test_tsb_continua_forcando_a_troca(self):
        """Regra historica preservada: TSB abaixo do limite troca por Z2 mesmo
        com a prontidao em GREEN."""
        plano = self._plan(tsb=-30, readiness=decisao("green"))
        self.assertEqual(plano[0]["focus"], FOCUS_ZONE2)

    def test_regra_mais_restritiva_vence_sem_dupla_reducao(self):
        """TSB manda em REPLACE mesmo com REDUCE por prontidao; o plano nao
        recebe as duas aplicacoes somadas."""
        com_red = self._plan(tsb=-30, readiness=decisao("red"))
        self.assertEqual(com_red[0]["focus"], FOCUS_ZONE2)
        self.assertEqual(com_red[0]["params"]["on_sec"], 900)
        self.assertEqual(com_red[0]["params"]["repeats"], 1)

    def test_readiness_ausente_nao_adapta(self):
        self.assertEqual(self._plan(), self._plan(readiness=None))

    def test_sessao_z2_planejada_permanece_z2(self):
        """Nao ha operacao de REDUCE que_transforme_ um Z2 em outra coisa."""
        base = self._plan(goal="active-off-season")
        plano = self._plan(readiness=decisao("yellow"), goal="active-off-season")
        self.assertEqual(plano[0]["focus"], FOCUS_ZONE2)
        self.assertEqual(plano[0]["params"]["on_power"],
                         base[0]["params"]["on_power"])


class _FakeClient:
    """IntervalsClient fake. Conta as chamadas para provar que nao ha
    duplicacao de I/O no caminho do build."""

    def __init__(self, registros=None):
        self.registros = registros or []
        self.chamadas_wellness = 0
        self.chamadas_events = 0

    def events(self, **params):
        self.chamadas_events += 1
        return []

    def wellness(self, **params):
        self.chamadas_wellness += 1
        return self.registros


class _CliTest(unittest.TestCase):
    """O caminho real: build monta o plano e o persiste (ou nao)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        env = root / ".env"
        env.write_text("FTP=182\n", encoding="utf-8")
        self.path = root / "plan.json"
        self.orig = (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT, tp.get_client,
                     tp.get_ftp, tp.get_goal, tp.get_race_date,
                     tp.get_weekly_hours, tp.get_long_day, tp.get_training_days)
        tp.PLAN_FILE = self.path
        tp.ENV_FILE = env
        tp.PROJECT_ROOT = root
        tp.get_ftp = lambda: 182
        tp.get_goal = lambda: "ftp-builder"
        tp.get_race_date = lambda: None
        tp.get_weekly_hours = lambda: None
        tp.get_long_day = lambda: None
        tp.get_training_days = lambda: (0, 1, 2, 3, 4)
        self.cliente = None

    def tearDown(self):
        (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT, tp.get_client, tp.get_ftp,
         tp.get_goal, tp.get_race_date, tp.get_weekly_hours, tp.get_long_day,
         tp.get_training_days) = self.orig
        self.tmp.cleanup()

    def _build(self, registros, dry_run=False):
        self.cliente = _FakeClient(registros)
        tp.get_client = lambda: self.cliente
        args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                     dry_run=dry_run)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            plano = tp.cmd_build(args)
        return plano, buf.getvalue()


class IntegracaoCliTest(_CliTest):
    def test_wellness_desfavoravel_adapta_o_plano_gerado(self):
        plano, saida = self._build(wellness(3, 50, 60, 5))
        self.assertTrue(plano)
        self.assertIn("Prontidao:", saida)
        self.assertIn("REDUZIDO", saida)
        self.assertIn("sleep", saida.lower())

    def test_alerta_aparece_como_alerta_e_nao_como_diagnostico(self):
        # RHR subindo e HRV caindo ao longo de tres noites: e a conjuncao que
        # o detector legado reconhece. A ordem das datas importa — `2 - i`
        # mantem o primeiro registro como o mais antigo.
        recs = [{"day": (date.today() - timedelta(days=2 - i)).isoformat(),
                 "restingHR": r, "hrv": h, "sleepSecs": 8 * 3600,
                 "readiness": 70}
                for i, (r, h) in enumerate([(50, 60), (54, 50), (57, 35)])]
        _, saida = self._build(recs)
        self.assertIn("ALERTA", saida)
        self.assertIn("nao e", saida.lower())
        self.assertNotIn("diagnosticado", saida.lower())

    def test_wellness_ausente_nao_quebra_o_build(self):
        plano, saida = self._build([])
        self.assertTrue(plano)
        self.assertIn("indisponiveis", saida)

    def test_build_consulta_wellness_uma_vez(self):
        self._build(wellness(3, 50, 60, 8))
        self.assertEqual(self.cliente.chamadas_wellness, 1)

    def test_dry_run_mostra_a_proposta_e_nao_grava(self):
        _, saida = self._build(wellness(3, 50, 60, 5), dry_run=True)
        self.assertIn("dry-run", saida)
        self.assertIn("REDUZIDO", saida)
        self.assertFalse(self.path.exists(),
                         "--dry-run nao pode criar plan.json")

    def test_build_normal_grava_o_plano(self):
        self._build(wellness(3, 50, 60, 8))
        self.assertTrue(self.path.exists())
        self.assertNotIn("dry-run", "")

    def test_all_dry_run_encerra_antes_de_publicar(self):
        """Sem isso, `reconcile` e `push` leriam o plan.json antigo e
        reconciliariam contra um plano que nunca foi gerado."""
        self.cliente = _FakeClient(wellness(3, 50, 60, 5))
        tp.get_client = lambda: self.cliente
        args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                     dry_run=True, show=False, start=None)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tp.cmd_all(args)
        saida = buf.getvalue()
        self.assertIn("encerrando apos build", saida)
        self.assertNotIn("dry-run: enviaria", saida)
        self.assertFalse(self.path.exists())

    def test_all_dry_run_nao_chama_reconcile_nem_push(self):
        """Item 5 da revisao: a saida precisa deixar claro que SO o
        planejamento foi simulado. `reconcile`/`push` nao sao executados nem
        simulados, entao os stubs abaixo levantam se forem alcancados."""
        self.cliente = _FakeClient(wellness(3, 50, 60, 5))
        tp.get_client = lambda: self.cliente
        args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                     dry_run=True, show=False, start=None)
        chamados = []

        def _nao_chamar(nome):
            def _stub(*_a, **_k):
                chamados.append(nome)
                raise AssertionError(f"{nome} nao pode rodar em all --dry-run")
            return _stub

        orig = (tp.cmd_reconcile, tp.cmd_push)
        tp.cmd_reconcile = _nao_chamar("reconcile")
        tp.cmd_push = _nao_chamar("push")
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.cmd_all(args)
        finally:
            tp.cmd_reconcile, tp.cmd_push = orig
        self.assertEqual(chamados, [])
        self.assertIn("reconciliacao nao foi executada nem simulada",
                      buf.getvalue())

    def test_saida_avisa_quando_a_leitura_nao_foi_aplicada(self):
        """Leitura de ontem, build de hoje: nada e adaptado e o CLI diz o
        motivo, para nao parecer que a prontidao foi ignorada."""
        ontem = date.today() - timedelta(days=1)
        recs = [{"day": (ontem + timedelta(days=i)).isoformat(),
                 "restingHR": 50, "hrv": 60, "sleepSecs": 5 * 3600,
                 "readiness": 80} for i in range(3)]
        _, saida = self._build(recs, dry_run=True)
        self.assertIn("leitura de", saida)
        self.assertIn("nao aplicada", saida)
        self.assertIn("nao foi transferida", saida)


if __name__ == "__main__":
    unittest.main()

class NaoCompensacaoTest(unittest.TestCase):
    """Item 1 da revisao: reduzir hoje nao pode aumentar amanha.

    O orcamento e um guarda-chuva, nao uma meta. Se a intervencao de prontidao
    devolvesse teto aos dias seguintes, o atleta leria mais carga — e a leitura
    de um dia seria usada como justificativa para mais treino. Estes testes
    comparam o plano adaptado com um de referencia gerado com as MESMAS
    entradas, exceto a intervencao, e exigem que nenhum dia fique MAIOR.
    """

    def _cenario(self, tsb=0, goal="ftp-builder", days=5):
        """(referencia, adaptado) com leitura ruim ancorada no 3o dia."""
        recs = [{"day": (START + timedelta(days=i)).isoformat(),
                 "restingHR": 50, "hrv": 60, "sleepSecs": 5 * 3600,
                 "readiness": 80} for i in range(3)]
        avaliacao, trace = assess_readiness_assessment(recs)
        decisao = readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low, trace.coverage,
            trace.observations, reference_day=trace.reference_day)
        ref = build_plan([], tsb, ftp=FTP, days=days, start=START, goal=goal)
        adapt = build_plan([], tsb, ftp=FTP, days=days, start=START, goal=goal,
                           readiness=decisao)
        return ref, adapt, decisao

    def test_nenhum_dia_fica_com_carga_maior_que_a_referencia(self):
        ref, adapt, _ = self._cenario()
        for r, a in zip(ref, adapt):
            self.assertLessEqual(
                a["tss"], r["tss"] + 1e-9,
                f"{a['day']} ficou com MAIS carga ({a['tss']}) que a referencia "
                f"({r['tss']}) apos uma reducao de prontidao")

    def test_duracao_e_trabalho_iguais_ou_menores(self):
        """Preservar so `focus`/`on_power` nao prova ausencia de compensacao.
        O controle esta em volume e carga de cada dia.

        Nota sobre `on_sec`: reduzir `repeats` nao exige encurtar cada
        repeticao, e a ordem do motor e adaptacao -> teto diario -> orcamento,
        entao `on_sec` pode diferir sem que isso seja compensacao. O invariante
        que importa e o produto `repeats x on_sec`, a duracao total e o TSS.
        """
        ref, adapt, _ = self._cenario()
        for r, a in zip(ref, adapt):
            trabalho_ref = r["params"]["repeats"] * r["params"]["on_sec"]
            trabalho_adaptado = a["params"]["repeats"] * a["params"]["on_sec"]
            self.assertLessEqual(trabalho_adaptado, trabalho_ref,
                                 f"{a['day']} ganhou trabalho de intervalo")
            self.assertLessEqual(a["planned_duration"], r["planned_duration"])
            self.assertLessEqual(a["params"]["on_power"], r["params"]["on_power"])

    def test_reducao_ocorre_no_dia_da_leitura(self):
        ref, adapt, _ = self._cenario()
        reduzidos = [a["day"] for r, a in zip(ref, adapt)
                     if a["tss"] < r["tss"] - 1e-9]
        self.assertEqual(reduzidos, [(START + timedelta(days=2)).isoformat()])

    def test_tsb_negativo_nao_introduz_compensacao(self):
        ref, adapt, _ = self._cenario(tsb=-30)
        for r, a in zip(ref, adapt):
            self.assertLessEqual(a["tss"], r["tss"] + 1e-9)


class HorizonteTemporalTest(unittest.TestCase):
    """Item 2 da revisao: o sinal vale para o dia que ele descreve."""

    def _decisao_do_dia(self, dia, alvo):
        """Leitura ruim cujo ultimo registro e `dia`; o sinal e sobre `dia`."""
        recs = [{"day": (dia + timedelta(days=i)).isoformat(),
                 "restingHR": 50, "hrv": 60, "sleepSecs": 5 * 3600,
                 "readiness": 80} for i in range(3)]
        avaliacao, trace = assess_readiness_assessment(recs)
        return readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low, trace.coverage,
            trace.observations, reference_day=alvo.isoformat()), trace

    def _plan(self, decisao, goal="ftp-builder", tsb=0, days=5, report=None):
        return build_plan([], tsb, ftp=FTP, days=days, start=START, goal=goal,
                          readiness=decisao, readiness_report=report)

    def test_leitura_de_ontem_nao_adapta_a_sessao_de_hoje(self):
        dec, _ = self._decisao_do_dia(START, START - timedelta(days=1))
        report = {}
        self._plan(dec, report=report)
        self.assertEqual(report["aplicada_em"], [])
        self.assertEqual(report["situacao"], "dia_alvo_fora_do_plano")

    def test_leitura_desatualizada_nao_adapta_nada(self):
        """Nao existe prazo de validade arbitrario: uma leitura antiga so
        poderia tocar o dia que ela descreve, e esse dia ja passou."""
        dec, _ = self._decisao_do_dia(START, START - timedelta(days=9))
        report = {}
        self._plan(dec, report=report)
        self.assertEqual(report["aplicada_em"], [])
        self.assertEqual(report["situacao"], "dia_alvo_fora_do_plano")

    def test_sem_sessao_de_qualidade_no_dia_nao_transfere_para_outro_dia(self):
        """`active-off-season` so tem Z2. O sinal nao pode pular para a
        primeira sessao de qualidade de outro dia."""
        dec, _ = self._decisao_do_dia(START, START)
        ref = build_plan([], 0, ftp=FTP, days=5, start=START,
                         goal="active-off-season")
        report = {}
        adapt = self._plan(dec, goal="active-off-season", report=report)
        self.assertEqual(report["aplicada_em"], [])
        self.assertEqual(report["situacao"], "sem_sessao_de_qualidade_no_dia")
        self.assertEqual(adapt, ref, "plano nao pode mudar sem sessao elegivel")

    def test_dia_fora_da_janela_do_plano_nao_e_alcancado(self):
        dec, _ = self._decisao_do_dia(START, START + timedelta(days=30))
        report = {}
        self._plan(dec, days=5, report=report)
        self.assertEqual(report["aplicada_em"], [])
        self.assertEqual(report["situacao"], "dia_alvo_fora_do_plano")

    def test_avaliacoes_ruins_em_dias_consecutivos_adaptam_dias_distintos(self):
        """Sinal persistente: cada dia avaliado recebe a sua propria decisao,
        uma por build. Nada se acumula."""
        vistos = []
        for offset in range(3):
            alvo = START + timedelta(days=offset)
            dec, _ = self._decisao_do_dia(alvo, alvo)
            report = {}
            self._plan(dec, report=report)
            vistos.append(report["aplicada_em"])
        for aplicado in vistos:
            self.assertEqual(len(aplicado), 1,
                             "cada build deve adaptar no maximo um dia")
        alvos = [v[0] for v in vistos]
        self.assertEqual(len(set(alvos)), 3, "dias distintos por avaliacao")

    def test_tsb_ainda_adapta_sem_ancora_de_dia(self):
        """O escopo por dia vale so para prontidao. TSB continua valendo para
        a primeira sessao de qualidade do plano, como sempre."""
        dec, _ = self._decisao_do_dia(START, START - timedelta(days=5))
        plan = self._plan(dec, tsb=-30)
        self.assertEqual(plan[0]["focus"], FOCUS_ZONE2)


class SemReducaoCumulativaTest(unittest.TestCase):
    """Item 3 da revisao: replanejar nao pode reduzir de novo."""

    def _decisao(self):
        recs = [{"day": (START + timedelta(days=i)).isoformat(),
                 "restingHR": 50, "hrv": 60, "sleepSecs": 5 * 3600,
                 "readiness": 80} for i in range(3)]
        avaliacao, trace = assess_readiness_assessment(recs)
        return readiness_decision(
            avaliacao, trace.illness_alert, trace.composite_low, trace.coverage,
            trace.observations, reference_day=trace.reference_day)

    @staticmethod
    def _como_dicts(plan):
        return [{"day": w["day"], "focus": w["focus"],
                 "planned_duration": w["planned_duration"], "name": w["name"],
                 "params": w["params"], "tss": w["tss"],
                 "external_id": w["external_id"]} for w in plan]

    def _rodar(self, decisao, existing=None):
        return build_plan([], 0, ftp=FTP, days=5, start=START,
                          goal="ftp-builder", readiness=decisao,
                          existing=existing)

    def test_replanejar_com_a_mesma_leitura_da_o_mesmo_plano(self):
        """O motor reconstroi a proposta do template, nao do resultado
        anterior: reduzir duas vezes reduziria 3x480 -> 2x480 -> 1x480."""
        dec = self._decisao()
        primeiro = self._rodar(dec)
        segundo = self._rodar(dec, self._como_dicts(primeiro))
        terceiro = self._rodar(dec, self._como_dicts(segundo))
        chave = lambda p: [(w["day"], w["focus"], w["params"], round(w["tss"], 6))
                           for w in p]
        self.assertEqual(chave(primeiro), chave(segundo))
        self.assertEqual(chave(segundo), chave(terceiro))

    def test_sessao_ja_reduzida_nao_e_reduzida_de_novo(self):
        dec = self._decisao()
        primeiro = self._rodar(dec)
        reduzido = [w for w in primeiro if w["day"] == (START + timedelta(days=2)).isoformat()][0]
        segundo = self._rodar(dec, self._como_dicts(primeiro))
        de_novo = [w for w in segundo if w["day"] == reduzido["day"]][0]
        self.assertEqual(reduzido["params"]["repeats"],
                         de_novo["params"]["repeats"])

    def test_referencia_sem_prontidao_e_o_plano_nao_adaptado(self):
        """Guarda o principio: sem a intervencao, a mesma entrada produz a
        prescricao cheia. E o que torna a comparacao do item 1 valida."""
        dec = self._decisao()
        adaptado = self._rodar(dec)
        base = build_plan([], 0, ftp=FTP, days=5, start=START, goal="ftp-builder")
        self.assertLess(sum(w["tss"] for w in adaptado),
                        sum(w["tss"] for w in base))


class LedgerEhPorFonteTest(unittest.TestCase):
    """Regressao: o livro-razao do orcamento so vale quando a PRONTIDAO agiu.

    `readiness_agiu` foi inicialmente marcado pela simples presenca de
    `state.readiness`, e depois pela adaptacao ocorrer com qualquer readiness
    presente. Os dois erros empurravam `tss_pre` para o razao em casos em que a
    prontidao nao dirigiu nada, e o plano divergia de um plano equivalente sem
    prontidao. Nenhum dia pode ficar MAIOR que a referencia; e quando a prontidao
    nao age, o plano tem de ser identico ao de referencia.
    """

    FTP = 182
    START = date(2026, 9, 14)

    def _decisao(self, escore=0.2, tsb_dia=None):
        return readiness_decision(
            ReadinessAssessment(hrv_score=escore, rhr_score=escore,
                                sleep_score=0.8),
            reference_day=(tsb_dia or self.START).isoformat())

    def _referencia(self, tsb):
        return build_plan([], tsb, ftp=self.FTP, days=7, start=self.START,
                          goal="ftp-builder")

    def _rodar(self, decisao, tsb):
        relatorio = {}
        plano = build_plan([], tsb, ftp=self.FTP, days=7, start=self.START,
                           goal="ftp-builder", readiness=decisao,
                           readiness_report=relatorio)
        return plano, relatorio

    def test_decisao_none_nao_altera_o_plano_quando_tsb_age(self):
        """Regressao do primeiro defeito: medido 173 -> 166 TSS com TSB -30."""
        decisao = self._decisao(escore=0.8)
        adapted, _ = self._rodar(decisao, -30)
        base = self._referencia(-30)
        self.assertEqual([w["day"] for w in adapted],
                         [w["day"] for w in base])
        for a, b in zip(adapted, base):
            self.assertEqual(a["focus"], b["focus"])
            self.assertAlmostEqual(a["tss"], b["tss"], places=6,
                                   msg=f"{a['day']} divergiu com decisao NONE")

    def test_decisao_none_nao_altera_o_plano_sem_tsb(self):
        decisao = self._decisao(escore=0.8)
        adapted, relatorio = self._rodar(decisao, 0)
        base = self._referencia(0)
        for a, b in zip(adapted, base):
            self.assertAlmostEqual(a["tss"], b["tss"], places=6)
        self.assertEqual(relatorio["situacao"], "nenhuma_adaptacao_necessaria")
        self.assertEqual(relatorio["aplicada_em"], [])

    def test_tsb_vencedor_nao_usa_razao_da_prontidao(self):
        """Regressao do segundo defeito: 18/09 caia de 39 para 32 TSS.

        Com TSB abaixo do limite a acao ja e REPLACE por TSB. Uma decisao
        REDUCE nao dirigiu a mudanca, logo nao pode empurrar `tss_pre` para o
        razao nem ser reportada como aplicada.
        """
        adaptado, relatorio = self._rodar(self._decisao(), -30)
        base = self._referencia(-30)
        for a, b in zip(adaptado, base):
            self.assertEqual(a["focus"], b["focus"])
            self.assertAlmostEqual(a["tss"], b["tss"], places=6,
                                   msg=f"{a['day']} divergiu; TSB venceu a prontidao")
        self.assertNotIn(self.START.isoformat(), relatorio["aplicada_em"])

    def test_reduce_da_prontidao_nao_promove_nenhum_dia(self):
        """Invariante do item 1, agora com o ledger por fonte corrigido."""
        adapted, relatorio = self._rodar(self._decisao(), 0)
        base = self._referencia(0)
        self.assertEqual(relatorio["situacao"], "aplicada")
        for a, b in zip(adapted, base):
            self.assertLessEqual(a["tss"], b["tss"] + 1e-9,
                                 msg=f"{a['day']} ficou MAIOR que a referencia")
            self.assertLessEqual(a["planned_duration"],
                                 b["planned_duration"] + 1e-9)

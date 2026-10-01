"""Estimativa de FTP a partir de pedal fora do plano.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §9. O que estas travas defendem:

* FTP aqui é **referência operacional de potência**, não MLSS, LT, RCP nem
  Critical Power. A conversão `best20 x 0,95` é a convenção clássica do teste
  de 20 min, não uma equivalência fisiológica.
* O módulo é **puro e determinístico**: mesmo stream, mesmo resultado; nada de
  data corrente ou rede. Um FTP que muda sozinho a cada chamada não pode
  entrar em `plan.json`.
* O gate de contexto é **unidirecional**: só propõe para cima, e só entre
  +3% e +30%. Esforço abaixo do FTP atual é fadiga, não FTP menor.
* A limpeza de picos é **conservadora**: clipa em vez de remover, e só pode
  subestimar. Um pico espúrio inflado jamais pode virar sugestão de FTP.
* FTP zero/vazio não produz divisão por zero nem sugestão.

Nota: `pstdev` é o desvio populacional. Para um esforço de 1200 amostras a
diferença para o amostral é ~0,04% no CV, muito abaixo do gate de 15%; usar o
amostral aqui mudaria a fronteira do gate sem motivo.
"""
import math
import unittest

from src.ftp_estimation import (BEST_WINDOW_SEC, FTP_FACTOR, MAX_CV,
                               MAX_NEW_FTP_RATIO, MIN_NEW_FTP_RATIO,
                               MIN_WINDOW_RATIO, analyze_ride, best_effort,
                               clean_power, ftp_from_best20)

JANELA = 1200


def pedal(watts, total=JANELA + 120):
    """Stream uniforme e a copia dele, para checar que o modulo nao muta."""
    stream = [watts] * total
    return stream, list(stream)


def suave(base=280, amplitude=20, total=JANELA + 120):
    """Stream limpo com variação senoidal: CV baixo e sem apagões."""
    return [base + round(amplitude * math.sin(i / 30)) for i in range(total)]


class LimpezaDePicosTest(unittest.TestCase):
    def test_pico_espurio_e_clipado_e_nao_removido(self):
        dados = [250.0] * 60
        dados[30] = 4000.0
        limpa, removidos = clean_power(dados)
        self.assertEqual(removidos, 1)
        self.assertEqual(len(limpa), len(dados))
        self.assertLess(limpa[30], 4000.0)
        # O clip fica bem acima do effort normal e bem abaixo do pico: o valor
        # e limitado, nao apagado.
        self.assertGreater(limpa[30], 250.0)

    def test_o_limite_de_clip_e_a_mediana_vez_spike_factor(self):
        dados = [250.0] * 60
        dados[30] = 4000.0
        limpa, _ = clean_power(dados, spike_factor=2.5)
        self.assertAlmostEqual(limpa[30], 250.0 * 2.5)

    def test_clip_sempre_subestima(self):
        # O efeito no best-20min e para baixo: um pico removido nunca levanta a
        # estimativa, entao o outlier inflado nao pode virar FTP maior.
        dados = [250.0] * (JANELA + 60)
        dados[10] = 9000.0
        limpa, _ = clean_power(dados)
        self.assertLessEqual(max(limpa), 250.0 * 2.5)

    def test_valor_nao_finito_vira_zero_e_e_contado(self):
        limpa, removidos = clean_power([250.0, float("nan"), float("inf")])
        self.assertEqual(removidos, 2)
        self.assertEqual(limpa[1], 0.0)
        self.assertEqual(limpa[2], 0.0)

    def test_valor_nao_numerico_vira_zero(self):
        limpa, removidos = clean_power([250.0, None, "erro"])
        self.assertEqual(removidos, 2)
        self.assertEqual(limpa[1:], [0.0, 0.0])

    def test_anomalia_declarada_da_plataforma_e_respeitada(self):
        # O flag da plataforma tem precedencia sobre o limiar automatico.
        dados = [250.0] * 60
        dados[30] = 300.0
        anomalias = [False] * 60
        anomalias[30] = True
        limpa, removidos = clean_power(dados, anomalies=anomalias)
        self.assertEqual(removidos, 1)
        self.assertAlmostEqual(limpa[30], 625.0)

    def test_stream_sem_valores_finitos_nao_explode(self):
        # Mediana 0 ou lista vazia: o modulo nao pode levantar excecao, e sim
        # devolver o stream intacto para o chamador tratar.
        self.assertEqual(clean_power([]), ([], 0))
        self.assertEqual(clean_power([0, 0, 0]), ([0, 0, 0], 0))
        self.assertEqual(clean_power([None, "x"]), ([None, "x"], 0))

    def test_a_entrada_nao_e_mutada(self):
        dados = [250.0] * 10
        copia = list(dados)
        clean_power(dados)
        self.assertEqual(dados, copia)


class MelhorMediaMovelTest(unittest.TestCase):
    def test_encontra_a_janela_de_maior_media(self):
        dados = [200.0] * 100 + [300.0] * 30
        media, inicio, fim = best_effort(dados, 30)
        self.assertAlmostEqual(media, 300.0)
        self.assertEqual((inicio, fim), (100, 130))

    def test_stream_curto_devolve_none(self):
        # Sem janela completa nao ha estimativa, e o chamador reduz a um motivo.
        self.assertEqual(best_effort([250.0] * 10, JANELA), (None, 0, 0))
        self.assertEqual(best_effort([], JANELA), (None, 0, 0))

    def test_janela_igual_ao_stream_usa_o_stream_inteiro(self):
        media, inicio, fim = best_effort([250.0] * 30, 30)
        self.assertAlmostEqual(media, 250.0)
        self.assertEqual((inicio, fim), (0, 30))

    def test_a_janela_precisa_caber_no_stream(self):
        # `>` estrito: janela do mesmo tamanho do stream e valida.
        self.assertIsNotNone(best_effort([250.0] * 30, 30)[0])
        self.assertIsNone(best_effort([250.0] * 29, 30)[0])

    def test_amostragem_altera_a_contagem_da_janela(self):
        # sample_sec=5 significa um ponto a cada 5 s, entao 1200 s de janela
        # viram 240 amostras, nao 1200.
        media, _, _ = best_effort([250.0] * 240, 1200, sample_sec=5.0)
        self.assertAlmostEqual(media, 250.0)
        self.assertIsNone(best_effort([250.0] * 239, 1200, sample_sec=5.0)[0])

    def test_media_igual_em_duas_janelas_ficca_com_a_primeira(self):
        # Empate nao vira "melhor": o loop usa `>` e preserva o inicio mais
        # cedo, o que torna a estimativa estavel entre execucoes.
        media, inicio, _ = best_effort([300.0] * 30 + [200.0] * 30, 30)
        self.assertAlmostEqual(media, 300.0)
        self.assertEqual(inicio, 0)


class ConversaoParaFtpTest(unittest.TestCase):
    def test_conversao_usando_o_fator_declarado(self):
        self.assertEqual(ftp_from_best20(300), int(round(300 * FTP_FACTOR)))
        self.assertEqual(ftp_from_best20(300), 285)

    def test_o_resultado_e_inteiro(self):
        # FTP e persistido em watts inteiros; float aqui vazaria para o plano.
        self.assertIsInstance(ftp_from_best20(301.7), int)

    def test_a_conversao_nunca_excede_o_best20(self):
        # Fator 0,95 < 1: o FTP proposto e sempre menor que a potencia da
        # janela, o que mantem o numero abaixo do esforco que o produziu.
        for best in range(150, 500, 7):
            self.assertLessEqual(ftp_from_best20(best), best)


class GateDeQualidadeTest(unittest.TestCase):
    def setUp(self):
        self.ftp = 250

    def test_esforco_limpo_dentro_da_faixa_sugere_novo_ftp(self):
        # Contra 250 W de FTP atual, o pedal precisa subir o suficiente para o
        # proporcional cair na faixa +3%..+30%. 300 W (+20%) entra; 270 W (+8%)
        # arredonda para 257 W e nao chega ao piso, como o teste vizinho fixa.
        estimativa = analyze_ride(suave(base=300), self.ftp)
        self.assertTrue(estimativa.quality_ok)
        self.assertTrue(estimativa.suggests_new)
        self.assertGreaterEqual(estimativa.diff_ratio, MIN_NEW_FTP_RATIO)
        self.assertLessEqual(estimativa.diff_ratio, MAX_NEW_FTP_RATIO)

    def test_esforco_dentro_do_ruido_nao_sugere_novidade(self):
        # 270 W contra 250 W de FTP: +8% no pedal, mas o best-20min arredonda
        # para 257 W (+2,8%), abaixo do piso de +3%. A margem e pequena de
        # proposito: e o arredondamento que decide, nao o %.
        estimativa = analyze_ride(suave(base=270), self.ftp)
        self.assertLess(estimativa.diff_ratio, MIN_NEW_FTP_RATIO)
        estimativa = analyze_ride(suave(base=250), self.ftp)
        self.assertTrue(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertIn("sem novidade", estimativa.reason)

    def test_aumento_peligoso_e_bloqueado_como_anomalia(self):
        # +50% passa na qualidade mas viola o teto anti-anomalia.
        estimativa = analyze_ride(suave(base=400), self.ftp)
        self.assertTrue(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertIn("anomalia", estimativa.reason)

    def test_esforco_abaixo_do_ftp_nunca_propoe_reducao(self):
        # A regra e unidirecional: um pedal fraco nao é evidencia de FTP menor.
        estimativa = analyze_ride(suave(base=200), self.ftp)
        self.assertTrue(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertLess(estimativa.diff_ratio, 1.0)
        self.assertIn("sem novidade", estimativa.reason)

    def test_puncheiro_e_reprovado_no_cv(self):
        # CV alto e o padrao de quem quebra o pedal: sem gate de CV, a media da
        # janela seria lida como FTP.
        dados = [500.0 if i % 2 else 100.0 for i in range(JANELA + 60)]
        estimativa = analyze_ride(dados, self.ftp)
        self.assertFalse(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertGreater(estimativa.cv, MAX_CV)
        self.assertIn("variabilidade", estimativa.reason)

    def test_apagao_dentro_da_janela_e_reprovado(self):
        # min/mediana < 0,80: o atleta nao sustentou a janela toda.
        dados = suave(base=270)
        dados[600] = 40.0
        estimativa = analyze_ride(dados, self.ftp)
        self.assertFalse(estimativa.quality_ok)
        self.assertIn("apag", estimativa.reason)
        self.assertLess(estimativa.min_ratio, MIN_WINDOW_RATIO)

    def test_apagoes_queimados_por_picos_sao_gerados_antes_do_cv(self):
        # A limpeza roda antes do best-20min: um pico nao pode ser lido como
        # "esforco variavel" quando e spike de sensor.
        dados = suave(base=270)
        dados[600] = 40.0
        dados[610] = 4000.0
        estimativa = analyze_ride(dados, self.ftp)
        self.assertGreater(estimativa.cleaned_outliers, 0)
        self.assertFalse(estimativa.suggests_new)

    def test_qualidade_ruim_manda_o_motivo_do_limiar_de_contexto(self):
        # Quando a qualidade falha, o motivo cita a qualidade e nao "novidade":
        # sugerir mudanca de FTP sobre esforco naoustainable seria o erro caro.
        estimativa = analyze_ride([500.0 if i % 2 else 100.0
                                   for i in range(JANELA + 60)], self.ftp)
        self.assertIn("nao sustenta estimativa", estimativa.reason)
        self.assertNotIn("sem novidade", estimativa.reason)


class EntradasDegeneradasTest(unittest.TestCase):
    def test_stream_vazio_nao_propoe_ftp(self):
        estimativa = analyze_ride([], 250)
        self.assertFalse(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertEqual(estimativa.proposed_ftp, 0)
        self.assertIn("sem dados", estimativa.reason)

    def test_stream_curto_para_a_janela_nao_propoe_ftp(self):
        estimativa = analyze_ride([250.0] * 60, 250)
        self.assertFalse(estimativa.quality_ok)
        self.assertFalse(estimativa.suggests_new)
        self.assertIn("stream curto", estimativa.reason)
        self.assertIn("20", estimativa.reason)

    def test_ftp_atual_zero_nao_divide_por_zero(self):
        # Sem FTP de referencia o ratio vai a infinito e nada e sugerido: nao ha
        # denominador contra o qual julgar novidade.
        estimativa = analyze_ride(suave(base=280), 0)
        self.assertEqual(estimativa.diff_ratio, math.inf)
        self.assertFalse(estimativa.suggests_new)

    def test_ftp_atual_negativo_nao_propoe_ftp_maior(self):
        estimativa = analyze_ride(suave(base=280), -250)
        self.assertFalse(estimativa.suggests_new)

    def test_media_zero_nao_produz_nan(self):
        # Stream de zeros: media 0, CV e min_ratio nao podem virar NaN e fazer
        # a comparacao do gate falhar silenciosamente.
        estimativa = analyze_ride([0.0] * (JANELA + 60), 250)
        self.assertFalse(math.isnan(estimativa.cv))
        self.assertFalse(math.isnan(estimativa.min_ratio))
        self.assertFalse(estimativa.suggests_new)

    def test_janela_customizada_muda_o_motivo_do_stream_curto(self):
        estimativa = analyze_ride([250.0] * 100, 250, window_sec=600)
        self.assertFalse(estimativa.suggests_new)
        self.assertIn("10", estimativa.reason)


class DeterminismoTest(unittest.TestCase):
    def test_o_mesmo_stream_devolve_o_mesmo_resultado(self):
        dados = suave(base=272)
        primeiro = analyze_ride(list(dados), 250)
        segundo = analyze_ride(list(dados), 250)
        self.assertEqual(primeiro, segundo)

    def test_repetir_o_analise_nao_amplifica_a_estimativa(self):
        # Se `analyze_ride` limpasse a lista recebida in-place, a segunda
        # chamada veria um stream diferente e o FTP driftaria a cada rodada.
        dados, segundos = pedal(280)
        primeira = analyze_ride(dados, 250)
        segunda = analyze_ride(dados, 250)
        self.assertEqual(primeira.proposed_ftp, segunda.proposed_ftp)
        self.assertEqual(primeira.best_effort_avg, segunda.best_effort_avg)
        self.assertEqual(primeira.cleaned_outliers, segunda.cleaned_outliers)
        self.assertEqual(segundos, [280.0] * (JANELA + 120))

    def test_a_janela_vencedora_e_reportada(self):
        # Os indices da janela sao o que permite auditar a estimativa contra o
        # stream original depois de publicado o plano.
        estimativa = analyze_ride(suave(base=272), 250)
        self.assertEqual(estimativa.best_end_index - estimativa.best_start_index,
                         JANELA)
        self.assertGreaterEqual(estimativa.best_start_index, 0)


if __name__ == "__main__":
    unittest.main()

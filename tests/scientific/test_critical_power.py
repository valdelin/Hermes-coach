"""Critical Power e W' como métrica complementar, nunca equivalente ao FTP.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §10. O que estas travas defendem:

* CP e W' **não** são FTP, MLSS, LT ou RCP, e não substituem o FTP
  automaticamente. CP é assíntoto do modelo de Potência-Critica; o FTP é uma
  referência operacional de potência derivada de outra fonte.
* A regressão é `P = CP + W'/t` sobre `1/t`. Portanto **CP é o intercepto** e
  **W' é o coeficiente angular em joules** (W·s), não em watts. Trocar os dois
  inverteria a leitura do perfil.
* Dados insuficientes devolvem `None`, nunca um chute: 1 ponto, durações
  inválidas ou degeneração numérica não geram número.
* O trabalho acima de CP é **limitado pelo W' disponível**: um repeat infinito
  não rende trabalho infinito, que é o sentido físico do modelo.
* O déficit de W' não fica negativo: consumer mais do que se tem deixa zero,
  não saldo devedor.

Nota de modelagem: o intercepto é recusado quando `<= 0`. Isso é proteção contra
degeneração numérica (powers vs durações invertidas, por exemplo), e não uma
afirmação fisiológica de que CP positivo é lei.
"""
import dataclasses
import unittest

from src.critical_power import (CPConfidence, CPProtocol, CriticalPowerProfile,
                                estimate_cp, estimate_w_prime,
                                w_prime_balance, w_prime_reconstitution,
                                work_above_cp)

# Pontos exatamente sobre P = CP + W'/t com CP = 250 W e W' = 300 J. Sao usados
# valores exatos, e nao potencias "redondas", porque o ajuste e uma reta em
# 1/t: um ponto fora da reta desloca o intercepto. Este conjunto recupera
# 250,0 e 300,0 sem tolerancia.
PONTOS_CP = tuple((t, 250 + 300 / t) for t in (120, 300, 1200))
PERFIL = CriticalPowerProfile(critical_power=250, w_prime=300,
                               protocol=CPProtocol.STEP,
                               confidence=CPConfidence.MEDIUM,
                               test_dates=("2026-09-01",))


class RegressaoTest(unittest.TestCase):
    def setUp(self):
        self.cp = estimate_cp(PONTOS_CP)
        self.wp = estimate_w_prime(PONTOS_CP)

    def test_cp_e_o_intercepto_da_regressao(self):
        # Em P = CP + W'/t, t -> infinito faz W'/t -> 0, entao P -> CP: CP e o
        # assintoto horizontal do modelo, e nao a media das potencias.
        self.assertAlmostEqual(self.cp, 250.0)

    def test_w_prime_e_o_coeficiente_angular_em_joules(self):
        # W' tem unidade de joule (W*s). A regressao entrega W' direto, porque
        # P esta em watts e 1/t em 1/s. Inverter os dois daria CP em joules.
        self.assertAlmostEqual(self.wp, 300.0)

    def test_potencia_extrapolada_para_o_assintoto_da_cp(self):
        # O modelo precisa reconstruir a potencia em qualquer duracao, nao so
        # nos pontos observados. Esta e a checagem de que intercepto e
        # coeficiente foram lidos na ordem certa.
        for duracao in (30, 600, 3600):
            reconstruida = self.cp + self.wp / duracao
            self.assertAlmostEqual(reconstruida, 250 + 300 / duracao,
                                   msg=duracao)

    def test_cp_ficabaixo_de_toda_a_potencia_do_esforco(self):
        # O assintoto tem de ser menor que a potencia medida em qualquer
        # duracao finita; se nao, os pontos nao descrevem Potencia-Critica.
        for duracao, potencia in PONTOS_CP:
            self.assertLess(self.cp, potencia, duracao)

    def test_um_esforco_muito_curto_ou_muito_longo_muda_cp(self):
        """O peso do estimador é desigual, e isso é uma limitação conhecida.

        Em P contra 1/t, o ponto de 120 s tem 1/t dez vezes maior que o de
        1200 s, e por isso pesa dez vezes mais no ajuste. Um esforço longo é
        quase a mesma observação do assíntoto e quase não o determina. Registrar
        aqui para que a confiança do CP não seja lida como se todos os pontos
        pesassem igual.
        """
        # Um ponto muito longo **acima** da reta puxa CP para cima, ainda que
        # 1200 s seja quase o próprio assíntoto.
        puxa_cima = PONTOS_CP + ((7200, 260.0),)
        self.assertGreater(estimate_cp(puxa_cima), self.cp)
        # O mesmo ponto abaixo da reta puxa para baixo. O sentido do efeito é
        # determinístico; o tamanho é o que não é uniforme.
        puxa_baixo = PONTOS_CP + ((7200, 240.0),)
        self.assertLess(estimate_cp(puxa_baixo), self.cp)

    def test_mais_pontos_aproximam_o_verdadeiro(self):
        # Com 5 pontos coerentes o erro cai; o modelo converge para CP = 250.
        pontos = tuple((t, 250 + 300 / t) for t in (60, 120, 300, 600, 1200))
        self.assertAlmostEqual(estimate_cp(pontos), 250.0)
        self.assertAlmostEqual(estimate_w_prime(pontos), 300.0)

    def test_ruido_no_esforco_desvia_a_estimativa(self):
        """Limitação do método, registrada como tal.

        O ajuste e OLS de P contra 1/t. Essa transformacao **enviesa** o
        intercepto: um esforco com ruido move CP, e um esforco muito curto tem
        mais peso que um longo. Nao ha ponderacao por duracao nem filtro de
        outlier. O numero e honesto apenas dentro da faixa de duracoes
        realmente medida; extrapolar para o assintoto com 3 pontos ruidosos e
        chute. Nao corrigido aqui porque muda o estimador, fora do escopo do
        P3-01.
        """
        ruidoso = ((120, 251.0), (300, 262.0), (1200, 240.0))
        self.assertNotAlmostEqual(estimate_cp(ruidoso), 250.0, delta=2.0)
        # Um único ponto ruidoso entre pontos perfeitos já desloca a leitura.
        com_um_ruido = PONTOS_CP + ((300, 300.0),)
        self.assertNotAlmostEqual(estimate_cp(com_um_ruido), 250.0, delta=1.0)


class DadosInsuficientesTest(unittest.TestCase):
    def test_vazio_devolve_none(self):
        self.assertIsNone(estimate_cp(()))
        self.assertIsNone(estimate_w_prime(()))

    def test_ponto_unico_devolve_none(self):
        # Uma unica medida nao define reta: sem isso viraria chute de CP.
        self.assertIsNone(estimate_cp(((300, 300.0),)))
        self.assertIsNone(estimate_w_prime(((300, 300.0),)))

    def test_duracao_zero_ou_negativa_e_descartada(self):
        # `t > 0` no filtro: 1/t indefinido, entao o ponto sai do ajuste.
        pontos = ((0, 300.0), (300, 300.0))
        self.assertIsNone(estimate_cp(pontos))
        self.assertIsNone(estimate_cp(((-300, 300.0),)))

    def test_apenas_um_ponto_valido_apos_filtrar_devolve_none(self):
        # Se so sobra um ponto valido, o ajuste nao existe.
        self.assertIsNone(estimate_cp(((0, 300.0), (-1, 300.0), (300, 300.0))))

    def test_duracoes_iguais_degeneram_para_none(self):
        # Mesma duracao, potencias diferentes: 1/t identico, denominador zero.
        self.assertIsNone(estimate_cp(((300, 250.0), (300, 300.0))))
        self.assertIsNone(estimate_w_prime(((300, 250.0), (300, 300.0))))

    def test_intercepto_nao_positivo_e_recusado(self):
        # Potencia subindo com a duracao inverte a inclinacao. O intercepto sai
        # negativo e o modulo recusa em vez de devolver CP negativo.
        degenerado = ((60, 300.0), (300, 10.0))
        self.assertIsNone(estimate_cp(degenerado))
        self.assertIsNone(estimate_w_prime(degenerado))

    def test_nenhum_valor_de_cp_negativo_e_publicado(self):
        # Varredura: com potencias invertidas o ajuste recusa. O que nao pode
        # acontecer e CP < 0, que nao tem leitura fisica.
        for curta in (60, 120, 300):
            for longa in (600, 1200, 2400):
                for pc, pl in ((300.0, 10.0), (100.0, 10.0), (600.0, 50.0)):
                    cp = estimate_cp(((curta, pc), (longa, pl)))
                    if cp is not None:
                        self.assertGreater(cp, 0, (curta, pc, longa, pl))


class TrabalhoAcimaDeCpTest(unittest.TestCase):
    def test_trabalho_acima_de_cp_usa_o_excesso_pela_duracao(self):
        # 50 W acima de CP por 300 s = 15.000 J. Com estoque de 100 kJ o
        # modelo entrega o produto linear; com estoque de 300 J entrega o
        # limite, como o teste seguinte fixa.
        self.assertAlmostEqual(work_above_cp(300, 300, 250, 100_000),
                               50.0 * 300)

    def test_o_trabalho_satura_no_w_prime(self):
        # O teto e o sentido do modelo: repetir acima de CP nao gera trabalho
        # infinito porque o W' e um estoque finito.
        self.assertEqual(work_above_cp(3600, 400, 250, 300), 300.0)

    def test_potencia_igual_ao_cp_nao_gera_trabalho_acima(self):
        self.assertEqual(work_above_cp(600, 250, 250, 300), 0.0)

    def test_potencia_abaixo_do_cp_gera_zero_e_nao_credito(self):
        # Nao existe "trabalho negativo acima de CP": devolver valor negativo
        # viraria saldo de W' a favor.
        self.assertEqual(work_above_cp(600, 200, 250, 300), 0.0)

    def test_duracao_nao_positiva_gera_zero(self):
        self.assertEqual(work_above_cp(0, 400, 250, 300), 0.0)
        self.assertEqual(work_above_cp(-60, 400, 250, 300), 0.0)

    def test_cp_ou_w_prime_ausente_gera_zero(self):
        # Perfil incompleto nao pode "adivinhar" o trabalho acima de CP.
        self.assertEqual(work_above_cp(600, 400, 0, 300), 0.0)
        self.assertEqual(work_above_cp(600, 400, 250, 0), 0.0)
        self.assertEqual(work_above_cp(600, 400, None, 300), 0.0)

    def test_esforco_acima_do_cp_e_limitado_mesmo_com_w_prime_grande(self):
        # 20 min a 50 W acima de CP, com estoque de 25 kJ: consome 25 kJ, e o
        # limite e o estoque, nao a duracao.
        self.assertEqual(work_above_cp(1200, 300, 250, 25_000), 25_000.0)


class SaldoDeWprimeTest(unittest.TestCase):
    def test_saldo_e_o_estoque_menos_o_consumido(self):
        self.assertAlmostEqual(w_prime_balance(PERFIL, 100), 200.0)

    def test_saldo_nao_fica_negativo(self):
        # Gastar mais do que o estoque zera o saldo; um valor negativo viraria
        # "divida" de W' que o modelo nao tem.
        self.assertEqual(w_prime_balance(PERFIL, 500), 0.0)

    def test_saldo_exatamente_no_estoque_zera(self):
        self.assertEqual(w_prime_balance(PERFIL, 300), 0.0)

    def test_perfil_sem_w_prime_devolve_none(self):
        # Sem W' conhecido, o saldo e desconhecido, nao zero.
        perfil = CriticalPowerProfile(critical_power=250)
        self.assertIsNone(w_prime_balance(perfil, 100))
        self.assertIsNone(w_prime_balance(CriticalPowerProfile(), 0))

    def test_saldo_preserva_a_imutabilidade_do_perfil(self):
        # `w_prime_balance` nao altera o perfil: o saldo e leitura, nao estado.
        antes = PERFIL.w_prime
        w_prime_balance(PERFIL, 250)
        self.assertEqual(PERFIL.w_prime, antes)


class ReconstituicaoTest(unittest.TestCase):
    def test_reduz_o_deficito_no_ritmo_configurado(self):
        # 0,1 W/s (≈6 W por minuto) e heurística do sistema, marcada no módulo.
        self.assertAlmostEqual(w_prime_reconstitution(300, 1000), 200.0)

    def test_deficit_totalmente_recuperado_zera(self):
        # Tempo suficiente consome o deficit inteiro e para em zero.
        self.assertEqual(w_prime_reconstitution(300, 3000), 0.0)

    def test_deficit_nao_recuperado_mantem_o_restante(self):
        # 1000 s a 0,1 W/s = 100 J: sobram 200 J de deficit.
        self.assertAlmostEqual(w_prime_reconstitution(300, 1000), 200.0)
        self.assertGreater(w_prime_reconstitution(300, 100), 0)

    def test_deficit_negativo_ou_tempo_nao_positivo_gera_zero(self):
        # Sem deficit, nada a reconstituir; tempo invalido nao "acelera" a
        # recuperacao alem do zero.
        self.assertEqual(w_prime_reconstitution(0, 1000), 0.0)
        self.assertEqual(w_prime_reconstitution(-100, 1000), 0.0)
        self.assertEqual(w_prime_reconstitution(300, 0), 0.0)
        self.assertEqual(w_prime_reconstitution(300, -500), 0.0)

    def test_ritmo_maior_recupera_mais_rapido(self):
        lento = w_prime_reconstitution(300, 1000, rate=0.05)
        rapido = w_prime_reconstitution(300, 1000, rate=0.2)
        self.assertLess(rapido, lento)
        self.assertGreaterEqual(rapido, 0.0)


class PerfilTest(unittest.TestCase):
    def test_known_exige_cp_e_w_prime(self):
        # `known` e conjunction, nao presenca de um dos dois: perfil com so CP
        # nao descreve o modelo de Potencia-Critica por completo.
        self.assertTrue(PERFIL.known)
        self.assertFalse(CriticalPowerProfile(critical_power=250).known)
        self.assertFalse(CriticalPowerProfile(w_prime=300).known)
        self.assertFalse(CriticalPowerProfile().known)

    def test_perfil_e_imutavel(self):
        # Frozen: o perfil de CP entra no `plan.json` e nao pode ser reescrito
        # por um modulo consumidor depois de construido.
        with self.assertRaises(dataclasses.FrozenInstanceError):
            PERFIL.critical_power = 999

    def test_test_dates_tem_padrao_vazio_e_nao_e_compartilhado(self):
        # `field(default_factory=tuple)`: default mutavel compartilhado entre
        # instancias seria contaminacao de estado entre atletas.
        a = CriticalPowerProfile()
        b = CriticalPowerProfile()
        self.assertEqual(a.test_dates, ())
        self.assertEqual(a, b)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            a.test_dates = ("2026-01-01",)

    def test_protocolos_e_confiancas_sao_enumerados_fechados(self):
        # Protocolo e um vocabulario fechado: um valor novo exigiria revisar a
        # inferencia, nao passar texto livre.
        self.assertEqual({p.value for p in CPProtocol},
                         {"ramp", "step", "multi_broken", "field_estimate"})
        self.assertEqual({c.value for c in CPConfidence},
                         {"low", "medium", "high"})


if __name__ == "__main__":
    unittest.main()

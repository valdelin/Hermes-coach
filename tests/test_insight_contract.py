import unittest

from src.insight import contract
from src.insight.contract import InsightContext


def _payload(**over):
    base = {
        "foco": "z2",
        "duracao_min": 45,
        "intensidade": "casual",
        "acao": "Hoje e recuperacao: 45 min bem leve.",
        "alerta": None,
    }
    base.update(over)
    return base


def _ctx(**over):
    base = {
        "foco_motor": "z2",
        "tl_duracao_min": 45,
        "tsb": -5.0,
        "ctl": 25.3,
        "atl": 40.8,
        "raw": "foco z2, 45 min, TSB -5.0, CTL 25.3, ATL 40.8",
    }
    base.update(over)
    return InsightContext(**base)


class ContractTest(unittest.TestCase):
    """Exit do M1: o contrato e valido offline, sem chave de API."""

    def test_payload_completo_passa(self):
        self.assertEqual(contract.contract_errors(_payload()), [])

    def test_campo_obrigatorio_ausente(self):
        p = _payload()
        del p["alerta"]
        self.assertTrue(any("alerta" in e for e in contract.contract_errors(p)))

    def test_campo_fora_do_contrato(self):
        erros = contract.contract_errors(_payload(motivo="porque"))
        self.assertTrue(any("fora do contrato" in e for e in erros))

    def test_foco_fora_do_enum(self):
        erros = contract.contract_errors(_payload(foco="intervalos"))
        self.assertTrue(any("foco invalido" in e for e in erros))

    def test_duracao_fora_dos_limites(self):
        self.assertTrue(contract.contract_errors(_payload(duracao_min=900)))
        self.assertTrue(contract.contract_errors(_payload(duracao_min=-10)))

    def test_booleano_nao_passa_como_inteiro(self):
        # bool e subclasse de int em Python: True nao pode virar duracao_min.
        self.assertTrue(contract.contract_errors(_payload(duracao_min=True)))

    def test_acao_vazia(self):
        self.assertTrue(contract.contract_errors(_payload(acao="")))

    def test_payload_nao_objeto(self):
        self.assertEqual(contract.contract_errors(["z2"]), ["payload nao e objeto"])

    def test_alerta_aceita_string_ou_null(self):
        self.assertEqual(contract.contract_errors(_payload(alerta="TSB -21.8")), [])
        self.assertEqual(contract.contract_errors(_payload(alerta=None)), [])

    def test_dumps_ordenado_e_estavel(self):
        a = contract.dumps({"alerta": None, "foco": "z2"})
        b = contract.dumps({"foco": "z2", "alerta": None})
        self.assertEqual(a, b)


class RegistryTest(unittest.TestCase):
    def test_registro_traz_versao_e_hash(self):
        entrada = contract.registry_entry(model="claude-test")
        self.assertEqual(entrada["prompt_version"], contract.PROMPT_VERSION)
        self.assertEqual(entrada["model"], "claude-test")
        self.assertIsNotNone(entrada["prompt_hash"])
        self.assertEqual(len(entrada["prompt_hash"]), 12)

    def test_hash_muda_quando_o_prompt_muda(self):
        original = contract.PROMPT_PATH.read_bytes()
        antes = contract.prompt_hash()
        try:
            contract.PROMPT_PATH.write_bytes(original + b"\n<!-- x -->")
            self.assertNotEqual(antes, contract.prompt_hash())
        finally:
            contract.PROMPT_PATH.write_bytes(original)
        self.assertEqual(antes, contract.prompt_hash())

    def test_hash_estavel_entre_chamadas(self):
        self.assertEqual(contract.prompt_hash(), contract.prompt_hash())


class ContextTest(unittest.TestCase):
    def test_prompt_data_arredonda(self):
        dados = _ctx().as_prompt_data()
        self.assertEqual(dados["tsb"], -5.0)
        self.assertEqual(dados["foco_do_motor"], "z2")
        self.assertNotIn("raw", dados)

    def test_contexto_nao_expoe_raw_no_prompt_data(self):
        # `raw` existe so para os graders lerem os numeros; nao vai ao prompt.
        self.assertNotIn("raw", _ctx().as_prompt_data())


if __name__ == "__main__":
    unittest.main()

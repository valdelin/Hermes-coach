"""Contrato de referências científicas do embasamento.

Este arquivo é a camada offline do CI: não faz rede. Ele garante que o
documento tem uma lista numerada completa, que toda citação resolve para uma
entrada, que nenhuma entrada é órfã e que a matriz de rastreabilidade declara
explicitamente o que cada fonte não mostra. A resolução de PMID/DOI contra
NCBI/Crossref é feita por ``scripts/check_references.py`` no workflow
``references``.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_references.py"
SPEC = importlib.util.spec_from_file_location("check_references", SCRIPT)
check = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check
SPEC.loader.exec_module(check)

DOC = Path(__file__).resolve().parent.parent / "docs" / "EMBASAMENTO-CIENTIFICO.md"

FEATURES_OBRIGATORIAS = (
    "FTP canônico",
    "FTP vs marcadores",
    "CP e W′",
    "Zonas",
    "Periodização",
    "Distribuição de intensidade",
    "Training Load",
    "CTL, ATL, TSB",
    "Readiness",
    "Adaptation State",
    "Progression Engine",
    "VO2max",
    "Recovery / Deload",
    "Inatividade e reteste",
)


class ScientificReferencesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DOC.read_text(encoding="utf-8")
        cls.body, cls.refs_text, cls.references = check.parse_references(cls.text)

    def test_parser_encontra_todas_as_entradas_em_sequencia(self):
        numbers = [ref.number for ref in self.references]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertGreaterEqual(len(self.references), 45)

    def test_toda_entrada_tem_autor_ano_e_titulo(self):
        for ref in self.references:
            with self.subTest(referencia=ref.number):
                self.assertTrue(ref.author.strip())
                self.assertTrue(ref.title.strip())
                self.assertGreaterEqual(len(ref.title), 8)
                self.assertGreaterEqual(ref.year, 1900)
                self.assertLessEqual(ref.year, 2100)

    def test_pmid_e_unico_bem_formado_e_dentro_do_limite(self):
        seen = {}
        for ref in self.references:
            if not ref.pmid:
                continue
            with self.subTest(referencia=ref.number):
                self.assertRegex(ref.pmid, r"^\d{7,8}$")
                self.assertLessEqual(int(ref.pmid), check.PMID_LIMIT)
                self.assertNotIn(ref.pmid, seen)
                seen[ref.pmid] = ref.number

    def test_doi_e_unico_e_bem_formado(self):
        seen = {}
        for ref in self.references:
            if not ref.doi:
                continue
            with self.subTest(referencia=ref.number):
                self.assertTrue(ref.doi.startswith("10."))
                self.assertNotIn(" ", ref.doi)
                self.assertNotIn(ref.doi, seen)
                seen[ref.doi] = ref.number

    def test_blocos_de_referencia_nao_vazam_para_a_entrada_seguinte(self):
        # A entrada 7 é documentação de indústria sem PMID; o PMID 36640771
        # pertence à entrada 8. Um parser que só procura o próximo "PMID" no
        # texto erraria essa fronteira e criaria uma citação falsa.
        by_number = {ref.number: ref for ref in self.references}
        self.assertIsNone(by_number[7].pmid)
        self.assertEqual(by_number[7].doi, None)
        self.assertEqual(by_number[8].pmid, "36640771")
        self.assertEqual(by_number[8].first_author, "Galán-Rioja")

    def test_primeiro_autor_e_extraido_do_campo_de_autores(self):
        by_number = {ref.number: ref for ref in self.references}
        self.assertEqual(by_number[11].first_author, "Jeffries")
        self.assertEqual(by_number[27].first_author, "Coyle")
        self.assertEqual(by_number[35].first_author, "Borszcz")
        self.assertFalse(by_number[37].person_author)  # Intervals.icu / David

    def test_toda_citacao_do_corpo_resolve_para_uma_entrada(self):
        known_pmids = {ref.pmid for ref in self.references if ref.pmid}
        known_numbers = {ref.number for ref in self.references}
        cited_pmids = set(check.PMID_RE.findall(self.body))
        cited_numbers = {
            int(number) for number in check.BRACKET_REF_RE.findall(self.body)
        }
        self.assertEqual(cited_pmids - known_pmids, set())
        self.assertEqual(cited_numbers - known_numbers, set())

    def test_nenhuma_referencia_orfa(self):
        cited_pmids = set(check.PMID_RE.findall(self.body))
        cited_numbers = {
            int(number) for number in check.BRACKET_REF_RE.findall(self.body)
        }
        for ref in self.references:
            cited = (ref.pmid is not None and ref.pmid in cited_pmids) or (
                ref.number in cited_numbers
            )
            with self.subTest(referencia=ref.number, autor=ref.first_author):
                self.assertTrue(cited, "entrada não citada no corpo")

    def test_matriz_tem_quatro_colunas_e_limite_explicito(self):
        rows = check.matrix_rows(self.text)
        self.assertGreaterEqual(len(rows), 14)
        for feature, method, source, limit in rows:
            with self.subTest(feature=feature):
                self.assertTrue(feature)
                self.assertTrue(method)
                self.assertTrue(source)
                self.assertGreaterEqual(
                    len(limit), 40, "limite do que a fonte não mostra está vago"
                )
        self.assertIn(
            "o que o estudo não mostra",
            self.text.casefold(),
            "a coluna de limite precisa ser explícita",
        )

    def test_matriz_cobre_todas_as_features_do_documento(self):
        matrix = " ".join(row[0] for row in check.matrix_rows(self.text))
        for feature in FEATURES_OBRIGATORIAS:
            with self.subTest(feature=feature):
                self.assertIn(feature, matrix)

    def test_matriz_nao_cita_referencia_inexistente(self):
        known = {ref.number for ref in self.references}
        for row in check.matrix_rows(self.text):
            for number in check.BRACKET_REF_RE.findall(row[2]):
                with self.subTest(feature=row[0], referencia=number):
                    self.assertIn(int(number), known)

    def test_camada_offline_nao_tem_falhas(self):
        findings = check.offline_findings(self.body, self.refs_text, self.references)
        failures = [item for item in findings if item.level == "fail"]
        self.assertEqual(
            failures,
            [],
            "\n".join(f"{item.reference}: {item.field}: {item.message}" for item in failures),
        )

    def test_documento_aponta_para_o_verificador(self):
        self.assertIn("scripts/check_references.py", self.refs_text)
        self.assertIn("tests/test_scientific_references.py", self.text)

    def test_comparador_aceita_metadados_corretos(self):
        ref = check.Reference(
            number=8,
            author="Galán-Rioja, M. Á., Gonzalez-Ravé, J. M., et al.",
            year=2023,
            title=(
                "Training Periodization, Intensity Distribution, and Volume in "
                "Trained Cyclists: A Systematic Review"
            ),
            pmid="36640771",
            doi=None,
            url=None,
            block="",
        )
        findings = check.compare_metadata(
            ref,
            source="PMID",
            title=(
                "Training Periodization, Intensity Distribution, and Volume in "
                "Trained Cyclists: A Systematic Review"
            ),
            authors=["Galán-Rioja M", "Gonzalez-Ravé JM"],
            years=["2023 Jul"],
            identifier="36640771",
        )
        levels = {item.field: item.level for item in findings}
        self.assertEqual(levels, {"autor": "ok", "ano": "ok", "título": "ok"})

    def test_comparador_rejeita_pmid_de_outro_assunto(self):
        ref = check.Reference(
            number=99,
            author="Meyer, T.",
            year=2020,
            title="Aerobic capacity in trained cyclists",
            pmid="10222543",
            doi=None,
            url=None,
            block="",
        )
        findings = check.compare_metadata(
            ref,
            source="PMID",
            title="Pancreatic cancer: a review of gastroenterology findings",
            authors=["Smith J"],
            years=["1999"],
            identifier="10222543",
        )
        levels = {item.field: item.level for item in findings}
        self.assertEqual(levels["autor"], "fail")
        self.assertEqual(levels["ano"], "fail")
        self.assertEqual(levels["título"], "fail")

    def test_comparador_nao_falha_por_ano_de_publicacao_adjacente(self):
        ref = check.Reference(
            number=15,
            author="Düking, P., et al.",
            year=2021,
            title=(
                "Monitoring and adapting endurance training on the basis of heart "
                "rate variability monitored by wearable technologies"
            ),
            pmid="34489178",
            doi=None,
            url=None,
            block="",
        )
        findings = check.compare_metadata(
            ref,
            source="PMID",
            title=(
                "Monitoring and adapting endurance training on the basis of heart "
                "rate variability monitored by wearable technologies"
            ),
            authors=["Düking P"],
            years=["2022"],
            identifier="34489178",
        )
        levels = {item.field: item.level for item in findings}
        self.assertEqual(levels["ano"], "warn")
        self.assertEqual(levels["autor"], "ok")
        self.assertEqual(levels["título"], "ok")

    def test_comparador_nao_falha_por_subtitulo_ausente_na_fonte(self):
        ref = check.Reference(
            number=19,
            author="Buchheit, M., & Laursen, P. B.",
            year=2013,
            title=(
                "High-intensity interval training, solutions to the programming "
                "puzzle: Part I: cardiopulmonary emphasis"
            ),
            pmid="23539308",
            doi=None,
            url=None,
            block="",
        )
        findings = check.compare_metadata(
            ref,
            source="PMID",
            title="High-Intensity Interval Training, Solutions to the Programming Puzzle",
            authors=["Buchheit M"],
            years=["2013"],
            identifier="23539308",
        )
        levels = {item.field: item.level for item in findings}
        self.assertEqual(levels["título"], "ok")
        self.assertEqual(levels["autor"], "ok")
        self.assertEqual(levels["ano"], "ok")


if __name__ == "__main__":
    unittest.main()

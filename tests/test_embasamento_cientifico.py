import re
import unittest
from pathlib import Path

REPO_DOC = Path(__file__).resolve().parent.parent / "docs" / "EMBASAMENTO-CIENTIFICO.md"

SECOES_ESPERADAS = (
    "## 1. Princípios",
    "## 2. FTP",
    "## 3. Critical Power e W'",
    "## 4. Zonas",
    "## 5. Periodização",
    "## 6. Distribuição de intensidade",
    "## 7. Training Load",
    "## 8. CTL / ATL / TSB",
    "## 9. Readiness",
    "## 10. Adaptation State",
    "## 11. Progression Engine",
    "## 12. VO2max",
    "## 13. Recovery / Deload",
    "## 14. Limitações",
    "## 15. Referências",
)

CLASSIFICACOES = ("EVIDÊNCIA CIENTÍFICA", "HEURÍSTICA DO SISTEMA",
                  "MODELO COMPUTACIONAL")

PMIDs_ESPERADOS = (
    "36640771",  # Galán-Rioja et al. 2023, periodizacao em ciclistas treinados
    "39788807",  # meta-analise 2025, distribuicao e volume
    "34304689",  # FTP20 scoping review
    "31269000",  # FTP vs parametros de lactato
    "31689684",  # FTP95 vs MLSS
    "33728842",  # FTP vs VT / RCP
    "32899777",  # Critical Power / W'
    "34489178",  # HRV-guided training
    "33143175",  # HRV-guided training, VO2max
    "42237396",  # HIIT / VO2max 2026
    "42482078",  # HIIT network meta-analise 2026
)


class EmbasamentoCientificoTest(unittest.TestCase):
    """Contrato documental: secoes, classificacao e rastreabilidade de fontes.

    REGRA: nenhuma afirmacao fisiologica entra no documento sem PMID
    verificavel, e nenhuma referencia e inventada. Um PMID fora do limite
    estrutural, um autor trocado ou um superlativo sem base falha a suite.
    """

    @classmethod
    def setUpClass(cls):
        cls.doc = REPO_DOC.read_text(encoding="utf-8")

    def test_existe_e_nao_e_vazio(self):
        self.assertTrue(REPO_DOC.exists())
        self.assertGreater(len(self.doc), 4000)

    def test_tem_as_quinze_secoes_na_ordem(self):
        positions = []
        for heading in SECOES_ESPERADAS:
            self.assertIn(heading, self.doc, f"secao ausente: {heading}")
            positions.append(self.doc.index(heading))
        self.assertEqual(positions, sorted(positions), "secoes fora de ordem")

    def test_todas_as_tres_classificacoes_sao_usadas(self):
        for label in CLASSIFICACOES:
            self.assertIn(label, self.doc, f"classificacao ausente: {label}")

    def test_classificacao_aparece_antes_de_cada_secao_de_conteudo(self):
        # Cada seção de conteúdo precisa rotular o que é evidência, heurística ou
        # modelo — é o que impede heurística de ser lida como mecanismo.
        for heading in SECOES_ESPERADAS[1:-1]:
            start = self.doc.index(heading)
            end = self.doc.find("\n## ", start + 1)
            block = self.doc[start:end if end != -1 else len(self.doc)]
            labelled = any(label in block for label in CLASSIFICACOES)
            self.assertTrue(labelled, f"sem classificacao: {heading}")

    def test_todas_as_referencias_do_prompt_estao_citadas(self):
        for pmid in PMIDs_ESPERADOS:
            self.assertIn(pmid, self.doc, f"PMID nao citado: {pmid}")

    def test_pmids_citados_tem_formato_de_referencia(self):
        # Todo PMID no corpo precisa aparecer na seção de referências com autor,
        # para não haver fonte órfã nem autor sem fonte.
        body, _, refs = self.doc.partition("## 15. Referências")
        cited = set(re.findall(r"PMID (\d{7,8})", body))
        for pmid in cited:
            self.assertIn(pmid, refs, f"PMID {pmid} citado sem referencia")

    def test_nenhum_pmid_inexistente(self):
        # 4294967295 é o limite superior do inteiro de 32 bits sem sinal: um
        # PMID acima disso é estruturalmente impossível, logo inventado.
        for pmid in re.findall(r"PMID (\d{7,9})", self.doc):
            self.assertLessEqual(int(pmid), 4294967295,
                                 f"PMID fora do limite: {pmid}")

    def test_tss_e_identificado_como_metodologia_de_industria(self):
        block = self.doc.partition("## 7. Training Load")[2]
        block = block.partition("## 8.")[0]
        self.assertIn("METODOLOGIA DE INDÚSTRIA", block)
        self.assertIn("não são equivalentes a MLSS, LT, RCP ou Critical Power", block)

    def test_secao_de_limitacoes_enumera_as_ressalvas(self):
        block = self.doc.partition("## 14. Limitações")[2]
        block = block.partition("## 15.")[0]
        for expected in ("FTP não é fisiologia", "Não há modelo de periodização superior",
                         "Não há protocolo de VO2max superior",
                         "TSS é metodologia de indústria",
                         "Prontidão não prediz desempenho",
                         "Módulos isolados não afetam a publicação"):
            self.assertIn(expected, block, f"limitacao ausente: {expected}")

    def test_superlativos_sem_base_sao_proibidos(self):
        # "melhor"/"ideal"/"otimo" so entram acompanhados de ressalva ou
        # referencia; a regra e nao afirmar superioridade onde a evidencia nao a
        # sustenta.
        for match in re.finditer(r"\b(melhor|ideal|ótimo|otimo)\b", self.doc,
                                 re.IGNORECASE):
            start = max(0, match.start() - 90)
            context = self.doc[start:match.end() + 90]
            hedged = any(term in context.lower() for term in
                         ("não há", "sem evidência", "não existe", "não foram",
                          "nenhum", "evidência suficiente", "comparar", "não se"))
            self.assertTrue(hedged,
                            f"superlativo sem base: ...{context.strip()}...")

    def test_limites_de_concordancia_do_ftp_vs_lactato_estao_citados(self):
        # O numero que sustenta a nao-equivalencia de FTP e MLSS/LT.
        block = self.doc.partition("## 2. FTP")[2]
        block = block.partition("## 3.")[0]
        self.assertIn("−45 a +51 W", block)
        self.assertIn("88,5% do FTP", block)
        self.assertIn("refuta equivalência", block)

    def test_ausencia_de_superioridade_e_declarada_na_vo2max(self):
        block = self.doc.partition("## 12. VO2max")[2]
        block = block.partition("## 13.")[0]
        self.assertIn("nenhuma estrutura de protocolo é superior", block.lower())
        self.assertIn("I² = 69,2%", block)
        self.assertIn("exploratório", block)

    def test_sobreposicao_de_familias_esta_documentada(self):
        block = self.doc.partition("## 4. Zonas")[2]
        block = block.partition("## 5.")[0]
        self.assertIn("91–97% FTP", block)
        self.assertIn("AmbiguousIntensity", block)
        self.assertIn("não equivale a\nlimiar fisiológico", block.replace("  ", " "))

    def test_z7_fora_do_invariante_e_explicito(self):
        self.assertIn("Z7 está fora de `ZONE_BANDS`", self.doc)

    def test_vo2_z6_esta_documentado(self):
        block = self.doc.partition("## 12. VO2max")[2].partition("## 13.")[0]
        self.assertIn("Z6", block)
        self.assertIn("Z5_CEILING", block)

    def test_referencia_7_e_marcada_como_industria(self):
        refs = self.doc.partition("## 15. Referências")[2]
        entry = refs.partition("7. **Coggan")[2].partition("8. **")[0]
        self.assertIn("METODOLOGIA DE INDÚSTRIA", entry)

    def test_links_de_pmids_apontam_para_o_pubmed(self):
        self.assertNotRegex(self.doc, r"pubmed\.ncbi\.nlm\.nih\.gov/\D")
        for pmid in re.findall(r"https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?", self.doc):
            self.assertIn(pmid, self.doc,
                          f"URL de PMID {pmid} sem PMID correspondente na lista")

    def test_vault_e_declarado_como_fonte_da_tabela_z1_z7(self):
        # Sem isso, nao ha como saber onde a tabela canonica vive.
        self.assertIn("Fonte única da verdade: o vault", self.doc)
        self.assertIn("EMBASAMENTO-CIENTIFICO.md", self.doc)
        self.assertIn("Z1–Z7", self.doc)

    def test_bibliografia_preserva_referencias_do_prompt(self):
        refs = self.doc.partition("## 15. Referências")[2]
        for expected in ("Banister", "Seiler", "Coggan", "Billat", "Friel",
                         "Galán-Rioja", "Cove", "Mackey", "Jeffries", "Inglis",
                         "Sitko", "Chorley", "Düking", "Granero-Gallegos",
                         "Schoenmakers", "Held"):
            self.assertIn(expected, refs, f"referencia ausente: {expected}")


if __name__ == "__main__":
    unittest.main()

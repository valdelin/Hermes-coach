"""Testes do utilitário de sync repo -> vault (scripts/sync_vault_docs.py).

Nenhum teste escreve no vault real: todo path vem de ``tempfile.TemporaryDirectory``
(§23). Os testes que tocam o disco usam um repo/vault falsos montados aqui.
"""

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sync_vault_docs.py"
SPEC = importlib.util.spec_from_file_location("sync_vault_docs", SCRIPT)
sync = importlib.util.module_from_spec(SPEC)
# `dataclass` resolve o modulo via sys.modules; registrar antes de executar
sys.modules[SPEC.name] = sync
SPEC.loader.exec_module(sync)

MARKER = "> [!info] Dono deste documento"

REPO_OWNERSHIP = (
    f"{MARKER}\n"
    "> Fonte canônica: `docs/GLOSSARIO.md` **no repo** (o mesmo arquivo do\n"
    "> vault é cópia). Quando divergirem, o repo vence. Editar no repo e\n"
    "> copiar.\n"
    "> Espelho: `~/Documents/Obsidian Vault/.../GLOSSARIO.md`.\n")

VAULT_OWNERSHIP = (
    f"{MARKER}\n"
    "> Fonte canônica: `docs/GLOSSARIO.md` **no repo** (o mesmo arquivo do\n"
    "> vault é cópia). Quando divergirem, o repo vence. Editar no repo e\n"
    "> copiar.\n"
    "> Repo: `~/Work/cycling-coach/`. **Este arquivo é espelho para leitura**, "
    "não um\n> segundo glossário independente.\n")

BODY_OLD = "## introducing\n\nconteudo antigo do glossario.\n\n## fim\n"
BODY_NEW = "## Termo\n\nconteudo novo do glossario, bem maior que o antigo.\n"


def _doc(body: str, ownership: str = VAULT_OWNERSHIP) -> str:
    return "# Glossario — Hermes Coach\n\n" + ownership + "\n" + body


class _Fixture(unittest.TestCase):
    """Repo e vault falsos, um par GLOSSARIO por vez."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.vault = root / "vault"
        (self.repo / "docs").mkdir(parents=True)
        self.vault.mkdir(parents=True)
        self.mirror = sync.Mirror("docs/GLOSSARIO.md", "GLOSSARIO.md",
                                  "não um segundo glossário independente")

    def tearDown(self):
        self.tmp.cleanup()

    def write_repo(self, body: str = BODY_NEW, ownership: str = REPO_OWNERSHIP):
        (self.repo / "docs" / "GLOSSARIO.md").write_text(
            _doc(body, ownership), encoding="utf-8")

    def write_vault(self, text: str):
        (self.vault / "GLOSSARIO.md").write_text(text, encoding="utf-8")

    def read_vault(self) -> str:
        return (self.vault / "GLOSSARIO.md").read_text(encoding="utf-8")

    def run_plan(self, *, write: bool = False, dry_run: bool = False):
        return sync.plan_mirror(self.mirror, self.repo, self.vault,
                                write=write, dry_run=dry_run)


class PrefixOrderTest(unittest.TestCase):
    """O bloco de ownership nao precisa vir logo apos o titulo.

    `docs/PORTAL-UI-DESIGN.md` tem um callout `> Status:` entre os dois. Um
    rebuild `title + ownership + body` reordenaria o documento; o prefixo tem de
    sobreviver verbatim.
    """

    PREFIX_CALL = ("> Status: **rascunho aprovado** (Trilha B).\n")
    REPO = ("# Portal\n\n" + PREFIX_CALL + VAULT_OWNERSHIP + "\ncorpo do repo.\n")

    def test_split_preserva_o_prefixo(self):
        parsed = sync.split_document(self.REPO, where="r")
        self.assertEqual(parsed.prefix, "# Portal\n\n" + self.PREFIX_CALL)
        self.assertEqual(parsed.body, "corpo do repo.\n")
        self.assertTrue(parsed.title.startswith("# Portal"))

    def test_rebuild_nao_reordena(self):
        parsed = sync.split_document(self.REPO, where="r")
        target = sync.build_mirror(parsed, sync.Mirror("docs/P.md", "P.md"),
                                   parsed.ownership)
        self.assertEqual(target, self.REPO)
        # a linha de Status continua ANTES do bloco de ownership
        self.assertLess(target.index(self.PREFIX_CALL),
                        target.index(VAULT_OWNERSHIP))

    def test_prefix_do_repo_e_propagado_ao_espelho(self):
        parsed = sync.split_document(self.REPO, where="r")
        vault_text = "# Portal\n\n" + VAULT_OWNERSHIP + "\ncorpo velho.\n"
        existing = sync.split_document(vault_text, where="v").ownership
        target = sync.build_mirror(
            parsed, sync.Mirror("docs/P.md", "P.md"), existing)
        self.assertIn(self.PREFIX_CALL, target)
        self.assertNotIn("corpo velho", target)

    def test_ownership_apos_outro_callout_e_reconhecido(self):
        parsed = sync.split_document(self.REPO, where="r")
        self.assertEqual(parsed.ownership, VAULT_OWNERSHIP)


# ---------------------------------------------------------------------------
# Body extraction (§12)
# ---------------------------------------------------------------------------

class SplitDocumentTest(unittest.TestCase):
    def test_divide_titulo_ownership_corpo(self):
        parsed = sync.split_document(_doc(BODY_NEW), where="t")
        self.assertTrue(parsed.title.startswith("# Glossario"))
        self.assertEqual(parsed.ownership, VAULT_OWNERSHIP)
        self.assertEqual(parsed.body, BODY_NEW)

    def test_callout_continua_ate_a_primeira_linha_fora_dele(self):
        parsed = sync.split_document(_doc(BODY_NEW), where="t")
        self.assertNotIn("conteudo novo", parsed.ownership)
        self.assertNotIn(MARKER, parsed.body)

    def test_sem_ownership_falha_fechado(self):
        texto = "# Titulo\n\ncorpo sem ownership.\n"
        with self.assertRaises(sync.DocumentError) as ctx:
            sync.split_document(texto, where="t")
        self.assertIn("ownership block missing", str(ctx.exception))

    def test_arquivo_vazio_falha(self):
        with self.assertRaises(sync.DocumentError):
            sync.split_document("", where="t")

    def test_ownership_sem_linha_em_branco_apos(self):
        texto = ("# T\n\n" + VAULT_OWNERSHIP + "corpo grudado.\n")
        parsed = sync.split_document(texto, where="t")
        self.assertEqual(parsed.body, "corpo grudado.\n")


# ---------------------------------------------------------------------------
# Renderizacao de ownership (§9, §10)
# ---------------------------------------------------------------------------

class RenderOwnershipTest(unittest.TestCase):
    def test_template_deterministico(self):
        a = sync.render_ownership("docs/GLOSSARIO.md", "não um segundo glossário")
        b = sync.render_ownership("docs/GLOSSARIO.md", "não um segundo glossário")
        self.assertEqual(a, b)
        self.assertEqual(a.count(MARKER), 1)

    def test_mirror_note_aparece(self):
        out = sync.render_ownership("docs/X.md", "não um segundo deck")
        self.assertIn("não um segundo deck.", out)

    def test_sem_mirror_note_usa_variante_neutra(self):
        out = sync.render_ownership("docs/X.md", None)
        self.assertIn("**Este arquivo é espelho para leitura**.", out)
        self.assertNotIn("não um", out)

    def test_referencia_canonica_correta(self):
        out = sync.render_ownership("docs/ROADMAP.md", None)
        self.assertIn("`docs/ROADMAP.md`", out)


# ---------------------------------------------------------------------------
# Regression do bug real: corpo antigo + corpo novo (§6, §19)
# ---------------------------------------------------------------------------

class DuplicationRegressionTest(_Fixture):
    def test_mirror_com_corpo_antigo_nao_e_concatenado(self):
        """O erro da sessão: espelho = ownership + corpo_antigo, repo = corpo_novo."""
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        result = self.run_plan(write=True)
        self.assertEqual(result.status, "updated")

        out = self.read_vault()
        self.assertIn(BODY_NEW, out)
        self.assertNotIn("conteudo antigo do glossario", out)
        # a forma proibida: corpo novo seguido do corpo antigo
        self.assertNotIn(BODY_NEW + BODY_OLD, out)
        self.assertEqual(out.count(BODY_NEW), 1)

    def test_ownership_existente_e_preservado_byte_a_byte(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        self.run_plan(write=True)
        self.assertIn(VAULT_OWNERSHIP, self.read_vault())
        self.assertEqual(sync.split_document(self.read_vault(),
                                             where="v").ownership,
                         VAULT_OWNERSHIP)

    def test_ownership_ausente_e_gerado_de_template(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault("# Glossario — Hermes Coach\n\n" + BODY_OLD)

        result = self.run_plan(write=True)
        self.assertEqual(result.status, "updated")
        self.assertTrue(any("ownership block missing" in f
                            for f in result.findings))
        parsed = sync.split_document(self.read_vault(), where="v")
        self.assertEqual(parsed.ownership.count(MARKER), 1)
        self.assertIn("não um segundo glossário", parsed.ownership)


# ---------------------------------------------------------------------------
# Regression de ownership: exatamente 1 bloco (§20)
# ---------------------------------------------------------------------------

class OwnershipCountTest(_Fixture):
    def test_resultado_tem_exatamente_um_bloco(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))
        self.run_plan(write=True)
        self.assertEqual(len(sync.ownership_blocks(self.read_vault())), 1)

    def test_espelho_com_dois_blocos_e_reportado(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD, ownership=VAULT_OWNERSHIP
                              + "\n" + VAULT_OWNERSHIP))
        result = self.run_plan()
        self.assertTrue(any("2 blocos de ownership" in f
                            for f in result.findings), result.findings)

    def test_espelho_com_dois_blocos_e_reparado_no_sync(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD, ownership=VAULT_OWNERSHIP
                              + "\n" + VAULT_OWNERSHIP))
        self.run_plan(write=True)
        self.assertEqual(len(sync.ownership_blocks(self.read_vault())), 1)

    def test_espelho_zerado_sem_ownership_no_espelho(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD, ownership=""))
        self.run_plan(write=True)
        self.assertEqual(len(sync.ownership_blocks(self.read_vault())), 1)


# ---------------------------------------------------------------------------
# Idempotencia e round trip (§21, §22)
# ---------------------------------------------------------------------------

class IdempotencyTest(_Fixture):
    def test_sync_duas_vezes_e_byte_identico(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        self.assertEqual(self.run_plan(write=True).status, "updated")
        first = self.read_vault()

        self.assertEqual(self.run_plan(write=True).status, "in_sync")
        self.assertEqual(self.read_vault(), first)

    def test_sync_de_mirror_inexistente_e_idempotente(self):
        self.write_repo(body=BODY_NEW)

        self.assertEqual(self.run_plan(write=True).status, "updated")
        first = self.read_vault()
        self.assertEqual(self.run_plan(write=True).status, "in_sync")
        self.assertEqual(self.read_vault(), first)

    def test_round_trip_logico_corpos_iguais(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))
        self.run_plan(write=True)

        repo_body = sync.split_document(
            (self.repo / "docs" / "GLOSSARIO.md").read_text(encoding="utf-8"),
            where="r").body
        vault_body = sync.split_document(self.read_vault(), where="v").body
        self.assertEqual(repo_body, vault_body)


# ---------------------------------------------------------------------------
# Estados e falhas (§13, §18)
# ---------------------------------------------------------------------------

class PlanStatesTest(_Fixture):
    def test_ja_sincronizado_reorna_in_sync(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_NEW))
        result = self.run_plan()
        self.assertEqual(result.status, "in_sync")
        self.assertTrue(result.ok)

    def test_corpo_divergente_e_detectado(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))
        result = self.run_plan()
        self.assertEqual(result.status, "would_update")

    def test_repo_sem_ownership_falha_sem_escrever(self):
        self.write_repo(ownership="")
        self.write_vault(_doc(BODY_OLD))
        result = self.run_plan(write=True)
        self.assertEqual(result.status, "error")
        self.assertIn("ownership block missing", result.detail)
        self.assertEqual(self.read_vault(), _doc(BODY_OLD))

    def test_repo_inexistente_falha(self):
        result = self.run_plan(write=True)
        self.assertEqual(result.status, "error")
        self.assertIn("repo ausente", result.detail)

    def test_repo_nunca_e_modificado(self):
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))
        antes = (self.repo / "docs" / "GLOSSARIO.md").read_text(encoding="utf-8")
        self.run_plan(write=True)
        depois = (self.repo / "docs" / "GLOSSARIO.md").read_text(encoding="utf-8")
        self.assertEqual(antes, depois)


# ---------------------------------------------------------------------------
# Escrita atomica e backup (§7, §8)
# ---------------------------------------------------------------------------

class AtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_escreve_e_cria_backup_do_anterior(self):
        alvo = self.dir / "sub" / "doc.md"
        alvo.parent.mkdir(parents=True)
        alvo.write_text("antigo\n", encoding="utf-8")
        backup = self.dir / "bk" / "doc.md.bak"

        sync.atomic_write(alvo, "novo\n", backup=backup)

        self.assertEqual(alvo.read_text(encoding="utf-8"), "novo\n")
        self.assertEqual(backup.read_text(encoding="utf-8"), "antigo\n")

    def test_nao_deixa_arquivo_temporario(self):
        alvo = self.dir / "doc.md"
        sync.atomic_write(alvo, "conteudo\n")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["doc.md"])

    def test_preserva_newline_final_e_ausencia_de_ele(self):
        alvo = self.dir / "doc.md"
        sync.atomic_write(alvo, "com\n")
        self.assertEqual(alvo.read_text(encoding="utf-8"), "com\n")
        sync.atomic_write(alvo, "sem")
        self.assertEqual(alvo.read_text(encoding="utf-8"), "sem")
        self.assertFalse(alvo.read_text(encoding="utf-8").endswith("\n"))

    def test_falha_de_escrita_nao_deixa_temp_quebrado(self):
        alvo = self.dir / "doc.md"
        alvo.write_text("original\n", encoding="utf-8")

        def _boom(src, dst):
            raise OSError("falha simulada no replace")

        real_replace = os.replace
        try:
            os.replace = _boom
            with self.assertRaises(OSError):
                sync.atomic_write(alvo, "novo\n")
        finally:
            os.replace = real_replace

        self.assertEqual(alvo.read_text(encoding="utf-8"), "original\n")
        self.assertEqual([p.name for p in self.dir.iterdir()], ["doc.md"])


# ---------------------------------------------------------------------------
# Mapping (§2, §3, §17)
# ---------------------------------------------------------------------------

class MappingTest(unittest.TestCase):
    def test_todos_os_pares_existem_no_repo(self):
        for m in sync.MIRRORS:
            self.assertTrue((sync.REPO_ROOT / m.repo).exists(), m.repo)

    def test_espelhos_declarados_batem_com_o_vault_real(self):
        for m in sync.MIRRORS:
            self.assertIn(m.vault, sync.MIRRORS_BY_VAULT)
            self.assertIs(sync.MIRRORS_BY_VAULT[m.vault], m)

    def test_nome_diferente_do_basename_e_explicito(self):
        """ROADMAP e ARQUITETURA nao podem ser inferidos pelo nome."""
        roadmap = sync.MIRRORS_BY_KEY["docs/ROADMAP.md"]
        self.assertEqual(roadmap.vault, "PLANO-NOVAS-IMPLEMENTACOES.md")
        arq = sync.MIRRORS_BY_KEY["docs/ARQUITETURA.md"]
        self.assertEqual(arq.vault,
                         "hermes_coach_arquitetura_e_implementa_o.md")

    def test_changelog_mapeado_para_raiz_do_repo(self):
        self.assertIn("CHANGELOG.md", sync.MIRRORS_BY_KEY)

    def test_lookup_aceita_varias_formas(self):
        for chave in ("GLOSSARIO", "GLOSSARIO.md", "docs/GLOSSARIO.md"):
            self.assertIsNotNone(sync._lookup(chave), chave)
        self.assertIsNotNone(sync._lookup("PLANO-NOVAS-IMPLEMENTACOES.md"))

    def test_lookup_desconhecido_retorna_none(self):
        self.assertIsNone(sync._lookup("NAO-EXISTE"))

    def test_nao_ha_docs_de_hr4_ou_novos_itens(self):
        for m in sync.MIRRORS:
            self.assertNotIn("HR-4", m.repo)
            self.assertNotIn("SLEEP", m.repo.upper())

    def test_check_sem_sync_cobre_todos(self):
        escolhidos = sync.select(None, all_docs=True)
        self.assertEqual(len(escolhidos), len(sync.MIRRORS))

    def test_sync_de_um_doc_so_traz_um(self):
        escolhidos = sync.select(["GLOSSARIO"], all_docs=False)
        self.assertEqual(len(escolhidos), 1)
        self.assertEqual(escolhidos[0].repo, "docs/GLOSSARIO.md")

    def test_doc_que_cita_o_marker_nao_vira_orfao(self):
        """A propria doc do tooling cita o marker na prosa: falso positivo."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "VAULT-SYNC.md").write_text(
                "# Sync\n\nnum callout `" + MARKER + "` marca o dono.\n\n"
                "corpo normal.\n", encoding="utf-8")
            self.assertEqual(sync.unmapped(root), [])

    def test_doc_com_bloco_real_e_orfao(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "NOVO.md").write_text(
                "# Novo\n\n" + VAULT_OWNERSHIP + "\ncorpo.\n", encoding="utf-8")
            self.assertEqual(sync.unmapped(root), ["docs/NOVO.md"])


# ---------------------------------------------------------------------------
# CLI (§5, §15, §16, §24)
# ---------------------------------------------------------------------------

class CliTest(_Fixture):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sync.main(argv)
        return code, out.getvalue(), err.getvalue()

    def _cli_repo(self):
        """Faz main() usar o repo/vault falsos."""
        self._real_root = sync.REPO_ROOT
        sync.REPO_ROOT = self.repo

    def tearDown(self):
        sync.REPO_ROOT = getattr(self, "_real_root", sync.REPO_ROOT)
        super().tearDown()

    def test_check_nao_escreve_e_retorna_erro_quando_divergente(self):
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        code, out, _ = self._run(["--check", "--sync", "GLOSSARIO", "--vault",
                                  str(self.vault)])
        self.assertEqual(code, 1)
        self.assertIn("would_update", out)
        self.assertEqual(self.read_vault(), _doc(BODY_OLD))

    def test_check_retorna_zero_quando_em_sincronia(self):
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_NEW))

        code, out, _ = self._run(["--check", "--sync", "GLOSSARIO", "--vault",
                                  str(self.vault)])
        self.assertEqual(code, 0)
        self.assertIn("in_sync", out)

    def test_dry_run_nao_escreve(self):
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        code, out, _ = self._run(["--sync", "GLOSSARIO", "--dry-run", "--vault",
                                  str(self.vault)])
        self.assertEqual(code, 0)
        self.assertIn("would_update", out)
        self.assertEqual(self.read_vault(), _doc(BODY_OLD))

    def test_sync_escreve_e_depois_reporta_in_sync(self):
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        code, _, _ = self._run(["--sync", "GLOSSARIO", "--vault",
                                str(self.vault)])
        self.assertEqual(code, 0)
        self.assertIn(BODY_NEW, self.read_vault())

        code, out, _ = self._run(["--check", "--sync", "GLOSSARIO", "--vault",
                                  str(self.vault)])
        self.assertEqual(code, 0)
        self.assertIn("in_sync", out)

    def test_sync_all_falha_cerrado_quando_falta_doc_no_repo(self):
        """O repo falso so tem GLOSSARIO; os outros 13 devem ser erro."""
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        code, out, err = self._run(["--sync-all", "--vault", str(self.vault)])
        self.assertEqual(code, 1)
        self.assertIn("repo ausente", out)
        self.assertIn("com erro", err)
        # o documento presente foi sincronizado mesmo assim
        self.assertIn(BODY_NEW, self.read_vault())

    def test_sync_de_um_documento(self):
        self._cli_repo()
        self.write_repo(body=BODY_NEW)
        self.write_vault(_doc(BODY_OLD))

        code, _, _ = self._run(["--sync", "GLOSSARIO", "--vault",
                                str(self.vault)])
        self.assertEqual(code, 0)
        self.assertIn(BODY_NEW, self.read_vault())

    def test_sync_de_nome_desconhecido_falha(self):
        code, _, err = self._run(["--sync", "NAO-EXISTE", "--vault",
                                  str(self.vault)])
        self.assertEqual(code, 2)
        self.assertIn("nenhum documento reconhecido", err)

    def test_sem_modo_nao_faz_nada(self):
        with self.assertRaises(SystemExit):
            self._run(["--vault", str(self.vault)])

    def test_erro_de_validacao_sai_com_codigo_1(self):
        self._cli_repo()
        self.write_repo(ownership="")      # repo sem ownership
        self.write_vault(_doc(BODY_OLD))

        code, _, err = self._run(["--sync-all", "--vault", str(self.vault)])
        self.assertEqual(code, 1)
        self.assertIn("com erro", err)


if __name__ == "__main__":
    unittest.main()
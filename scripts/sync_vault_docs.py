#!/usr/bin/env python3
"""Sincroniza documentos canonicos do repo para os espelhos no Obsidian vault.

Substitui o procedimento manual "editar no repo e copiar". O repo e sempre o
owner; o vault e mirror de leitura. A direcao inversa nao existe.

Por que a ferramenta existe (PROMPT 30): o sync manual da sessaoHR-3 duplicou
o corpo de quatro espelhos e sobrescreveu o bloco de ownership original de tres
deles. A causa foi um script ad-hoc que concatenou `corpo_do_vault` com
`corpo_do_repo`, e um header reconstruido a mao sem fonte. Este modulo centraliza
a extracao, valida em memoria e so entao escreve de forma atomica.

Garantias:

- ``repo`` e read-only; o unico alvo de escrita e o espelho no vault;
- o corpo do espelho e **substituido**, nunca concatenado ao corpo anterior;
- o bloco de ownership do espelho e preservado byte-a-byte quando ja existe e
  valido; so e gerado de template quando ausente;
- escrita atomica (temp file + ``fsync`` + ``os.replace``) com backup do
  arquivo anterior para restore dentro da mesma execucao;
- idempotente: sync duas vezes produz bytes identicos.

Uso:

    python3 scripts/sync_vault_docs.py --check
    python3 scripts/sync_vault_docs.py --check --dry-run
    python3 scripts/sync_vault_docs.py --sync GLOSSARIO
    python3 scripts/sync_vault_docs.py --sync-all --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

VAULT_SUBDIR = Path(
    "Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach")
VAULT_FALLBACK = Path(
    "~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach").expanduser()

OWNERSHIP_MARKER = "> [!info] Dono deste documento"
CANONICAL_PREFIX = "> Fonte canônica: `"
CANONICAL_MIDDLE = "` **no repo**"


# --------------------------------------------------------------------------
# Mapping explicito. Nenhum par e inferido por nome (§3): cada linha declara o
# path do repo, o nome do espelho no vault e o texto do espelho. `mirror_note`
# e a cauda especifica de cada documento ("não um segundo glossário"), usada
# apenas quando o bloco precisa ser gerado. §17.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Mirror:
    repo: str
    vault: str
    mirror_note: Optional[str] = None


MIRRORS: tuple[Mirror, ...] = (
    Mirror("docs/ARQUITETURA.md",
           "hermes_coach_arquitetura_e_implementa_o.md",
           "não uma segunda especificação independente"),
    Mirror("docs/COMPARACAO-PMC.md", "COMPARACAO-PMC.md",
           "não uma segunda análise de PMC"),
    Mirror("docs/DIAGRAMAS.md", "DIAGRAMAS.md",
           "não um segundo catálogo de diagramas"),
    Mirror("docs/EMBASAMENTO-CIENTIFICO.md", "EMBASAMENTO-CIENTIFICO.md"),
    Mirror("docs/GLOSSARIO.md", "GLOSSARIO.md"),
    Mirror("docs/PITCH-DECK.md", "PITCH-DECK.md"),
    Mirror("docs/PITCH-DECK-SLIDES.md", "PITCH-DECK-SLIDES.md",
           "não um segundo deck"),
    Mirror("docs/PORTAL-UI-DESIGN.md", "PORTAL-UI-DESIGN.md"),
    Mirror("docs/ROADMAP.md", "PLANO-NOVAS-IMPLEMENTACOES.md"),
    Mirror("docs/ROTEIRO-TESTES.md", "ROTEIRO-TESTES.md"),
    Mirror("docs/ROTEIRO-TREINADOR.md", "ROTEIRO-TREINADOR.md"),
    Mirror("docs/SYNC-PLATAFORMAS.md", "SYNC-PLATAFORMAS.md",
           "não um segundo guia de sincronização"),
    Mirror("docs/TEMAS.md", "TEMAS.md", "não um segundo kit de temas"),
    Mirror("CHANGELOG.md", "CHANGELOG.md"),
)

MIRRORS_BY_KEY = {m.repo: m for m in MIRRORS}
MIRRORS_BY_VAULT = {m.vault: m for m in MIRRORS}


# --------------------------------------------------------------------------
# Extracao (sem I/O). §12: o corpo comeca depois do callout de ownership e da
# primeira linha fora dele. Nada de `tail -n +N` por arquivo.
# --------------------------------------------------------------------------

class DocumentError(Exception):
    """Falha estrutural de um documento. SempreLevanta em vez de adivinhar."""


def _canonical_declaration(mirror: Mirror) -> str:
    return f"{CANONICAL_PREFIX}{mirror.repo}{CANONICAL_MIDDLE}"


@dataclass(frozen=True)
class ParsedDoc:
    prefix: str            # titulo + qualquer linha antes do bloco de ownership
    ownership: str         # bloco de ownership, terminado em "\n"
    body: str              # corpo apos o bloco, sem strip

    @property
    def title(self) -> str:
        return self.prefix.splitlines(keepends=True)[0] if self.prefix else ""


def split_document(text: str, *, where: str) -> ParsedDoc:
    """Divide `text` em prefixo, bloco de ownership e corpo.

    Falha fechada: sem bloco de ownership a ferramenta nao advinha onde a
    metadata termina (§13).

    O bloco de ownership nao precisa ser a primeira coisa depois do titulo —
    `docs/PORTAL-UI-DESIGN.md` tem um callout `> Status:` entre os dois. Por isso
    o prefixo e preservado verbatim e `prefix + ownership + body` reconstroi o
    arquivo **sem reordenar nada**.
    """
    if not text.endswith("\n"):
        pass  # entrada nao normalizada; corpo comparado byte-a-byte
    lines = text.splitlines(keepends=True)
    if not lines:
        raise DocumentError(f"{where}: arquivo vazio")

    idx = _ownership_start(lines)
    if idx is None:
        raise DocumentError(
            f"{where}: ownership block missing "
            f"(esperado `{OWNERSHIP_MARKER}`)")

    end = _ownership_end(lines, idx)
    return ParsedDoc(prefix="".join(lines[:idx]),
                     ownership="".join(lines[idx:end]),
                     body="".join(lines[_body_start(lines, end):]))


def _ownership_start(lines: list[str]) -> Optional[int]:
    """Primeira linha do callout de ownership, ou None."""
    for i, line in enumerate(lines):
        if line.startswith(OWNERSHIP_MARKER):
            return i
    return None


def _ownership_end(lines: list[str], start: int) -> int:
    """Ultima linha do callout (exclusive): a primeira que nao comeca com `>`."""
    i = start
    while i < len(lines) and lines[i].startswith(">"):
        i += 1
    return i


def _body_start(lines: list[str], ownership_end: int) -> int:
    """Inicio do corpo: apos o callout e a separacao em branco."""
    i = ownership_end
    while i < len(lines) and not lines[i].strip():
        i += 1
    return i


def ownership_blocks(text: str) -> list[str]:
    """Todos os blocos `> [!info] Dono...` do documento, para detectar duplicacao."""
    blocks: list[str] = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        if lines[i].startswith(OWNERSHIP_MARKER):
            end = _ownership_end(lines, i)
            blocks.append("".join(lines[i:end]))
            i = _body_start(lines, end)
            continue
        i += 1
    return blocks


def validate_ownership(text: str, mirror: Mirror, *, side: str) -> ParsedDoc:
    """Valida ownership semantico conforme o lado do espelho.

    Ambos os lados precisam apontar para *o mesmo* path canonico no repo. Um
    vault existente ainda deve declarar que e copia/espelho. Nunca se "conserta"
    metadata existente: ela e provenance, nao conteudo descartavel.
    """
    blocks = ownership_blocks(text)
    if not blocks:
        raise DocumentError(f"{side}:{mirror.vault}: ownership block missing")
    if len(blocks) != 1:
        raise DocumentError(
            f"{side}:{mirror.vault}: {len(blocks)} ownership blocks "
            "(esperado exatamente 1)")
    parsed = split_document(text, where=f"{side}:{mirror.vault}")
    expected = _canonical_declaration(mirror)
    if expected not in parsed.ownership:
        raise DocumentError(
            f"{side}:{mirror.vault}: origem canonica invalida "
            f"(esperado `{mirror.repo}` no repo)")
    if side == "vault":
        normalized = parsed.ownership.casefold()
        if "vault" not in normalized or ("espelho" not in normalized
                                         and "cópia" not in normalized):
            raise DocumentError(
                f"vault:{mirror.vault}: ownership nao declara espelho de leitura")
    return parsed


def _safe_repo_path(repo_root: Path, mirror: Mirror) -> Path:
    relative = Path(mirror.repo)
    if relative.is_absolute() or ".." in relative.parts:
        raise DocumentError(f"mapping invalido: repo path {mirror.repo!r}")
    root = repo_root.resolve()
    candidate = repo_root / relative
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise DocumentError(f"repo path fora da raiz: {mirror.repo!r}") from exc
    return candidate


def _safe_vault_path(vault_root: Path, mirror: Mirror) -> Path:
    relative = Path(mirror.vault)
    if (relative.is_absolute() or ".." in relative.parts
            or len(relative.parts) != 1):
        raise DocumentError(f"mapping invalido: vault path {mirror.vault!r}")
    root = vault_root.resolve()
    candidate = vault_root / relative
    if candidate.is_symlink():
        raise DocumentError(f"vault:{mirror.vault}: destino symlink recusado")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise DocumentError(f"vault:{mirror.vault}: destino fora do vault") from exc
    return candidate


def render_ownership(repo_ref: str, mirror_note: Optional[str]) -> str:
    """Gera o bloco de ownership do lado vault por template deterministico."""
    head = (f"{OWNERSHIP_MARKER}\n"
            f"> Fonte canônica: `{repo_ref}` **no repo** (o mesmo arquivo do\n"
            "> vault é cópia). Quando divergirem, o repo vence. Editar no repo e\n"
            "> copiar.\n")
    if mirror_note is None:
        return head + "> Repo: `~/Work/cycling-coach/`. " \
                      "**Este arquivo é espelho para leitura**.\n"
    return (head + "> Repo: `~/Work/cycling-coach/`. "
                   "**Este arquivo é espelho para leitura**, "
            + f"{mirror_note}.\n")


def build_mirror(repo_parsed: ParsedDoc, mirror: Mirror,
                 existing_ownership: Optional[str]) -> str:
    """Monta o conteudo final do espelho.

    Anexo **exatamente uma** copia do corpo do repo (§6). O corpo anterior do
    espelho nunca entra na conta. O prefixo do repo (titulo + callouts antes do
    ownership) e preservado, entao nada e reordenado. O ownership existente e
    preservado; so e gerado quando ausente (§10, para nao degradar wording).
    """
    ownership = (existing_ownership if existing_ownership is not None
                 else render_ownership(mirror.repo, mirror.mirror_note))
    return repo_parsed.prefix + ownership + "\n" + repo_parsed.body


# --------------------------------------------------------------------------
# Deteccao de duplicacao (§11). Só detecta repeticao integral ou quase
# integral do corpo canonico, que é o defeito que a ferramenta precisa impedir.
# Nao tenta ser um detector de repeticao textual arbitraria.
# --------------------------------------------------------------------------

def duplication_findings(text: str, body: str) -> list[str]:
    """Deteccao de duplicacao introduzida pelo proprio sync (§11).

    Escopo deliberado: repeticao **integral** do corpo canonico e excesso de
    blocos de ownership. Nao e detector de repeticao textual arbitraria.
    """
    findings: list[str] = []
    if not body.strip():
        return findings
    occurrences = text.count(body)
    if occurrences > 1:
        findings.append(
            f"corpo canonico aparece {occurrences}x (conteudo duplicado)")
    blocks = ownership_blocks(text)
    if len(blocks) > 1:
        findings.append(
            f"{len(blocks)} blocos de ownership (esperado exatamente 1)")
    # corpo canonico repetido de forma parcial logo apos ele mesmo
    half = len(body) // 2
    if half >= 64:
        head = body[:half]
        tail = body[half:]
        if tail and text.count(head) > 1 and tail in text:
            findings.append("corpo canonico aparece truncado alem da 1a copia")
    return findings


# --------------------------------------------------------------------------
# Resultado de uma operacao
# --------------------------------------------------------------------------

@dataclass
class Result:
    key: str
    repo_path: Path
    vault_path: Path
    status: str                    # in_sync | would_update | updated | error | skipped
    detail: str = ""
    findings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """`would_update` em modo check/dry-run é um achado, não um erro."""
        return self.status != "error"


# --------------------------------------------------------------------------
# Escrita atomica + backup (§7, §8). Sem dependencia de git no vault.
# --------------------------------------------------------------------------

def atomic_write(path: Path, content: str, *, backup: Optional[Path] = None) -> None:
    """Escreve `content` em `path` de forma atomica.

    Se `backup` for informado, o conteudo anterior e gravado la antes, para
    restore dentro da mesma execucao se algo falhar depois.
    """
    if backup is not None and path.exists():
        if backup.parent.is_symlink() or backup.is_symlink():
            raise OSError(f"backup symlink recusado: {backup}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(directory), prefix=".sync_vault_",
                                    suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# --------------------------------------------------------------------------
# Operacoes
# --------------------------------------------------------------------------

def resolve_vault_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    return (Path.home() / VAULT_SUBDIR)


def plan_mirror(mirror: Mirror, repo_root: Path, vault_root: Path,
                 *, write: bool, dry_run: bool) -> Result:
    # Caminhos vem exclusivamente de MIRRORS; ainda assim a defesa abaixo evita
    # que um mapping futuro ou argumento inesperado atravesse a raiz declarada.
    try:
        repo_path = _safe_repo_path(repo_root, mirror)
        vault_path = _safe_vault_path(vault_root, mirror)
    except DocumentError as exc:
        return Result(key=mirror.repo, repo_path=repo_root / mirror.repo,
                      vault_path=vault_root / mirror.vault, status="error",
                      detail=str(exc))

    result = Result(key=mirror.repo, repo_path=repo_path,
                    vault_path=vault_path, status="error")

    if not repo_path.is_file():
        result.detail = f"repo ausente ou nao regular: {repo_path}"
        return result

    try:
        repo_text = repo_path.read_text(encoding="utf-8")
        repo_parsed = validate_ownership(repo_text, mirror, side="repo")
    except (DocumentError, OSError) as exc:
        result.detail = str(exc)
        return result

    existing = None
    if vault_path.exists():
        if not vault_path.is_file():
            result.detail = f"vault:{mirror.vault}: destino nao regular"
            return result
        try:
            mirror_text = vault_path.read_text(encoding="utf-8")
            existing = validate_ownership(mirror_text, mirror, side="vault").ownership
        except (DocumentError, OSError) as exc:
            result.detail = str(exc)
            return result
        result.findings.extend(
            f"vault: {f}" for f in duplication_findings(mirror_text,
                                                         repo_parsed.body))

    target = build_mirror(repo_parsed, mirror, existing)
    findings = duplication_findings(target, repo_parsed.body)
    if findings:
        result.status = "error"
        result.detail = "validacao do resultado falhou"
        result.findings.extend(f"resultado: {f}" for f in findings)
        return result

    try:
        current = (vault_path.read_text(encoding="utf-8")
                   if vault_path.exists() else None)
    except OSError as exc:
        result.detail = f"falha ao reler destino: {exc}"
        return result
    if current == target:
        result.status = "in_sync"
        result.detail = "conteudo identico"
        return result

    if not write or dry_run:
        result.status = "would_update"
        result.detail = "espelho divergente do repo"
        return result

    backup_dir = vault_path.parent / ".sync_vault_backups"
    backup = backup_dir / f"{vault_path.name}.bak"
    try:
        atomic_write(vault_path, target, backup=backup)
    except OSError as exc:
        result.detail = f"falha de escrita: {exc}"
        return result
    result.status = "updated"
    result.detail = f"espelho atualizado (backup em {backup})"
    return result


def select(keys: Optional[list[str]], *, all_docs: bool) -> list[Mirror]:
    """Selecao explicita (§16).

    ``--check`` sem ``--sync`` cobre todos os documentos do mapping: e a
    verificacao de rotina. ``--sync-all`` tambem. Com ``--sync DOC``, apenas os
    documentos pedidos sao tocados.
    """
    if all_docs:
        return list(MIRRORS)
    chosen: list[Mirror] = []
    for key in keys or []:
        mirror = _lookup(key)
        if mirror is not None:
            chosen.append(mirror)
    return chosen


def _lookup(key: str) -> Optional[Mirror]:
    for candidate in (key, f"{key}.md", f"docs/{key}.md"):
        if candidate in MIRRORS_BY_KEY:
            return MIRRORS_BY_KEY[candidate]
        if candidate in MIRRORS_BY_VAULT:
            return MIRRORS_BY_VAULT[candidate]
    return None


def unmapped(repo_root: Path) -> list[str]:
    """Docs do repo com bloco de ownership e sem par no mapping.

    Conta blocos de ownership de verdade (`ownership_blocks`), nao busca por
    substring: a documentacao do proprio tooling cita o marker na prosa e
    geraria falso positivo.
    """
    orphans: list[str] = []
    mapped_basenames = {Path(m.repo).name for m in MIRRORS}
    for path in sorted(repo_root.glob("docs/*.md")):
        if path.name in mapped_basenames:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if ownership_blocks(text):
            orphans.append(str(path.relative_to(repo_root)))
    return orphans


def render_report(results: list[Result], orphans: list[str]) -> str:
    icons = {"in_sync": "=", "updated": "+", "would_update": "~", "error": "!"}
    out: list[str] = []
    for r in results:
        icon = icons.get(r.status, "?")
        out.append(f"  [{icon}] {r.key:34s} -> {r.vault_path.name:44s} "
                   f"{r.status}")
        if r.detail:
            out.append(f"      {r.detail}")
        for finding in r.findings:
            out.append(f"      ! {finding}")
    if orphans:
        out.append("")
        out.append("  docs do repo com ownership mas SEM par no mapping "
                   "(nao sincronizados):")
        for o in orphans:
            out.append(f"    - {o}")
    return "\n".join(out)


def _prevalidate_batch(mirrors: list[Mirror], vault_root: Path) -> list[Result]:
    """Valida todo o lote sem I/O de escrita antes de `--sync-all`."""
    return [plan_mirror(m, REPO_ROOT, vault_root, write=False, dry_run=True)
            for m in mirrors]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync repo -> vault (repo e owner, vault e mirror).")
    parser.add_argument("--check", action="store_true",
                        help="compara e reporta; nunca escreve")
    parser.add_argument("--sync", metavar="DOC", action="append",
                        help="sincroniza um documento (repo path, nome ou "
                             "nome do espelho); repetivel")
    parser.add_argument("--sync-all", action="store_true",
                        help="sincroniza todos os documentos do mapping")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra o que mudaria sem escrever")
    parser.add_argument("--vault", metavar="DIR",
                        help="raiz do vault (default: Obsidian vault do usuario)")
    args = parser.parse_args(argv)

    if not (args.check or args.sync or args.sync_all):
        parser.error("informe --check, --sync DOC ou --sync-all")

    vault_root = resolve_vault_root(args.vault)
    # `--check` domina: e read-only por definicao, e reporta divergencia como
    # exit != 0 mesmo que `--sync` tambem esteja na linha de comando.
    write = bool(args.sync or args.sync_all) and not args.check
    dry_run = args.dry_run or args.check
    mirrors = select(args.sync,
                     all_docs=args.sync_all or (args.check and not args.sync))
    if write and not mirrors:
        print("nenhum documento reconhecido; use --sync com um nome do "
              "mapping ou --sync-all", file=sys.stderr)
        return 2

    # `--sync-all` nao tem rollback global. Antes da primeira escrita, entretanto,
    # todo o lote passa pela mesma validacao de source/destino/ownership. Cada
    # escrita revalida novamente em `plan_mirror`, reduzindo a janela de corrida.
    if write and not dry_run and args.sync_all:
        preflight = _prevalidate_batch(mirrors, vault_root)
        invalid = [r for r in preflight if r.status == "error"]
        if invalid:
            orphans = unmapped(REPO_ROOT)
            print(f"vault: {vault_root}")
            print(render_report(preflight, orphans))
            print(f"\npre-validacao falhou em {len(invalid)} documento(s); "
                  "nenhum espelho foi escrito.", file=sys.stderr)
            return 1

    results = [plan_mirror(m, REPO_ROOT, vault_root, write=write,
                           dry_run=dry_run) for m in mirrors]
    orphans = unmapped(REPO_ROOT)

    print(f"vault: {vault_root}")
    print(render_report(results, orphans))

    failed = [r for r in results if r.status == "error"]
    diverged = [r for r in results if r.status == "would_update"]
    if failed:
        updated = [r for r in results if r.status == "updated"]
        if updated:
            print(f"\nsync parcial: {len(updated)} documento(s) atualizado(s), "
                  f"{len(failed)} com erro. Restaure, se necessario, os backups "
                  "em <vault>/.sync_vault_backups/ e rode --check.",
                  file=sys.stderr)
        else:
            print(f"\n{len(failed)} documento(s) com erro — nada escrito para "
                  f"esses.", file=sys.stderr)
        return 1
    if args.check and diverged:
        # exit != 0 e especifico de --check; --sync e --dry-run reportam
        # sem transformar divergencia em falha.
        print(f"\n{len(diverged)} documento(s) divergente(s); "
              f"--check não escreve. Use --sync para escrever.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verifica as referências de ``docs/EMBASAMENTO-CIENTIFICO.md``.

Duas camadas:

* **offline** (``--offline``): estrutura do documento. Toda entrada tem autor,
  ano e título; PMID/DOI são únicos e bem formados; toda citação do corpo
  resolve para uma entrada; a matriz de rastreabilidade tem as quatro colunas.
* **online** (padrão): resolve cada PMID no NCBI E-utilities e cada DOI no
  Crossref, comparando título, primeiro autor e ano com o que o documento
  declara. É a camada que pega link trocado — o modo de falha que uma revisão
  manual de formato não pega.

O script não altera o documento. Use ``--json`` para um relatório consumível e
``--refresh`` para ignorar o cache local. A rede é opcional: o suite de PR roda
apenas a camada offline; o workflow ``references`` roda a resolução semanal.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOC = REPO_ROOT / "docs" / "EMBASAMENTO-CIENTIFICO.md"
DEFAULT_CACHE = REPO_ROOT / ".cache" / "references.json"
USER_AGENT = (
    "hermes-coach-reference-check/1.0 "
    "(https://github.com/valdelin/Hermes-coach; mailto:hermes-coach@users.noreply.github.com)"
)

REF_HEADING_RE = re.compile(r"^## \d+\. Referências\s*$", re.M)
MATRIX_HEADING_RE = re.compile(
    r"^## \d+\. Matriz de rastreabilidade por feature\s*$", re.M
)
ENTRY_START_RE = re.compile(r"^(?P<number>\d+)\.\s+\*\*", re.M)
ENTRY_META_RE = re.compile(
    r"^(?P<number>\d+)\.\s+\*\*(?P<author>[^\n]+?)\s*"
    r"\((?P<year>\d{4})\)\.\*\*\s+\*(?P<title>[^\n]+?)\*",
    re.M,
)
PMID_RE = re.compile(r"PMID\s+(\d{7,9})")
# DOI pode conter parênteses balanceados (ex.: 10.1016/S1440-2440(09)60004-9),
# por isso o delimitador é o fim do link/ângulo, não o primeiro ')'.
DOI_RE = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.[^\s<>]+)")
URL_RE = re.compile(r"https?://[^\s<>),]+")
BRACKET_REF_RE = re.compile(r"\[(\d{1,2})\]")
PMID_LIMIT = 4_294_967_295

NCBI_URL = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    "?db=pubmed&retmode=json&id={pmid}"
)
CROSSREF_URL = "https://api.crossref.org/works/{doi}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_text(value: str) -> str:
    """Normaliza para comparação: sem acento, caixa, HTML ou pontuação."""

    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def title_similarity(declared: str, fetched: str) -> float:
    return difflib.SequenceMatcher(
        None, normalize_text(declared), normalize_text(fetched)
    ).ratio()


def title_level(declared: str, fetched: str) -> tuple[str, float]:
    """Classifica o título sem punir subtítulo truncado pela fonte.

    O Crossref às vezes guarda só o título principal (sem "Part I: ..."). Se o
    título retornado é um prefixo substancial do declarado, é a mesma obra; a
    similaridade textual pura rebaixaria esse caso para warning.
    """

    declared_norm = normalize_text(declared)
    fetched_norm = normalize_text(fetched)
    if not fetched_norm:
        return "fail", 0.0
    similarity = title_similarity(declared, fetched)
    if declared_norm == fetched_norm:
        return "ok", 1.0
    prefix = declared_norm.startswith(fetched_norm) or fetched_norm.startswith(
        declared_norm
    )
    if prefix and min(len(declared_norm), len(fetched_norm)) >= 0.6 * max(
        len(declared_norm), len(fetched_norm)
    ):
        return "ok", similarity
    return (
        ("ok", similarity)
        if similarity >= 0.82
        else ("warn", similarity)
        if similarity >= 0.65
        else ("fail", similarity)
    )


@dataclasses.dataclass(frozen=True)
class Reference:
    number: int
    author: str
    year: int
    title: str
    pmid: str | None
    doi: str | None
    url: str | None
    block: str

    @property
    def first_author(self) -> str:
        """Sobrenome declarado, antes da vírgula ou do separador institucional."""

        return re.split(r",| / | et al", self.author)[0].strip().rstrip(".")

    @property
    def person_author(self) -> bool:
        # As entradas do Intervals.icu são institucionais; não há sobrenome.
        return not self.first_author.casefold().startswith("intervals")


@dataclasses.dataclass
class Finding:
    level: str  # ok | warn | fail
    reference: int | None
    source: str
    field: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def split_document(text: str) -> tuple[str, str]:
    match = REF_HEADING_RE.search(text)
    if match is None:
        raise ValueError("seção '## N. Referências' não encontrada")
    return text[: match.start()], text[match.end() :]


def parse_references(text: str) -> tuple[str, str, list[Reference]]:
    """Extrai corpo e entradas numeradas. O número é a chave de citação."""

    body, refs_text = split_document(text)
    starts = [match.start() for match in ENTRY_START_RE.finditer(refs_text)]
    references: list[Reference] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(refs_text)
        block = refs_text[start:end]
        meta = ENTRY_META_RE.match(block)
        if meta is None:
            first_line = block.splitlines()[0] if block else ""
            raise ValueError(f"entrada de referência fora do formato: {first_line!r}")
        pmid_match = PMID_RE.search(block)
        doi_match = DOI_RE.search(block)
        url_match = URL_RE.search(block)
        references.append(
            Reference(
                number=int(meta.group("number")),
                author=meta.group("author").strip(),
                year=int(meta.group("year")),
                title=meta.group("title").strip(),
                pmid=pmid_match.group(1) if pmid_match else None,
                doi=doi_match.group(1).rstrip(".,;") if doi_match else None,
                url=url_match.group(0).rstrip(".,;") if url_match else None,
                block=block,
            )
        )
    return body, refs_text, references


def matrix_rows(text: str) -> list[list[str]]:
    """Linhas de dados da matriz de rastreabilidade (fora do cabeçalho)."""

    match = MATRIX_HEADING_RE.search(text)
    if match is None:
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^## ", section, re.M)
    if next_heading:
        section = section[: next_heading.start()]
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4:
            continue
        if set(cells[0]) <= {"-", ":", " "}:
            continue
        if cells[0].casefold().startswith("feature"):
            continue
        rows.append(cells)
    return rows


def offline_findings(body: str, refs_text: str, references: list[Reference]) -> list[Finding]:
    findings: list[Finding] = []

    def fail(ref: int | None, field: str, message: str) -> None:
        findings.append(Finding("fail", ref, "offline", field, message))

    def ok(ref: int | None, field: str, message: str) -> None:
        findings.append(Finding("ok", ref, "offline", field, message))

    if not references:
        fail(None, "entradas", "nenhuma referência numerada encontrada")
        return findings

    numbers = [ref.number for ref in references]
    if numbers != list(range(1, len(numbers) + 1)):
        fail(None, "numeração", f"numeração não sequencial: {numbers}")
    else:
        ok(None, "numeração", f"{len(numbers)} entradas numeradas em sequência")

    seen_pmids: dict[str, int] = {}
    seen_dois: dict[str, int] = {}
    for ref in references:
        if not ref.title or len(ref.title) < 8:
            fail(ref.number, "título", "título ausente ou curto demais")
        if not ref.author:
            fail(ref.number, "autor", "autor ausente")
        if not (1900 <= ref.year <= 2100):
            fail(ref.number, "ano", f"ano implausível: {ref.year}")

        if ref.pmid:
            if int(ref.pmid) > PMID_LIMIT:
                fail(ref.number, "PMID", f"PMID fora do limite de 32 bits: {ref.pmid}")
            if ref.pmid in seen_pmids:
                fail(
                    ref.number,
                    "PMID",
                    f"PMID {ref.pmid} repetido (também na entrada {seen_pmids[ref.pmid]})",
                )
            seen_pmids[ref.pmid] = ref.number
        if ref.doi:
            if not ref.doi.startswith("10.") or " " in ref.doi:
                fail(ref.number, "DOI", f"DOI mal formado: {ref.doi}")
            if ref.doi in seen_dois:
                fail(
                    ref.number,
                    "DOI",
                    f"DOI {ref.doi} repetido (também na entrada {seen_dois[ref.doi]})",
                )
            seen_dois[ref.doi] = ref.number

    # Toda citação do corpo resolve para uma entrada.
    cited_pmids = set(PMID_RE.findall(body))
    known_pmids = {ref.pmid for ref in references if ref.pmid}
    for pmid in sorted(cited_pmids - known_pmids):
        fail(None, "citação", f"PMID {pmid} citado no corpo sem entrada de referência")

    cited_numbers = {int(number) for number in BRACKET_REF_RE.findall(body)}
    known_numbers = set(numbers)
    for number in sorted(cited_numbers - known_numbers):
        fail(None, "citação", f"referência [{number}] citada sem entrada")

    # Nenhuma entrada órfã: aparece no corpo por PMID ou por [n].
    for ref in references:
        by_pmid = bool(ref.pmid and ref.pmid in cited_pmids)
        by_number = ref.number in cited_numbers
        if not (by_pmid or by_number):
            fail(
                ref.number,
                "citação",
                f"entrada órfã: {ref.first_author} {ref.year} não é citado no corpo",
            )
    if not any(item.level == "fail" for item in findings):
        ok(None, "citações", "toda entrada é citada e toda citação tem entrada")

    # A matriz é o contrato de rastreabilidade: quatro colunas, limite explícito.
    rows = matrix_rows(body)
    if not rows:
        fail(None, "matriz", "matriz de rastreabilidade ausente ou sem linhas")
    else:
        ok(None, "matriz", f"{len(rows)} linhas de rastreabilidade")
        for index, row in enumerate(rows, start=1):
            feature, method, source, limit = row
            if not feature or not method or not source:
                fail(None, "matriz", f"linha {index} com célula vazia")
            if len(limit) < 40:
                fail(
                    None,
                    "matriz",
                    f"linha {index} ({feature}) sem limite explícito do que a fonte não mostra",
                )
            for number in BRACKET_REF_RE.findall(source):
                if int(number) not in known_numbers:
                    fail(
                        None,
                        "matriz",
                        f"linha {index} cita [{number}], que não existe na lista",
                    )
        if not any(
            word in body.casefold()
            for word in ("não mostra", "nao mostra", "não demonstra", "nao demonstra")
        ):
            fail(None, "matriz", "coluna de limite não declara 'não mostra'/'não demonstra'")
        else:
            ok(None, "matriz", "coluna de limite explícita")

    return findings


class JsonCache:
    def __init__(self, path: Path, ttl_days: int, refresh: bool = False) -> None:
        self.path = path
        self.ttl_seconds = ttl_days * 86_400
        self.refresh = refresh
        self.data: dict[str, Any] = {}
        if path.exists() and not refresh:
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.data = {}

    def get(self, key: str) -> Any | None:
        entry = self.data.get(key)
        if not isinstance(entry, dict):
            return None
        fetched_at = entry.get("fetched_at", 0)
        if self.refresh or time.time() - fetched_at > self.ttl_seconds:
            return None
        return entry.get("data")

    def put(self, key: str, data: Any) -> None:
        self.data[key] = {"fetched_at": time.time(), "data": data}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def fetch_json(url: str, *, timeout: float, retries: int) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code in (400, 401, 403, 404):
                raise
            last_error = error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        if attempt < retries:
            time.sleep(1.5 * attempt)
    raise RuntimeError(f"falha após {retries} tentativas em {url}: {last_error}")


def pubmed_metadata(pmid: str, *, cache: JsonCache, timeout: float, retries: int) -> dict[str, Any]:
    url = NCBI_URL.format(pmid=pmid)
    cached = cache.get(url)
    if cached is not None:
        return cached
    payload = fetch_json(url, timeout=timeout, retries=retries)
    result = (payload.get("result") or {}).get(pmid) or {}
    if result.get("error"):
        raise RuntimeError(f"NCBI recusou PMID {pmid}: {result['error']}")
    authors = [
        item.get("name", "")
        for item in result.get("authors", [])
        if item.get("name")
    ]
    data = {
        "title": result.get("title", ""),
        "authors": authors,
        "year": result.get("pubdate", ""),
        "epubdate": result.get("epubdate", ""),
        "sortpubdate": result.get("sortpubdate", ""),
        "journal": result.get("source", ""),
    }
    cache.put(url, data)
    time.sleep(0.34)  # NCBI: no máximo 3 requisições/s sem API key.
    return data


def crossref_metadata(doi: str, *, cache: JsonCache, timeout: float, retries: int) -> dict[str, Any]:
    url = CROSSREF_URL.format(doi=urllib.parse.quote(doi, safe="/"))
    cached = cache.get(url)
    if cached is not None:
        return cached
    payload = fetch_json(url, timeout=timeout, retries=retries)
    message = payload.get("message") or {}
    authors = []
    for item in message.get("author", []):
        family = item.get("family") or item.get("name") or ""
        given = item.get("given") or ""
        authors.append(f"{family} {given}".strip())
    titles = [title for title in message.get("title", []) if title]
    years = []
    for key in ("published-print", "published-online", "issued", "created"):
        parts = ((message.get(key) or {}).get("date-parts") or [[]])[0]
        if parts and parts[0]:
            years.append(str(parts[0]))
    data = {
        "title": titles[0] if titles else "",
        "authors": authors,
        "year": ",".join(years),
        "journal": (message.get("container-title") or [""])[0],
    }
    cache.put(url, data)
    time.sleep(0.12)
    return data


def years_in(value: str) -> set[int]:
    return {int(match) for match in re.findall(r"(?:19|20)\d{2}", value or "")}


def compare_metadata(
    reference: Reference,
    *,
    source: str,
    title: str,
    authors: Iterable[str],
    years: Iterable[str],
    identifier: str,
) -> list[Finding]:
    findings: list[Finding] = []
    label = f"{source} {identifier}"

    if reference.person_author:
        declared_author = normalize_text(reference.first_author)
        author_names = [normalize_text(name) for name in authors if name]
        author_ok = any(
            declared_author
            and (declared_author in name or name.startswith(declared_author))
            for name in author_names
        )
        if not author_ok:
            findings.append(
                Finding(
                    "fail",
                    reference.number,
                    label,
                    "autor",
                    f"declarado {reference.first_author!r}; retornado {author_names!r}",
                )
            )
        else:
            findings.append(
                Finding(
                    "ok",
                    reference.number,
                    label,
                    "autor",
                    f"{reference.first_author}",
                )
            )

    fetched_years: set[int] = set()
    for value in years:
        fetched_years |= years_in(value)
    if not fetched_years:
        findings.append(
            Finding("warn", reference.number, label, "ano", "fonte sem ano legível")
        )
    elif reference.year in fetched_years:
        findings.append(
            Finding("ok", reference.number, label, "ano", str(reference.year))
        )
    else:
        distance = min(abs(reference.year - year) for year in fetched_years)
        level = "warn" if distance <= 1 else "fail"
        findings.append(
            Finding(
                level,
                reference.number,
                label,
                "ano",
                f"declarado {reference.year}; retornado {sorted(fetched_years)}",
            )
        )

    if not title:
        findings.append(
            Finding("fail", reference.number, label, "título", "fonte sem título")
        )
    else:
        level, similarity = title_level(reference.title, title)
        findings.append(
            Finding(
                level,
                reference.number,
                label,
                "título",
                f"similaridade {similarity:.2f} com {title!r}",
            )
        )
    return findings


def online_findings(
    references: list[Reference],
    *,
    cache: JsonCache,
    timeout: float,
    retries: int,
) -> list[Finding]:
    findings: list[Finding] = []
    for ref in references:
        if ref.pmid:
            try:
                data = pubmed_metadata(
                    ref.pmid, cache=cache, timeout=timeout, retries=retries
                )
            except Exception as error:  # noqa: BLE001 - o relatório precisa da falha
                findings.append(
                    Finding(
                        "fail",
                        ref.number,
                        f"PMID {ref.pmid}",
                        "resolução",
                        str(error),
                    )
                )
            else:
                findings.extend(
                    compare_metadata(
                        ref,
                        source="PMID",
                        title=data.get("title", ""),
                        authors=data.get("authors", []),
                        years=[data.get("year", ""), data.get("epubdate", ""),
                               data.get("sortpubdate", "")],
                        identifier=ref.pmid,
                    )
                )
        if ref.doi:
            try:
                data = crossref_metadata(
                    ref.doi, cache=cache, timeout=timeout, retries=retries
                )
            except Exception as error:  # noqa: BLE001
                findings.append(
                    Finding(
                        "fail",
                        ref.number,
                        f"DOI {ref.doi}",
                        "resolução",
                        str(error),
                    )
                )
            else:
                findings.extend(
                    compare_metadata(
                        ref,
                        source="DOI",
                        title=data.get("title", ""),
                        authors=data.get("authors", []),
                        years=[data.get("year", "")],
                        identifier=ref.doi,
                    )
                )
    return findings


def print_findings(findings: list[Finding]) -> None:
    for item in findings:
        if item.level == "ok":
            continue
        reference = f"[{item.reference}]" if item.reference is not None else "[-]"
        print(f"{reference:>5} {item.source:<28} {item.level.upper():<4} "
              f"{item.field}: {item.message}")


def summarize(references: list[Reference], findings: list[Finding]) -> dict[str, int]:
    with_pmid = sum(1 for ref in references if ref.pmid)
    with_doi = sum(1 for ref in references if ref.doi)
    return {
        "referencias": len(references),
        "com_pmid": with_pmid,
        "com_doi": with_doi,
        "sem_identificador": sum(
            1 for ref in references if not ref.pmid and not ref.doi
        ),
        "ok": sum(1 for item in findings if item.level == "ok"),
        "warn": sum(1 for item in findings if item.level == "warn"),
        "fail": sum(1 for item in findings if item.level == "fail"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="só valida estrutura; não faz chamadas de rede",
    )
    parser.add_argument(
        "--only",
        default="",
        help="filtra por número, PMID ou DOI (lista separada por vírgula)",
    )
    parser.add_argument("--strict", action="store_true", help="warning também falha")
    parser.add_argument("--json", action="store_true", help="imprime relatório JSON")
    parser.add_argument("--refresh", action="store_true", help="ignora o cache")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--cache-ttl-days", type=int, default=14)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = args.doc.read_text(encoding="utf-8")
    body, refs_text, references = parse_references(text)

    selected = references
    if args.only:
        tokens = {token.strip() for token in args.only.split(",") if token.strip()}
        selected = [
            ref
            for ref in references
            if str(ref.number) in tokens or ref.pmid in tokens or ref.doi in tokens
        ]
        if not selected:
            print(f"nenhuma referência corresponde a --only {args.only!r}", file=sys.stderr)
            return 2

    findings = offline_findings(body, refs_text, references)
    if not args.offline:
        cache = JsonCache(args.cache, args.cache_ttl_days, refresh=args.refresh)
        findings.extend(
            online_findings(
                selected, cache=cache, timeout=args.timeout, retries=args.retries
            )
        )
        cache.save()

    summary = summarize(selected, findings)
    if args.json:
        print(
            json.dumps(
                {
                    "generated_at": utc_now(),
                    "document": str(args.doc),
                    "summary": summary,
                    "findings": [item.as_dict() for item in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_findings(findings)
        print(
            f"\n{summary['referencias']} referências "
            f"({summary['com_pmid']} com PMID, {summary['com_doi']} com DOI, "
            f"{summary['sem_identificador']} sem identificador indexado)."
        )
        print(
            f"Verificações: {summary['ok']} OK, {summary['warn']} warning, "
            f"{summary['fail']} falha."
        )

    if summary["fail"]:
        return 1
    if args.strict and summary["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

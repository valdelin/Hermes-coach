"""Contrato do `insight`: o que o LLM pode devolver ao atleta.

O LLM **nao decide** nada. Ele recebe os numeros ja decididos pelo motor
deterministico e devolve um unico objeto JSON valido neste contrato. Quem
garante que o texto nao contradiz o motor sao os graders do harness
(`ai-lab/adapters/cycling-coach/graders.py`), nao o prompt.

Regras do modulo 1 (contrato de prompt):
1. o schema de saida e o contrato; o prompt nao pode ampliá-lo;
2. a versao do prompt e pinada junto com o hash (trocar prompt = versao nova);
3. o contrato e validado **offline**, sem chave de API.
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

PROMPT_VERSION = "0.1.0"

FOCOS = ("recovery", "easy", "z2", "vo2", "ss", "rest")
INTENSIDADES = ("casual", "moderada", "alta")

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["foco", "duracao_min", "intensidade", "acao", "alerta"],
    "properties": {
        "foco": {"enum": list(FOCOS)},
        "duracao_min": {"type": "integer", "minimum": 0, "maximum": 480},
        "intensidade": {"enum": list(INTENSIDADES)},
        "acao": {"type": "string", "minLength": 1, "maxLength": 240},
        "alerta": {"type": ["string", "null"], "maxLength": 240},
    },
}

PROMPT_PATH = Path(__file__).with_name("prompt.md")


def prompt_hash():
    """Hash do prompt corrente. Entra no registro junto com a versao: sem
    hash, `PROMPT_VERSION` nao distingue dois prompts com o mesmo numero."""
    if not PROMPT_PATH.exists():
        return None
    return hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()[:12]


def registry_entry(model=None):
    """Linha do registro de prompt: versao + hash + modelo pinado."""
    return {
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": prompt_hash(),
        "model": model,
    }


@dataclass(frozen=True)
class InsightContext:
    """O que entra no prompt. Tudo aqui vem do motor deterministico —
    o LLM nao recebe (nem inventa) nenhum outro numero.

    `raw` e o texto entregue ao modelo (a superficie onde numeros
    aparecem); os graders leem ele para conferir que o texto da acao so
    usa numeros que existem aqui.
    """
    foco_motor: str
    tl_duracao_min: int
    tsb: float
    ctl: float
    atl: float
    raw: str = field(repr=False, default="")

    def as_prompt_data(self):
        return {
            "foco_do_motor": self.foco_motor,
            "duracao_plano_min": self.tl_duracao_min,
            "tsb": round(self.tsb, 1),
            "ctl": round(self.ctl, 1),
            "atl": round(self.atl, 1),
        }


def contract_errors(payload, ctx=None):
    """Erros de **contrato** (o que o schema proibe). Deliberadamente nao
    inclui as invariantes semanticas — essas sao dos graders.

    Retorna lista de strings; vazia = contrato ok.
    """
    errors = []
    if not isinstance(payload, dict):
        return ["payload nao e objeto"]

    for key in SCHEMA["required"]:
        if key not in payload:
            errors.append(f"campo obrigatorio ausente: {key}")

    unknown = set(payload) - set(SCHEMA["properties"])
    if unknown:
        errors.append(f"campos fora do contrato: {sorted(unknown)}")

    foco = payload.get("foco")
    if foco is not None and foco not in FOCOS:
        errors.append(f"foco invalido: {foco!r}")

    dur = payload.get("duracao_min")
    if not isinstance(dur, int) or isinstance(dur, bool) or not 0 <= dur <= 480:
        errors.append(f"duracao_min invalida: {dur!r}")

    intensidade = payload.get("intensidade")
    if intensidade is not None and intensidade not in INTENSIDADES:
        errors.append(f"intensidade invalida: {intensidade!r}")

    acao = payload.get("acao")
    if acao is not None and not (1 <= len(acao) <= 240):
        errors.append("acao fora do tamanho (1..240)")

    alerta = payload.get("alerta")
    if alerta is not None and len(alerta) > 240:
        errors.append("alerta acima de 240 chars")

    return errors


def dumps(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)

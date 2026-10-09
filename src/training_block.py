"""Boundary persistida do bloco de treino, sem policy de fase ou prescricao."""
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional


BLOCK_CONTEXT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BlockContext:
    """Identidade do bloco ativo e o objetivo capturado no seu inicio.

    O contexto e propositalmente pequeno: duracao, fase, criterios de transicao
    e FTP pertencem a contratos futuros. `started_on` vem do chamador para que
    a fronteira seja deterministica e auditavel.
    """

    id: str
    started_on: str
    goal: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("block context id deve ser texto nao vazio")
        if not isinstance(self.started_on, str):
            raise ValueError("block context started_on deve ser YYYY-MM-DD")
        try:
            date.fromisoformat(self.started_on)
        except ValueError as exc:
            raise ValueError("block context started_on deve ser YYYY-MM-DD") from exc
        if self.goal is not None and (not isinstance(self.goal, str) or not self.goal):
            raise ValueError("block context goal deve ser texto ou None")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": BLOCK_CONTEXT_SCHEMA_VERSION, "id": self.id,
                "started_on": self.started_on, "goal": self.goal}

    @classmethod
    def from_dict(cls, data: Any) -> "BlockContext":
        if not isinstance(data, dict):
            raise ValueError("block context deve ser objeto")
        if data.get("schema_version") != BLOCK_CONTEXT_SCHEMA_VERSION:
            raise ValueError("schema de block context nao suportado")
        return cls(id=data.get("id"), started_on=data.get("started_on"),
                   goal=data.get("goal"))

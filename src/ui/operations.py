"""Contrato fechado para operações da TUI via facade Hermes Agent."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
FACADE = "scripts/hermes_agent.py"


class OperationName(str, Enum):
    BUILD = "build"
    CHECK = "check"
    RECONCILE = "reconcile"
    PUSH = "push"


@dataclass(frozen=True)
class OperationSpec:
    preview_argv: tuple[str, ...]
    apply_argv: tuple[str, ...]
    typed_confirmation: str | None = None


@dataclass(frozen=True)
class OperationResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


_OPERATIONS = {
    OperationName.BUILD: OperationSpec(
        preview_argv=("build", "--dry-run"),
        apply_argv=("build", "--yes"),
    ),
    OperationName.CHECK: OperationSpec(
        preview_argv=("check", "--dry-run"),
        apply_argv=("check", "--apply", "--yes"),
    ),
    OperationName.RECONCILE: OperationSpec(
        preview_argv=("reconcile", "--show"),
        apply_argv=("reconcile", "--yes"),
    ),
    OperationName.PUSH: OperationSpec(
        preview_argv=("publicar", "--dry-run"),
        apply_argv=("publicar", "--yes"),
        typed_confirmation="PUBLICAR",
    ),
}


def operation_spec(operation: OperationName) -> OperationSpec:
    return _OPERATIONS[operation]


class FacadeRunner:
    """Executa somente argv declarados, sem shell, na raiz do repositório."""

    def __init__(
        self,
        root: Path = ROOT,
        execute: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._root = root
        self._execute = execute

    def run(self, argv: Sequence[str]) -> OperationResult:
        logical_argv = tuple(argv)
        command = [sys.executable, FACADE, *logical_argv]
        try:
            completed = self._execute(
                command,
                cwd=str(self._root),
                shell=False,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            return OperationResult(logical_argv, 1, "", str(exc))
        return OperationResult(
            logical_argv,
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
        )

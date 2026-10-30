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


class OperationPhase(str, Enum):
    PREVIEW_READY = "preview_ready"
    FIRST_CONFIRM = "first_confirm"
    TYPED_CONFIRM = "typed_confirm"
    APPLYING = "applying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
        apply_argv=("--yes", "build"),
    ),
    OperationName.CHECK: OperationSpec(
        preview_argv=("check", "--dry-run"),
        apply_argv=("--yes", "check", "--apply"),
    ),
    OperationName.RECONCILE: OperationSpec(
        preview_argv=("reconcile", "--show"),
        apply_argv=("--yes", "reconcile"),
    ),
    OperationName.PUSH: OperationSpec(
        preview_argv=("push", "--dry-run"),
        apply_argv=("--yes", "push"),
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


class OperationFlow:
    """Máquina de estados que impede apply sem prévia e confirmação."""

    def __init__(self, operation: OperationName, runner: FacadeRunner) -> None:
        self.operation = operation
        self.spec = operation_spec(operation)
        self.runner = runner
        self.phase: OperationPhase | None = None
        self.result: OperationResult | None = None

    def preview(self) -> OperationResult:
        self.result = self.runner.run(self.spec.preview_argv)
        self.phase = (OperationPhase.PREVIEW_READY if self.result.succeeded
                      else OperationPhase.FAILED)
        return self.result

    def continue_after_preview(self) -> bool:
        if self.phase is not OperationPhase.PREVIEW_READY:
            return False
        self.phase = (OperationPhase.TYPED_CONFIRM if self.spec.typed_confirmation
                      else OperationPhase.FIRST_CONFIRM)
        return True

    def confirm_typed(self, value: str) -> bool:
        if self.phase is not OperationPhase.TYPED_CONFIRM:
            return False
        if value != self.spec.typed_confirmation:
            return False
        self.phase = OperationPhase.FIRST_CONFIRM
        return True

    def apply(self) -> OperationResult | None:
        if self.phase is not OperationPhase.FIRST_CONFIRM:
            return None
        self.phase = OperationPhase.APPLYING
        self.result = self.runner.run(self.spec.apply_argv)
        self.phase = (OperationPhase.SUCCEEDED if self.result.succeeded
                      else OperationPhase.FAILED)
        return self.result

    def cancel(self) -> None:
        if self.phase is not OperationPhase.APPLYING:
            self.phase = OperationPhase.CANCELLED

"""Modal protegido para executar operações pela facade Hermes Agent."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual.worker import Worker, WorkerState

from ..operations import FacadeRunner, OperationFlow, OperationName, OperationPhase


class OperationModal(ModalScreen[bool]):
    """Mostra prévia, confirmação e resultado sem bloquear a TUI."""

    CSS = """
    OperationModal { align: center middle; }
    #operation-dialog { width: 90%; height: 85%; border: round $accent; background: $surface; padding: 1 2; }
    #operation-output { height: 1fr; border: round $panel; padding: 1; }
    #operation-actions { height: 3; layout: horizontal; }
    #operation-token { display: none; }
    """

    def __init__(self, operation: OperationName, on_success: Callable[[], None] | None = None,
                 runner: FacadeRunner | None = None):
        super().__init__()
        self._flow = OperationFlow(operation, runner or FacadeRunner())
        self._on_success = on_success
        self._worker = None

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Label(f"OPERAÇÃO: {self._flow.operation.value.upper()}", id="operation-title"),
            Label("Executando prévia...", id="operation-status"),
            Static("", id="operation-output"),
            Input(placeholder="Digite PUBLICAR", id="operation-token"),
            Button("Cancelar", id="operation-cancel"),
            Button("Continuar", id="operation-continue", disabled=True),
            Button("Aplicar", id="operation-apply", disabled=True),
            id="operation-dialog",
        )

    def on_mount(self) -> None:
        self._run_preview()

    def _run_preview(self) -> None:
        self._worker = self.run_worker(self._flow.preview, thread=True, exclusive=True, exit_on_error=False)

    def _run_apply(self) -> None:
        self.query_one("#operation-cancel", Button).disabled = True
        self._worker = self.run_worker(self._flow.apply, thread=True, exclusive=True, exit_on_error=False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._worker or event.state is not WorkerState.SUCCESS:
            return
        self._render_result()

    def _render_result(self) -> None:
        result = self._flow.result
        output = self._format_output(result)
        self.query_one("#operation-output", Static).update(output)
        status = self.query_one("#operation-status", Label)
        if self._flow.phase is OperationPhase.PREVIEW_READY:
            status.update("Prévia concluída. Revise a saída antes de continuar.")
            self.query_one("#operation-continue", Button).disabled = False
            self.query_one("#operation-cancel", Button).disabled = False
        elif self._flow.phase is OperationPhase.SUCCEEDED:
            status.update("Operação concluída.")
            try:
                self._complete_success()
            finally:
                self.query_one("#operation-cancel", Button).disabled = False
        else:
            status.update(f"Operação falhou (exit {result.returncode if result else 'desconhecido'}).")
            self.query_one("#operation-cancel", Button).disabled = False

    def _format_output(self, result) -> str:
        command = " ".join(result.argv) if result else ""
        output = "\n".join(part for part in (result.stdout, result.stderr) if part) if result else ""
        return f"$ hermes_agent.py {command}\nexit code: {result.returncode if result else 'desconhecido'}\n\n{output or 'Saída vazia.'}"

    def _complete_success(self) -> None:
        if self._on_success:
            self._on_success()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "operation-cancel":
            phase = self._flow.phase
            if phase in (OperationPhase.APPLYING, OperationPhase.PREVIEW_READY) is False and phase is None:
                # If preview hasn't completed yet, block closing
                worker = getattr(self, "_worker", None)
                if worker is not None and getattr(worker, "is_running", False):
                    return
            if phase is OperationPhase.APPLYING:
                return
            if phase is None:
                # Still running preview
                worker = getattr(self, "_worker", None)
                if worker is not None and getattr(worker, "is_running", False):
                    return
            self._flow.cancel()
            self.dismiss(False)
        elif button_id == "operation-continue" and self._flow.continue_after_preview():
            if self._flow.phase is OperationPhase.TYPED_CONFIRM:
                self.query_one("#operation-token", Input).styles.display = "block"
            else:
                self.query_one("#operation-apply", Button).disabled = False
        elif button_id == "operation-apply":
            if self._flow.phase is OperationPhase.FIRST_CONFIRM:
                event.button.disabled = True
                self._run_apply()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "operation-token":
            if self._flow.confirm_typed(event.value):
                self.query_one("#operation-apply", Button).disabled = False

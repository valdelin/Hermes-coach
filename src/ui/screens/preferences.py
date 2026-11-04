"""Tela de Preferências - Dias disponíveis para treino."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from ... import preferences


class PreferencesScreen(Screen):
    CSS = """
    PreferencesScreen {
        background: $surface;
    }

    #header {
        height: 3;
        padding: 0 2;
        align: center middle;
        background: $boost;
    }

    #title {
        text-style: bold;
    }

    #content {
        height: 1fr;
        padding: 2 4;
    }

    .section {
        text-style: bold;
        padding: 1 0;
    }

    .days {
        layout: horizontal;
        height: 3;
    }

    .day-btn {
        width: 1fr;
        margin: 0 1;
    }

    .day-btn.active {
        background: $success;
    }

    .long-days {
        layout: horizontal;
        height: 3;
    }

    .long-btn {
        width: 1fr;
        margin: 0 1;
    }

    .long-btn.active {
        background: $accent;
    }

    .hint {
        color: $text-muted;
        padding: 1 0;
    }

    .actions {
        layout: horizontal;
        padding: 2 0;
    }

    .actions Button {
        margin-right: 2;
    }
    """

    BINDINGS = [
        ("escape", "back", "Voltar"),
        ("s", "save", "Salvar"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.selected = set(preferences.load_training_days())
        self.long_day = preferences.load_preferred_long_day()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="header"):
            yield Label("PREFERÊNCIAS", id="title")
        with Vertical(id="content"):
            yield Label("Dias disponíveis para treino", classes="section")
            with Horizontal(classes="days"):
                for label, weekday in preferences.DAY_LABELS:
                    yield Button(label, id=f"day_{weekday}", classes="day-btn" + (" active" if weekday in self.selected else ""))
            yield Static("Marque os dias em que você tem disponibilidade para treinar. O plano considerará apenas estes dias.", classes="hint")
            yield Label("Dia preferido para treino longo", classes="section")
            with Horizontal(classes="long-days"):
                for label, weekday in preferences.DAY_LABELS:
                    yield Button(label, id=f"long_{weekday}", classes="long-btn" + (" active" if self.long_day == weekday else ""))
                yield Button("Nenhum", id="long_none", classes="long-btn" + (" active" if self.long_day is None else ""))
            yield Static("Se marcado, o plano tentará colocar o treino mais longo neste dia (quando possível).", classes="hint")
            with Horizontal(classes="actions"):
                yield Button("Salvar (s)", id="btn_save", variant="primary")
                yield Button("Cancelar (Esc)", id="btn_cancel")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_buttons()
        self._refresh_long_buttons()

    def _refresh_buttons(self) -> None:
        for label, weekday in preferences.DAY_LABELS:
            try:
                btn = self.query_one(f"#day_{weekday}", Button)
                if weekday in self.selected:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass

    def _refresh_long_buttons(self) -> None:
        for label, weekday in preferences.DAY_LABELS:
            try:
                btn = self.query_one(f"#long_{weekday}", Button)
                if self.long_day == weekday:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except Exception:
                pass
        try:
            btn = self.query_one("#long_none", Button)
            if self.long_day is None:
                btn.add_class("active")
            else:
                btn.remove_class("active")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn_save":
            self.action_save()
            return
        if btn_id == "btn_cancel":
            self.action_back()
            return
        if btn_id.startswith("day_"):
            try:
                weekday = int(btn_id.split("_")[1])
                if weekday in self.selected:
                    self.selected.discard(weekday)
                else:
                    self.selected.add(weekday)
                self._refresh_buttons()
            except Exception:
                pass
            return
        if btn_id.startswith("long_"):
            if btn_id == "long_none":
                self.long_day = None
            else:
                try:
                    self.long_day = int(btn_id.split("_")[1])
                except Exception:
                    self.long_day = None
            self._refresh_long_buttons()
            return

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        try:
            preferences.save_training_days(sorted(self.selected))
            preferences.save_preferred_long_day(self.long_day)
            self.app.pop_screen()
        except Exception:
            self.app.pop_screen()

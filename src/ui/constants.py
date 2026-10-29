# src/ui/constants.py
"""Constantes e configuração da interface TUI."""

APP_TITLE = "HERMES COACH"
APP_SUBTITLE = "Training Dashboard"

# Atalhos principais
BINDINGS_HELP = [
    ("1", "dashboard", "Dashboard"),
    ("2", "plan", "Plano Semanal"),
    ("3", "today", "Treino do Dia"),
    ("4", "publish", "Publicar"),
    ("g", "generate", "Gerar Plano"),
    ("r", "reconcile", "Reconciliar"),
    ("p", "publish", "Publicar"),
    ("q", "quit", "Sair"),
]

# Mensagens
MSG_NO_PLAN = "Nenhum plano encontrado. Pressione 'g' para gerar o plano."
MSG_LOADING = "Carregando..."

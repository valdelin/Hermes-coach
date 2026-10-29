# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ ARQUIVO COMENTADO: src/ui/constants.py                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# DESCRIÇÃO: Cópia didática do código da TUI local-first.
#
# Gerado em: 2026-10-29 19:44:17
#
# ATENÇÃO: CÓPIA PARA ESTUDO APENAS
# - Arquivo original: src/ui/constants.py (NÃO MODIFICADO)
# - Esta cópia contém APENAS cabeçalho explicativo adicionado no topo
# - Todo o código abaixo é IDÊNTICO ao original
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

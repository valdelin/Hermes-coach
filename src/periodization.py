"""Explicacao dos modelos de periodizacao para o atleta (CLI `periodization`).

Os 5 modelos de `PERIODIZATION` sao selecionaveis no .env e ajustam a
distribuicao de focos na semana (ver `plan.PERIODIZATION_TEMPLATES`). Este
modulo traduz cada modelo em linguagem de atleta: o que significa, o que se
sente na pratica e com que perfil/objetivo combina — alem de sugerir um modelo
para o `GOAL` atual (+ estado de TSB, quando informado).

A escolha continua sendo do atleta/treinador: o motor nunca altera o plano sem
`PERIODIZATION` configurado (o TSB governa por padrao).
"""

# Autodescricao por modelo (pt). `summary` = a ideia; `athlete` = o que o
# atleta sente na pratica; `best_for` = com que perfil/objetivo brilha.
PERIODIZATION_INFO = {
    "polarized": {
        "summary": "Polarizado (80/20): a maioria do volume em Z2 e uma fracao "
                   "pequena em VO2 curto. Quase nada de sweet spot/limiar no "
                   "meio do caminho.",
        "athlete": "Muito Z2 de 'conversa', 1-2 dias curtos de VO2 por semana; "
                   "a semana raramente tem aquela sensacao de 'apertar' no "
                   "limiar.",
        "best_for": "Atletas com volume alto que querem VO2; exige muitas "
                    "horas por semana (nao e o caso de seg-sex com volume "
                    "moderado).",
    },
    "pyramidal": {
        "summary": "Piramidal: base Z2 ancorando a semana, com progressao ate "
                   "sweet spot e limiar conforme o TSB sobe.",
        "athlete": "Z2 sustentado + 1-2 dias de qualidade subindo gradual; "
                   "sente a base firme e o limiar evoluindo sem choque.",
        "best_for": "Quem quer evoluir FTP/limiar com base solida — o "
                    "casamento natural de ftp-builder e gran-fondo.",
    },
    "undulating": {
        "summary": "Ondulante: alterna qualidade e recuperacao dentro da "
                   "propria semana (hard-easy).",
        "athlete": "Qualidade -> leve -> qualidade -> leve -> qualidade: o dia "
                   "leve fica exatamente no meio, quebrando a sequencia de "
                   "dias seguidos.",
        "best_for": "Quem acumula fadiga facil ou treina dias seguidos "
                    "(protege quando o TSB esta baixo, evitando overreaching).",
    },
    "linear": {
        "summary": "Linear: progressao simples semana a semana (Z2 -> sweet "
                   "spot -> limiar -> VO2); a carga cresce de forma previsivel "
                   "ate um pico.",
        "athlete": "Volume/intensidade sobem de forma previsivel; perto do "
                   "pico a semana 'apertura'. Bom para chegar pronto numa "
                   "data.",
        "best_for": "Quem tem uma data-alvo (prova ou reteste de FTP) e quer "
                    "um pico no fim — e o formato classico de preparacao.",
    },
    "block": {
        "summary": "Blocos: a semana inteira concentrada num estimulo so (tudo "
                   "Z2, ou tudo sweet spot, ou tudo qualidade), e o bloco muda "
                   "de uma semana para a outra.",
        "athlete": "Semanas monotonas e intensas em bloco, seguidas de "
                   "descanso maior entre blocos.",
        "best_for": "Atletas avancados que toleram monotonia e periodizam em "
                    "grandes blocos; arriscado com fadiga alta (TSB muito "
                    "baixo) ou poucas horas por semana.",
    },
}

# Afinidade por GOAL: (top, evitar). `top` = modelos que mais fazem sentido
# para o objetivo; `avoid` = modelos que tendem a atrapalhar.
GOAL_AFFINITY = {
    "back-to-fitness": (["pyramidal", "block"], ["polarized"]),
    "ftp-builder": (["pyramidal", "undulating", "linear"], ["block"]),
    "gran-fondo": (["pyramidal", "polarized"], ["block"]),
    "time-trial": (["linear", "pyramidal"], ["polarized", "block"]),
    "climbing": (["undulating", "polarized"], ["block"]),
    "active-off-season": (["block", "pyramidal"], []),
    "race": (["linear", "undulating"], ["block"]),
}

# Ajuste por TSB: quando a fadiga esta alta, dar preferencia a modelos com
# recuperacao embutida; com TSB fresco, liberar progressao/PVO2.
TSB_LOW = -10  # abaixo disso: fadiga acumulada (Friel: otimo < -10 para treino)
TSB_HIGH = 5   # acima disso: fresco o suficiente para qualidade


def quote(model):
    """Modelo valido ou None (aceita maiusculas/underscore)."""
    key = str(model or "").strip().lower().replace("_", "-")
    return key if key in PERIODIZATION_INFO else None


def describe(model):
    """Texto detalhado de um modelo (ou None se invalido)."""
    key = quote(model)
    if not key:
        return None
    info = PERIODIZATION_INFO[key]
    return (f"{key} — {info['summary']}\n"
            f"  Na pratica: {info['athlete']}\n"
            f"  Melhor para: {info['best_for']}")


def list_models():
    """Lista os 5 modelos com o resumo de uma linha."""
    return [f"{key} — {PERIODIZATION_INFO[key]['summary']}"
            for key in PERIODIZATION_INFO]


def suggest_for_goal(goal, tsb=None):
    """Modelos recomendados para um GOAL (e TSB, opcional).

    Retorna ("top", "avoid"): listas de modelos. O TSB reordena o top:
    fadiga alta favorece undulating (recuperacao embutida); TSB fresco
    favorece linear/polarized (qualidade/progressao).
    """
    top, avoid = GOAL_AFFINITY.get(goal, (["pyramidal", "undulating"], []))
    if tsb is None:
        return top[:2], avoid
    if tsb < TSB_LOW:
        # fadiga acumulada: recuperacao embutida primeiro, sem progressao dura
        order = [m for m in ("undulating", "pyramidal", "block",
                             "polarized", "linear") if m in top]
        return order[:2], avoid
    if tsb > TSB_HIGH:
        # fresco: qualidade/progressao na frente
        order = [m for m in ("linear", "polarized", "pyramidal",
                             "undulating", "block") if m in top]
        return order[:2], avoid
    return top[:2], avoid


def explain_current(goal=None, periodization=None, tsb=None):
    """Recomendacao completa para o estado atual (para a CLI)."""
    lines = []
    goal = goal or "sem GOAL (TSB governa)"
    if periodization and quote(periodization):
        lines.append(f"Configurado agora: {describe(periodization)}")
    else:
        lines.append("Sem PERIODIZATION no .env: o TSB governa a semana "
                     "(padrao — evolui sozinho por faixa de TSB).")
    top, avoid = suggest_for_goal(goal, tsb)
    estado = ""
    if tsb is not None:
        estado = (f" (TSB {tsb:.1f}: fadiga "
                  f"{'alta' if tsb < TSB_LOW else 'moderada' if tsb < TSB_HIGH else 'baixa'})")
    lines.append(f"Sugestao para {goal}{estado}:")
    lines.append(f"  top: {', '.join(top) or 'qualquer'} | evitar: "
                 f"{', '.join(avoid) or 'nada em especial'}")
    return "\n".join(lines)
"""Estimativa de FTP a partir de treinos nao agendados (issue #6).

Modulo puro e deterministico (sem rede, sem data corrente): dado o stream de
potencia de um pedal fora do plano, estima um novo FTP e valida a qualidade do
esforco.

- A fonte primaria da feature e o estimado que o proprio Intervals calcula
  (`icu_pm_ftp` no detalhe da atividade). Este modulo e a verificacao local
  (melhor media movel de 20 min x 0.95) e o motor dos gates.
- Nada aqui depende de `date.today()` nem de rede: dado o mesmo stream,
  retorna sempre o mesmo resultado.
"""

import math
import statistics
from dataclasses import dataclass

# Janela do esforco que sustenta o FTP (20 min) e conversao classica do
# teste de 20 min: FTP ~ 95% da melhor media de 20 minutos.
BEST_WINDOW_SEC = 1200
FTP_FACTOR = 0.95

# Gates de qualidade do esforco dentro da janela do best-20min.
MAX_CV = 0.15            # variabilidade <= 15% (esforco "limpo", nao puncheiro)
MIN_WINDOW_RATIO = 0.80  # minimo da janela >= 80% da media (sem apagoes)

# Gate de contexto: propor novo FTP apenas para cima (>= +3%) e dentro de um
# limite anti-anomalia (<= +30%). Um esforco abaixo do FTP atual NAO e
# evidencia de FTP menor (fadiga derruba potencia).
MIN_NEW_FTP_RATIO = 1.03
MAX_NEW_FTP_RATIO = 1.30

# Limpeza de outliers: valores acima de SPIKE_FACTOR x a mediana do pedal sao
# considerados picos espurios (sensor/bateria) e clipados na mediana x fator.
# Conservador: nao remove o valor, apenas limita — qualquer efeito no
# best-20min e para baixo (subestima, nunca infla).
SPIKE_FACTOR = 2.5

_zero = 0.0


@dataclass(frozen=True)
class RideFtpEstimate:
    best_effort_avg: float           # melhor media movel real da janela (W)
    best_start_index: int            # inicio da janela vencedora no stream
    best_end_index: int              # fim (exclusivo) da janela vencedora
    cleaned_outliers: int            # qtd de picos clipados/spurios
    cv: float                        # coeficiente de variacao da janela
    min_ratio: float                 # min(janela) / media(janela)
    proposed_ftp: float              # round(best * FTP_FACTOR), em watts
    diff_ratio: float                # proposed_ftp / current_ftp
    quality_ok: bool                 # passou nos gates de qualidade
    suggests_new: bool               # quality_ok e diff dentro de +3%..+30%
    reason: str = ""


def mean(values):
    return sum(values) / len(values)


def pstdev(values):
    return statistics.pstdev(values)


def clean_power(power, anomalies=None, spike_factor=SPIKE_FACTOR):
    """Clipa picos espurios do stream (sensor/bateria) e valores nao-finitos.

    - valores nao numericos/infinitos viram 0 (e contados como removidos);
    - valores acima de `spike_factor` x mediana (ou com `anomalies` True no
      mesmo indice) sao clipados na mediana x fator.
    Retorna (lista limpa, quantidade de outliers tratados).
    """
    cleaned = list(power)
    finite = [p for p in cleaned
              if isinstance(p, (int, float)) and math.isfinite(p)]
    if not finite:
        return cleaned, 0
    median = statistics.median(finite)
    if median <= 0:
        return cleaned, 0
    threshold = median * spike_factor
    flagged = {i for i, a in enumerate(anomalies or []) if a}
    removed = 0
    for i, p in enumerate(cleaned):
        if not isinstance(p, (int, float)) or not math.isfinite(p):
            cleaned[i] = _zero
            removed += 1
        elif (i in flagged) or p > threshold:
            cleaned[i] = threshold
            removed += 1
    return cleaned, removed


def best_effort(power, seconds, sample_sec=1.0):
    """Melhor media movel de `seconds` sobre o stream (amostrado a cada
    `sample_sec`). Retorna (media, indice_inicio, indice_fim) ou
    (None, 0, 0) quando o stream e curto demais para a janela."""
    if not power:
        return None, 0, 0
    window = max(1, int(round(seconds / sample_sec)))
    if len(power) < window:
        return None, 0, 0
    total = sum(power[:window])
    best = total
    start = 0
    for i in range(1, len(power) - window + 1):
        total += power[i + window - 1] - power[i - 1]
        if total > best:
            best = total
            start = i
    return best / window, start, start + window


def ftp_from_best20(best20):
    """Conversao classica do teste de 20 min: FTP = round(0.95 x best20)."""
    return int(round(best20 * FTP_FACTOR))


def analyze_ride(power, current_ftp, sample_sec=1.0,
                 window_sec=BEST_WINDOW_SEC, ftp_factor=FTP_FACTOR,
                 max_cv=MAX_CV, min_window_ratio=MIN_WINDOW_RATIO,
                 min_new_ratio=MIN_NEW_FTP_RATIO, max_new_ratio=MAX_NEW_FTP_RATIO,
                 spike_factor=SPIKE_FACTOR, anomalies=None):
    """Avalia um pedal fora do plano e devolve uma estimativa de FTP.

    Tudo determinístico. `current_ftp` e o FTP vigente (`.env`); `power` e a
    lista de watts do stream; `anomalies` (opcional) sao os flags de anomalia
    detectados pela plataforma."""
    power = list(power)
    if not power:
        return RideFtpEstimate(0.0, 0, 0, 0, 0.0, 0.0, 0.0, 1.0,
                               False, False, "sem dados de potencia")
    cleaned, removed = clean_power(power, anomalies=anomalies,
                                   spike_factor=spike_factor)
    best, start, end = best_effort(cleaned, window_sec, sample_sec)
    if best is None:
        return RideFtpEstimate(0.0, 0, 0, removed, 0.0, 0.0, 0.0, 1.0,
                               False, False,
                               f"stream curto para {int(window_sec//60)} min")
    window = cleaned[start:end]
    m = mean(window)
    cv = pstdev(window) / m if m else float("inf")
    mn = min(window)
    min_ratio = mn / m if m else 0.0
    proposed = int(round(best * ftp_factor))
    diff_ratio = proposed / current_ftp if current_ftp else float("inf")

    problems = []
    if cv > max_cv:
        problems.append(f"variabilidade alta (CV {cv:.1%} > {max_cv:.0%})")
    if min_ratio < min_window_ratio:
        problems.append(f"apagoes na janela (min {min_ratio:.0%} < "
                        f"{min_window_ratio:.0%} da media)")
    quality_ok = not problems
    if not quality_ok:
        problems.append("esforco fora do plano nao sustenta estimativa")

    suggests_new = False
    if quality_ok:
        if diff_ratio < min_new_ratio:
            problems.append(f"FTP {proposed}W dentro de +{(min_new_ratio - 1):.0%} "
                            "do atual (sem novidade)")
        elif diff_ratio > max_new_ratio:
            problems.append(f"FTP {proposed}W acima de +{(max_new_ratio - 1):.0%} "
                            "do atual (provável anomalia)")
        else:
            suggests_new = True

    return RideFtpEstimate(best, start, end, removed, cv, min_ratio,
                           proposed, diff_ratio, quality_ok, suggests_new,
                           "; ".join(problems))
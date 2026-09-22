"""Detecao de candidatos a novo FTP a partir de treinos fora do plano (#6).

Camada de integracao (eventos do calendario -> detalhe -> streams -> analise):

- Os treinos feitos fora do plano hermes sao eventos com `paired_activity_id`
  e `external_id` nao-hermes; o Intervals expoe o detalhe da atividade
  (`GET /activity/{id}`) e os streams (`GET /activity/{id}/streams.json`).
- A verificacao local (melhor media movel de 20 min x 0.95) e o motor dos
  gates ficam em `ftp_estimation` (modulo puro); aqui ficam os filtros de
  entrada, a extracao do stream e o relatorio.

Nada aqui depende de `date.today()` nem de rede no momento de decidir; o
acesso a rede fica no chamador (CLI).
"""

import statistics

try:
    from plan import EXTERNAL_ID_PREFIX
    from ftp_estimation import analyze_ride
except ImportError:
    from .plan import EXTERNAL_ID_PREFIX
    from .ftp_estimation import analyze_ride

# Duracao minima do pedal para sustentar uma estimativa (45 min) e intensidade
# media minima como pre-filtro (evita buscar streams de pedais de recuperacao).
MIN_MOVING_SECS = 45 * 60
MIN_INTENSITY_RATIO = 0.75


def extra_activities(events):
    """Treinos feitos fora do plano: eventos pareados (paired_activity_id) cujo
    external_id nao e hermes. Devolve lista de dicts com activity_id/day/name."""
    out = []
    for item in events:
        paired = item.get("paired_activity_id")
        eid = item.get("external_id") or ""
        if not paired:
            continue
        if eid.startswith(EXTERNAL_ID_PREFIX):
            continue
        out.append({
            "activity_id": paired,
            "day": str(item.get("start_date_local") or "")[:10],
            "name": item.get("name") or str(paired),
        })
    return out


def can_estimate_ftp(activity, ftp, min_moving_secs=MIN_MOVING_SECS,
                     min_intensity_ratio=MIN_INTENSITY_RATIO):
    """Filtros baratos sobre o detalhe da atividade (sem buscar stream):
    nao-manual, duracao suficiente, com potencia e intensidade nao-boba."""
    if (activity.get("source") or "").upper() == "MANUAL":
        return False
    moving = activity.get("moving_time") or 0
    if moving < min_moving_secs:
        return False
    if "watts" not in (activity.get("stream_types") or []) \
            and not activity.get("device_watts"):
        return False
    avg = (activity.get("icu_weighted_avg_watts")
           or activity.get("icu_average_watts") or 0)
    if avg and avg < min_intensity_ratio * ftp:
        return False
    return True


def skip_reason(activity, ftp, min_moving_secs=MIN_MOVING_SECS,
                min_intensity_ratio=MIN_INTENSITY_RATIO):
    """Motivo do filtro (para o relatorio) ou None quando passa."""
    if (activity.get("source") or "").upper() == "MANUAL":
        return "atividade manual"
    moving = activity.get("moving_time") or 0
    if moving < min_moving_secs:
        return f"curta ({moving // 60}m < {min_moving_secs // 60}m)"
    if "watts" not in (activity.get("stream_types") or []) \
            and not activity.get("device_watts"):
        return "sem potencia"
    avg = (activity.get("icu_weighted_avg_watts")
           or activity.get("icu_average_watts") or 0)
    if avg and avg < min_intensity_ratio * ftp:
        return (f"intensidade baixa ({avg:.0f}W < "
                f"{min_intensity_ratio:.0%} do FTP {ftp}W)")
    return None


def sample_rate(time_stream):
    """Taxa media de amostragem do stream (segundos por amostra). Sem stream
    de tempo, assume 1 s (padrao do Zwift/Intervals)."""
    diffs = [b - a for a, b in zip(time_stream, time_stream[1:]) if b > a]
    if not diffs:
        return 1.0
    return statistics.median(diffs) or 1.0


def estimate_ride(activity_id, day, name, activity, power, time, ftp):
    """Analisa um pedal fora do plano e devolve o registro do candidato.

    `power`/`time` sao os streams; a taxa de amostragem e derivada do tempo.
    O registro salvo na meta do plan.json e exatamente este dict."""
    rate = sample_rate(time)
    anomalies = activity.get("anomaly_flags")
    if not isinstance(anomalies, list):
        anomalies = None
    est = analyze_ride(power, ftp, sample_sec=rate, anomalies=anomalies)
    return {
        "activity_id": activity_id,
        "day": day,
        "name": name,
        "intervals_ftp": activity.get("icu_pm_ftp"),
        "moving_secs": activity.get("moving_time"),
        "best20": est.best_effort_avg,
        "proposed_ftp": est.proposed_ftp,
        "diff_ratio": round(est.diff_ratio, 3),
        "quality_ok": est.quality_ok,
        "suggests_new": est.suggests_new,
        "reason": est.reason,
        "applied": False,
    }


def best_candidate(candidates):
    """Candidato validado a aplicar: o mais recente; empate -> maior proposto."""
    return max(candidates, key=lambda c: (c["day"], c["proposed_ftp"]))


def ride_settings(settings):
    """Entrada das sport-settings de bicicleta (Ride/VirtualRide) ou None."""
    for s in settings or []:
        types = s.get("types") or []
        if "Ride" in types or "VirtualRide" in types:
            return s
    return None


def sanitize_ride_payload(settings, indoor_ftp):
    """Payload do PUT das sport-settings: entrada atual sem created/updated,
    com `indoor_ftp` novo (mesmo padrao do alinhamento 210 -> 182W em 19/09)."""
    payload = {k: v for k, v in settings.items()
               if k not in ("created", "updated")}
    payload["indoor_ftp"] = int(indoor_ftp)
    return payload
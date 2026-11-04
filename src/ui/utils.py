# src/ui/utils.py
"""Helpers para integrar UI com Application/plan.json."""

import os
import sys
import math
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.application import Application, load_env
    from src.plan import load_plan, load_plan_meta, DEFAULT_FTP
    from src.intervals_adapter import IntervalsAdapter
    from src.intervals_client import IntervalsClient
    from src.coach import latest_metrics
    from src import recovery
    from src.charts import pmc_chart
except Exception:
    from application import Application, load_env
    from plan import load_plan, load_plan_meta, DEFAULT_FTP
    from intervals_adapter import IntervalsAdapter
    from intervals_client import IntervalsClient
    from coach import latest_metrics
    import recovery
    from charts import pmc_chart


PLAN_FILE = PROJECT_ROOT / "plan.json"
ENV_FILE = PROJECT_ROOT / ".env"


def get_app():
    load_env(ENV_FILE)
    athlete_id = os.environ.get("INTERVALS_ATHLETE_ID")
    api_key = os.environ.get("INTERVALS_API_KEY")
    if athlete_id and api_key:
        client = IntervalsClient(athlete_id, api_key)
        return Application(plan_path=PLAN_FILE, env_path=ENV_FILE,
                           client_factory=lambda: IntervalsAdapter(client))
    return Application(plan_path=PLAN_FILE, env_path=ENV_FILE)


def _build_pmc_rows(client):
    """Monta série PMC (day, ctl, atl, tsb) a partir de atividades do Intervals.icu."""
    try:
        from datetime import date, timedelta
        newest = date.today()
        oldest = newest - timedelta(days=365)

        inner = getattr(client, "_client", None)
        if inner is None:
            c2 = getattr(client, "client", None)
            if c2 is not None:
                inner = getattr(c2, "_client", None) or c2
        if inner is None and hasattr(client, "activities"):
            inner = client

        acts = []
        if inner is not None and hasattr(inner, "activities"):
            try:
                acts = inner.activities(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
            except Exception:
                acts = []
        if not acts:
            # fallback: eventos
            try:
                c2 = inner or client
                if hasattr(c2, "events"):
                    events = c2.events(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
                    acts = events
            except Exception:
                acts = []

        daily = {}
        for a in acts:
            if not isinstance(a, dict):
                continue
            start = a.get("start_date_local") or a.get("start_date") or ""
            if not start:
                continue
            try:
                d = date.fromisoformat(start[:10])
            except Exception:
                continue
            tss = a.get("icu_training_load") or a.get("training_load") or a.get("tss")
            try:
                tss = float(tss)
            except Exception:
                tss = 0.0
            if tss and tss > 0:
                daily[d] = daily.get(d, 0.0) + tss

        if not daily:
            return []
        rows = recovery.pmc_series(daily)
        return rows
    except Exception:
        return []


def load_dashboard_data():
    """Carrega dados para o Dashboard (somente leitura)."""
    load_env(ENV_FILE)
    app = get_app()
    data = {
        "has_plan": False,
        "plan": [],
        "meta": {},
        "today": date.today(),
        "today_workout": None,
        "next_days": [],
        "ftp": os.environ.get("FTP") or str(DEFAULT_FTP),
        "vo2": "—",
        "vo2_date": None,
        "ctl": "—",
        "atl": "—",
        "tsb": "—",
        "pmc_chart": [],
    }

    try:
        client = app.client()

        newest = date.today()

        # VO₂max direto do wellness do Intervals.icu (mais confiável)
        try:
            oldest_w = newest - timedelta(days=90)
            wellness = client.wellness(oldest=oldest_w.isoformat(), newest=newest.isoformat())
            if isinstance(wellness, list):
                latest = None
                for entry in wellness:
                    raw = entry if isinstance(entry, dict) else getattr(entry, "raw", None)
                    if not isinstance(raw, dict):
                        continue
                    try:
                        observed = date.fromisoformat(str(raw.get("id") or raw.get("day") or "")[:10])
                        value = next((raw[key] for key in ("vo2max", "vo2Max", "VO2max")
                                      if raw.get(key) is not None), None)
                        if isinstance(value, bool):
                            continue
                        value = float(value)
                        if not math.isfinite(value) or value <= 0 or not oldest_w <= observed <= newest:
                            continue
                    except (TypeError, ValueError):
                        continue
                    if latest is None or observed > latest[0]:
                        latest = (observed, value)
                if latest:
                    observed, value = latest
                    data["vo2"] = str(int(value)) if value.is_integer() else f"{value:.1f}"
                    data["vo2_date"] = observed.isoformat()
        except Exception:
            pass

        # CTL/ATL/TSB via eventos + gráfico PMC
        try:
            pmc_rows = _build_pmc_rows(client)
            if pmc_rows:
                data["pmc_chart"] = pmc_chart(pmc_rows, markup=True)
                last = pmc_rows[-1]
                data["ctl"] = f"{float(last[1]):.1f}"
                data["atl"] = f"{float(last[2]):.1f}"
                data["tsb"] = f"{float(last[3]):+.1f}" if last[3] >= 0 else f"{float(last[3]):.1f}"
            else:
                oldest = newest - timedelta(days=120)
                events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
                m = latest_metrics(events)
                if m:
                    if getattr(m, "ctl") is not None:
                        data["ctl"] = f"{float(m.ctl):.1f}"
                    if getattr(m, "atl") is not None:
                        data["atl"] = f"{float(m.atl):.1f}"
                    if getattr(m, "tsb") is not None:
                        data["tsb"] = f"{float(m.tsb):+.1f}" if float(m.tsb) >= 0 else f"{float(m.tsb):.1f}"
        except Exception as e:
            print(f"DEBUG: {e}", file=sys.stderr)
            try:
                oldest = newest - timedelta(days=120)
                events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
                m = latest_metrics(events)
                if m:
                    if getattr(m, "ctl") is not None:
                        data["ctl"] = f"{float(m.ctl):.1f}"
                    if getattr(m, "atl") is not None:
                        data["atl"] = f"{float(m.atl):.1f}"
                    if getattr(m, "tsb") is not None:
                        data["tsb"] = f"{float(m.tsb):+.1f}" if float(m.tsb) >= 0 else f"{float(m.tsb):.1f}"
            except Exception:
                pass
    except Exception as e:
        print(f"DEBUG: {e}", file=sys.stderr)
        pass

    try:
        data["meta"] = app.load_plan_meta() or {}
    except Exception:
        data["meta"] = {}
    try:
        plan = load_plan(PLAN_FILE)
        if plan:
            data["has_plan"] = True
            data["plan"] = plan
            today_iso = date.today().isoformat()
            for w in plan:
                if w.get("day") == today_iso:
                    data["today_workout"] = w
                    break
            count = 0
            for w in plan:
                if w.get("day") >= today_iso and w.get("day") != today_iso:
                    data["next_days"].append(w)
                    count += 1
                    if count >= 3:
                        break
    except FileNotFoundError:
        data["has_plan"] = False
    except Exception:
        data["has_plan"] = False
    return data

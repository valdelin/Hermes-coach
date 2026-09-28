import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS,
                       wellness_summary, format_wellness, real_pmc_by_day)
    from intervals_client import IntervalsClient, IntervalsApiError
    from impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                  forecast_pmc)
    from plan import (build_plan, event_payload, load_plan, load_plan_meta,
                      reconcile, save_plan, orphan_external_ids,
                      parse_training_days, parse_goal, parse_weekly_hours,
                      parse_long_day, parse_fthr, parse_periodization,
                      GOAL_LABELS, FOCUS_LABELS_PT, PERIODIZATIONS,
                      PERIODIZATION_LABELS, REST, DEFAULT_FTP, CUE_LANGS,
                      GOALS, adherence_report, _tsb_race_verdict)
    import ftp_scan
    import recovery
    import activity_summary
    import charts
    import report
    import readiness
    import periodization
except ImportError:
    from .coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS,
                        wellness_summary, format_wellness, real_pmc_by_day)
    from .intervals_client import IntervalsClient, IntervalsApiError
    from .impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                   forecast_pmc)
    from .plan import (build_plan, event_payload, load_plan, load_plan_meta,
                       reconcile, save_plan, orphan_external_ids,
                       parse_training_days, parse_goal, parse_weekly_hours,
                       parse_long_day, parse_fthr, parse_periodization,
                       GOAL_LABELS, FOCUS_LABELS_PT, PERIODIZATIONS,
                       PERIODIZATION_LABELS, REST, DEFAULT_FTP, CUE_LANGS,
                       GOALS, adherence_report, _tsb_race_verdict)
    from . import ftp_scan
    from . import recovery
    from . import activity_summary
    from . import charts
    from . import report
    from . import readiness
    from . import periodization

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "plan.json"
ENV_FILE = PROJECT_ROOT / ".env"


def load_env(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_client():
    load_env(PROJECT_ROOT / ".env")
    athlete_id = os.environ.get("INTERVALS_ATHLETE_ID")
    api_key = os.environ.get("INTERVALS_API_KEY")
    if not athlete_id or not api_key:
        sys.exit("Faltam INTERVALS_ATHLETE_ID/INTERVALS_API_KEY no .env")
    return IntervalsClient(athlete_id, api_key)


def get_ftp():
    load_env(PROJECT_ROOT / ".env")
    return int(os.environ.get("FTP", DEFAULT_FTP))


def get_fthr():
    """FTHR do .env (frequencia cardiaca no limiar, bpm) para prescricao sem
    medidor de potencia (#3), ou None se ausente. Invalido -> aviso + None."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("FTHR", "")
    fthr = parse_fthr(value)
    if value.strip() and fthr is None:
        print(f"aviso: FTHR={value!r} invalido; use bpm (ex.: 182)")
    return fthr


def get_training_days():
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("TRAINING_DAYS", "")
    return parse_training_days(value)


def get_goal():
    """GOAL do .env (tipo de plano) ou None (comportamento padrao por TSB)."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("GOAL", "")
    goal = parse_goal(value)
    if value.strip() and goal is None:
        print(f"aviso: GOAL={value!r} invalido; valores: {', '.join(GOALS)}")
    return goal


def get_periodization():
    """PERIODIZATION do .env (modelo de periodizacao) ou None. O modelo ajusta
    a distribuicao de focos da semana (polarized, pyramidal, ...); sem ele vale
    GOAL/template padrao."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("PERIODIZATION", "")
    p = parse_periodization(value)
    if value.strip() and p is None:
        print(f"aviso: PERIODIZATION={value!r} invalido; modelos: "
              f"{', '.join(PERIODIZATIONS)}")
    return p


def get_race_date():
    """RACE_DATE do .env (YYYY-MM-DD) ou None. Necessaria para GOAL=race."""
    load_env(PROJECT_ROOT / ".env")
    raw = os.environ.get("RACE_DATE", "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        print(f"aviso: RACE_DATE={raw!r} invalido; use YYYY-MM-DD")
        return None


def get_weekly_hours():
    """WEEKLY_HOURS do .env (horas disponiveis por semana) ou None. O build
    escala a duracao dos treinos para caber nessas horas."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("WEEKLY_HOURS", "")
    hours = parse_weekly_hours(value)
    if value.strip() and hours is None:
        print(f"aviso: WEEKLY_HOURS={value!r} invalido; sem ajuste de volume")
    return hours


def get_long_day():
    """LONG_DAY do .env (dia preferido para treinos longos, ex. 'dom'/'sun')
    ou None."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("LONG_DAY", "")
    day = parse_long_day(value)
    if value.strip() and day is None:
        print(f"aviso: LONG_DAY={value!r} invalido; dias: seg..dom / mon..sun")
    return day


def get_ftp_test_date():
    """FTP_TEST_DATE do .env (YYYY-MM-DD, futura) ou None. Quando definida, o
    build protege as 48h antes do teste e cria o evento do Ramp Test."""
    load_env(PROJECT_ROOT / ".env")
    raw = os.environ.get("FTP_TEST_DATE", "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        print(f"aviso: FTP_TEST_DATE={raw!r} invalido; use YYYY-MM-DD")
        return None


def _env_set(key, value, path=None):
    """Grava/atualiza `key=value` no .env (ou em `path`) sem tocar nas demais
    linhas; nunca expoe a API key."""
    env_path = path or ENV_FILE
    key_line = f"{key}={value}"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    kept = [line for line in lines
            if not line.startswith(f"{key}=") and line.strip()]
    kept.append(key_line)
    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    os.environ[key] = value


def _record_ftp_candidates(new_candidates):
    """Mescla registros do ftp-scan na meta do plan.json (por activity_id)."""
    try:
        plan = load_plan(PLAN_FILE)
    except FileNotFoundError:
        print("aviso: plan.json ausente; rode `build` antes do `ftp-scan` "
              "(candidatos nao registrados).")
        return {}
    meta = load_plan_meta(PLAN_FILE)
    merged = dict(meta.get("ftp_candidates") or {})
    for c in new_candidates:
        merged[c["activity_id"]] = c
    save_plan(plan, PLAN_FILE, goal=meta["goal"], race_date=meta["race_date"],
              ftp_test_date=meta["ftp_test_date"], ftp_candidates=merged)
    return merged


def _pending_ftp_candidates():
    """Candidatos a novo FTP da meta, validados e ainda nao aplicados."""
    meta = load_plan_meta(PLAN_FILE)
    cands = meta.get("ftp_candidates") or {}
    return sorted(
        (c for c in cands.values()
         if c.get("suggests_new") and not c.get("applied")),
        key=lambda c: c.get("day", ""), reverse=True)


def _pending_ftp_hint():
    """Aviso curto de FTP sugerido pendente (para info/ftp-check) ou None."""
    pending = _pending_ftp_candidates()
    if not pending:
        return None
    p = pending[0]
    return (f"FTP sugerido pendente: {p['proposed_ftp']}W em {p['day']} "
            f"({p['name']}) — rode `ftp-scan` para revisar.")


def _plan_hr_mode():
    """True quando o plan.json atual tem treinos em modo FC (#3: sem medidor
    de potencia, prescricao em %FTHR + RPE)."""
    try:
        plan = load_plan(PLAN_FILE)
    except FileNotFoundError:
        return False
    return any(w.get("hr_mode") for w in plan)


def _hr_mode_hint():
    """Aviso curto de plano em modo FC (sem medidor de potencia) ou None."""
    if not _plan_hr_mode():
        return None
    fthr = get_fthr()
    if fthr:
        return ("Plano em modo FC (sem medidor de potencia): prescricao em "
                f"%FTHR + RPE com FTHR {fthr} bpm; carga estimada por FC "
                "(icu_training_load).")
    return ("Plano em modo FC (sem medidor de potencia), mas FTHR ausente no "
            ".env: prescricao em %FTHR + RPE; configure FTHR para alvos em bpm.")


def prompt_race_date():
    """GOAL=race exige a data alvo (dia da prova): sempre pergunta — nunca
    assume default nem deixa em branco — e salva no .env."""
    while True:
        raw = input("Qual a data alvo (dia da prova)? (YYYY-MM-DD) ").strip()
        try:
            race = date.fromisoformat(raw)
        except ValueError:
            print(f"  data invalida: {raw!r} — use YYYY-MM-DD (ex.: 2026-12-01)")
            continue
        if race <= date.today():
            print("  a prova precisa ser numa data futura.")
            continue
        _env_set("RACE_DATE", race.isoformat())
        return race.isoformat()


def prompt_ftp_test_date():
    """Agenda o teste de FTP: pergunta a data (futura), valida e salva em
    `FTP_TEST_DATE` no .env. Usada quando o ftp-check indica reteste e o
    atleta aceita preparar os dias anteriores."""
    while True:
        raw = input("Qual a data do Ramp Test (FTP)? (YYYY-MM-DD) ").strip()
        try:
            test = date.fromisoformat(raw)
        except ValueError:
            print(f"  data invalida: {raw!r} — use YYYY-MM-DD (ex.: 2026-10-22)")
            continue
        if test <= date.today():
            print("  o teste precisa ser numa data futura.")
            continue
        _env_set("FTP_TEST_DATE", test.isoformat())
        return test.isoformat()


def describe_training_days(training_days=None, env_value=None):
    """Texto curto da agenda em uso (para build/reconcile printarem)."""
    if training_days is None:
        training_days = get_training_days()
    names = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex",
             5: "sab", 6: "dom"}
    seq = ",".join(names[d] for d in training_days)
    if env_value is None or not str(env_value).strip():
        return f"Agenda: {seq} (TRAINING_DAYS ausente -> padrao)"
    return f"Agenda: {seq} (TRAINING_DAYS={env_value})"


def cmd_periodization(args):
    """Explica os modelos de periodizacao para o atleta e sugere o modelo para
    o GOAL/perfil atual (nao altera nada)."""
    active_model = get_periodization()
    goal = get_goal()
    tsb = None
    if not args.no_tsb:
        try:
            client = get_client()
            today = date.today()
            events = client.events(oldest=(today - timedelta(days=args.days)).isoformat(),
                                   newest=today.isoformat())
            metrics = latest_metrics(events)
            if metrics:
                tsb = metrics.tsb
        except IntervalsApiError as exc:
            print(f"aviso: nao consegui o TSB ({exc}); sugestao sem TSB.")
    if args.model:
        desc = periodization.describe(args.model)
        if not desc:
            print(f"modelo invalido: {args.model!r}; use: "
                  f"{', '.join(periodization.PERIODIZATION_INFO)}")
            return 2
        print(desc)
        print()
        top, avoid = periodization.suggest_for_goal(get_goal() or None, tsb)
        fit = ("combina com o seu objetivo" if args.model in top
               else "evite para o seu objetivo atual"
               if args.model in avoid else "neutro para o seu objetivo")
        print(f"Afinidade com GOAL={get_goal() or 'TSB (padrao)'}: {fit}.")
        return
    for m in periodization.list_models():
        print(m)
        print()
    print(periodization.explain_current(goal=get_goal() or None,
                                        periodization=active_model, tsb=tsb))


def cmd_info(args):
    client = get_client()
    ftp = get_ftp()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    metrics = latest_metrics(events)
    print(f"eventos na janela: {len(events)}")
    if metrics:
        print(f"TSB {metrics.tsb:.1f} (CTL {metrics.ctl:.1f} / ATL {metrics.atl:.1f})")
    wellness = client.wellness(oldest=oldest.isoformat(), newest=newest.isoformat())
    summary = wellness_summary(wellness, days=7)
    print(f"Wellness: {format_wellness(summary)}")
    hint = _pending_ftp_hint()
    if hint:
        print(hint)
    hr_hint = _hr_mode_hint()
    if hr_hint:
        print(hr_hint)


def cmd_check(args):
    """Prontidao do dia (#31): le wellbeing, avalia sinais de recuperacao e
    SUGERE (nunca impoe) trocar o treino de hoje por recuperacao leve.

    - Sem `--apply`: so reporta (TB de hoje + sinais + sugestao).
    - Com `--apply`: se a sugestao for de troca, substitui o treino do dia no
      plan.json por uma recuperacao Z2 curta e avisa para rodar `push`.
    - Inicio de doenca (RHR 2+ noites + HRV caindo): alerta na tela e, se
      COACH_WEBHOOK estiver no .env, envia o aviso ao treinador tambem.
    """
    client = get_client()
    ftp = get_ftp()
    today = date.today()
    newest = today
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    metrics = latest_metrics(events)
    if metrics:
        print(f"TSB {metrics.tsb:.1f} (CTL {metrics.ctl:.1f} / "
              f"ATL {metrics.atl:.1f})")
    else:
        print("TSB: sem metricas na janela.")
    wellness = client.wellness(oldest=oldest.isoformat(),
                               newest=newest.isoformat())
    assessment = readiness.assess_readiness(wellness, days=args.days)
    print(f"Prontidao: {assessment.reason}")
    if not assessment.has_data:
        print("Sem dados de wellness sincronizados para avaliar o dia.")
        return
    planned = None
    try:
        plan = load_plan(PLAN_FILE)
    except FileNotFoundError:
        plan = []
    today_w = next((w for w in plan if w["day"] == today.isoformat()), None)
    if today_w:
        print(f"Treino de hoje: {today_w['name']} "
              f"({today_w['planned_duration'] // 60}m, "
              f"TSS {today_w['tss']:.0f})")
    else:
        print("Hoje nao tem treino no plano.")
    swap, why = readiness.suggest_swap(assessment, today_w)
    if swap:
        print(f"SUGESTAO: {why}")
    else:
        print(f"Sem troca sugerida: {why}")
    if assessment.illness:
        print("ALERTA DE DOENCA: considere descanso e monitore amanha.")
        _notify_coach_if_configured(assessment, today)
    if swap and args.apply and today_w:
        new_w = readiness.recovery_workout(today.isoformat(), ftp)
        plan = [new_w if w["day"] == today.isoformat() else w for w in plan]
        meta = load_plan_meta(PLAN_FILE)
        save_plan(plan, PLAN_FILE, goal=meta["goal"],
                  race_date=meta["race_date"],
                  ftp_test_date=meta["ftp_test_date"],
                  ftp_candidates=meta.get("ftp_candidates"))
        print(f"Aplicado: {today_w['name']} -> {new_w['name']} "
              f"(TSS {new_w['tss']:.0f}, {new_w['planned_duration'] // 60}m).")
        print("Rode `push` para publicar a troca no calendario.")
    elif swap and args.apply:
        print("Nada a trocar hoje (sem treino no plano).")


def _notify_coach_if_configured(assessment, today):
    """Opcional (COACH_WEBHOOK no .env): aviso de inicio de doenca ao
    treinador. Nunca derruba o fluxo se o webhook falhar."""
    load_env(PROJECT_ROOT / ".env")
    webhook = os.environ.get("COACH_WEBHOOK", "").strip()
    if not webhook:
        return
    athlete = os.environ.get("INTERVALS_ATHLETE_ID", "?")
    try:
        resp = requests.post(webhook, timeout=10,
                             json=readiness.coach_alert_payload(
                                 athlete, assessment, today.isoformat()))
        if resp.status_code >= 400:
            print(f"aviso: webhook do treinador respondeu HTTP "
                  f"{resp.status_code}")
    except requests.exceptions.RequestException as exc:
        print(f"aviso: falha ao avisar o treinador ({exc}); "
              "siga com o treino normalmente.")


def cmd_ftp_check(args):
    client = get_client()
    ftp = get_ftp()
    goal = get_goal()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    sug = suggest_ftp_test(events, ftp, weeks=args.weeks, goal=goal)
    print(f"FTP atual: {ftp}W")
    if goal:
        print(f"Plano ativo: {GOAL_LABELS.get(goal, goal)} (janela de reteste pelo tipo de plano)")
    print(f"Ultimo teste de FTP: {sug.last_test or 'nenhum detectado'}"
          + (f" ({sug.days_since} dias)" if sug.days_since else ""))
    print(f"Reteste devido: {'SIM' if sug.due else 'nao'}  |  {sug.reason}")
    if sug.due:
        print("Sugestao: agende um Ramp Test no app Zwift em um dia descansado;")
        print("  rode `build --ftp-test YYYY-MM-DD` para proteger as 48h antes")
        print("  (D-2 facil, D-1 spin) e publicar o evento do teste no plano.")
    hint = _pending_ftp_hint()
    if hint:
        print(hint)


def cmd_model(args):
    client = get_client()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    series = daily_tss_series(events, window_days=args.days)
    engine = ImpulseResponseEngine()
    api = latest_metrics(events)
    print(f"eventos na janela: {len(events)} | dias com TSS: {len(series)}")
    # Bootstrap presente (#33): a pipeline interna do Intervals nao e
    # reproduzivel por EWMA simples sobre o `icu_training_load` (carga efetiva
    # ~2x; ver docs/ROADMAP.md #34), entao reconstruir a trajetoria do passado
    # diverge. Para o diagnostico bater com o que o plano realmente usa
    # (`latest_metrics`), o motor local parte do estado atual do Intervals.
    if api and api.ctl is not None and api.atl is not None:
        local = engine.compute_metrics([], initial_ctl=api.ctl,
                                       initial_atl=api.atl)
        print(f"Motor local (Banister, bootstrap hoje): "
              f"CTL {local['ctl_fitness']} / "
              f"ATL {local['atl_fatigue']} / TSB {local['tsb_form']}")
        print(f"Intervals.icu        : CTL {api.ctl:.1f} / "
              f"ATL {api.atl:.1f} / TSB {api.tsb:.1f}")
        print(f"Diferenca            : CTL {local['ctl_fitness'] - api.ctl:+.1f} / "
              f"ATL {local['atl_fatigue'] - api.atl:+.1f} / "
              f"TSB {local['tsb_form'] - api.tsb:+.1f}")
    else:
        # Sem estado viavel da API: cai para o motor partindo de zero.
        print("aviso: sem metricas validas (ctl/atl) da API na janela; "
              "motor local parte de zero.")
        local = engine.compute_metrics(series)
        print(f"Motor local (Banister): CTL {local['ctl_fitness']} / "
              f"ATL {local['atl_fatigue']} / TSB {local['tsb_form']}")
        print("Intervals.icu: metricas nao disponiveis na janela.")
    try:
        plan = load_plan(PLAN_FILE)
    except FileNotFoundError:
        plan = []
    if plan and api and api.ctl is not None and api.atl is not None:
        fc = forecast_pmc(events, plan, initial_ctl=api.ctl, initial_atl=api.atl)
        if fc["series"]:
            end = fc["end"]
            first = fc["series"][0]["day"]
            last = fc["series"][-1]["day"]
            print(f"Expected PMC (real + plano) de {first} a {last}: "
                  f"CTL {end['ctl_fitness']} / ATL {end['atl_fatigue']} / "
                  f"TSB {end['tsb_form']}")
            for row in fc["series"]:
                alert = "  <-- TSB <= -10" if row["tsb"] <= -10.0 else ""
                print(f"  {row['day']}  CTL {row['ctl']:6.1f}  "
                      f"ATL {row['atl']:6.1f}  TSB {row['tsb']:7.1f}"
                      f"  [{row['zone']}]{alert}")
            if fc["high_risk"]:
                print("Risco alto (TSB < -30): considerar R&R --")
                for r in fc["high_risk"]:
                    print(f"  {r['day']}  TSB {r['tsb']:.1f}")
            if fc["transition"]:
                print("Transicao (TSB > +25): descanso longo --")
                for r in fc["transition"]:
                    print(f"  {r['day']}  TSB {r['tsb']:.1f}")
        else:
            print("Expected PMC: sem treinos planejados para frente.")
    else:
        print("Projecao: sem plan.json ou metricas da API para projetar.")


def cmd_adherence(args):
    client = get_client()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    try:
        plan = load_plan(PLAN_FILE)
    except FileNotFoundError:
        print("sem plan.json: rode `build` primeiro.")
        return
    report = adherence_report(plan, events)
    print(f"Cumprimento do plano (plan.json) ate {report['today']}:")
    for w in report["weeks"]:
        pct = f"{w['pct']:.0f}%" if w["pct"] is not None else "  --"
        print(f"  {w['week']:<9} feito {w['done']:>3}  perdido {w['missed']:>3}  "
              f"pendente {w['pending']:>3}  -> {pct}")
    s = report["summary"]
    occurred = s["done"] + s["missed"]
    pct = f"{s['pct']:.0f}%" if s["pct"] is not None else "-"
    print(f"Total: {s['done']} feito / {s['missed']} perdido / "
          f"{s['pending']} pendente -> {pct} dos {occurred} treinos ocorridos")


def cmd_build(args):
    client = get_client()
    ftp = get_ftp()
    fthr = get_fthr()
    goal = get_goal()
    periodization = get_periodization()
    race_date = get_race_date()
    weekly_hours = get_weekly_hours()
    long_day = get_long_day()
    hr_mode = bool(getattr(args, "no_power", False))
    if hr_mode and fthr is None:
        print("erro: `--no-power` exige FTHR no .env (prescricao em %FTHR e "
              "RPE). Configure FTHR (bpm) e rode o build de novo.")
        print("  ex.: FTHR=182 no .env")
        return None
    if args.ftp_test:
        # --ftp-test YYYY-MM-DD: agenda o teste (valida futuro) e salva no .env
        try:
            test = date.fromisoformat(args.ftp_test)
        except ValueError:
            print(f"erro: --ftp-test={args.ftp_test!r} invalido; use YYYY-MM-DD")
            return None
        if test <= date.today():
            print("erro: --ftp-test precisa ser numa data futura.")
            return None
        _env_set("FTP_TEST_DATE", test.isoformat())
        ftp_test_date = test.isoformat()
    else:
        ftp_test_date = get_ftp_test_date()
    if goal == "race" and not race_date:
        # Regra da issue #5: plano race SEMPRE pergunta a data alvo antes de
        # montar o plano — nunca assume default nem deixa em branco.
        race_date = prompt_race_date()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    metrics = latest_metrics(events)
    tsb = metrics.tsb if metrics else 0.0
    try:
        existing = load_plan(PLAN_FILE)
    except FileNotFoundError:
        existing = None
    recovery_ramp = None
    ramp_label = None
    if getattr(args, "recovery", False):
        # #19: `build --recovery` ora o plano pelos tetos da rampa segura de
        # retorno a forma (mesma prescricao do CLI `recovery`).
        all_events = recovery.fetch_full_history(client)
        daily = recovery.actual_daily_load(all_events)
        rows, anchored = _pmc_rows(all_events, date(2011, 1, 1), date.today())
        if rows:
            st_real = recovery.state(rows)
            vol = recovery.weekly_volume(daily)
            if anchored:
                st = recovery.calibrated_state(st_real, vol) or st_real
            else:
                st = st_real
            ramp_pts = getattr(args, "ramp_pts", 9)
            weeks = max(getattr(args, "recovery_weeks", 12),
                        (args.days_plan + 6) // 7)
            schedule = recovery.ramp_schedule(st["peak_ctl"], vol, ramp_pts,
                                              weeks=weeks)
            recovery_ramp = schedule
            ramp_label = (f"teto semanal de retorno (CTL pico {st_real['peak_ctl']:.0f}; "
                          f"rampa +{ramp_pts}/sem): {schedule[0]:.0f} -> "
                          f"{schedule[-1]:.0f} TSS")
        else:
            print("aviso: sem treinos feitos com carga no historico; "
                  "`--recovery` ignorado (orcamento padrao).")
    plan = build_plan(events, tsb, ftp=ftp, days=args.days_plan,
                      existing=existing, training_days=get_training_days(),
                      goal=goal, race_date=race_date, ftp_test_date=ftp_test_date,
                      weekly_hours=weekly_hours, long_day=long_day,
                      hr_mode=hr_mode, recovery_ramp=recovery_ramp,
                      periodization=periodization)
    # Preserva candidatos de FTP ja registrados na meta (issue #6): o build
    # nao deve apagar o rastro de um ftp-scan anterior.
    existing_meta = load_plan_meta(PLAN_FILE)
    save_plan(plan, PLAN_FILE, goal=goal, race_date=race_date,
              ftp_test_date=ftp_test_date,
              ftp_candidates=existing_meta.get("ftp_candidates"))
    print(describe_training_days(env_value=os.environ.get("TRAINING_DAYS", "")))
    avail = []
    if weekly_hours:
        avail.append(f"{weekly_hours:g}h/semana")
    if long_day is not None:
        day_names = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex",
                     5: "sab", 6: "dom"}
        avail.append(f"treino longo: {day_names[long_day]}")
    if avail:
        print("Disponibilidade: " + " | ".join(avail))
    plano_label = GOAL_LABELS.get(goal, goal or "TSB (padrao)")
    if periodization:
        plano_label += f" / {PERIODIZATION_LABELS[periodization]}"
    race_info = f" | prova em {race_date}" if goal == "race" and race_date else ""
    test_info = f" | Ramp Test em {ftp_test_date}" if ftp_test_date else ""
    print(f"Plano: {plano_label}{race_info}{test_info} | TSB atual {tsb:.1f} | FTP {ftp}W")
    if ramp_label:
        print(ramp_label)
    if hr_mode:
        print(f"Prescricao sem medidor de potencia: alvos em %FTHR + RPE "
              f"(FTHR {fthr} bpm); carga estimada por FC no Intervals.")
    est_tss = sum(w["tss"] for w in plan)
    print(f"Plano gerado: {len(plan)} treinos | TSS estimado {est_tss:.0f}"
          + (" | preparacao p/ teste em " + ftp_test_date
             if ftp_test_date and any("Ramp Test (FTP)" in w["name"] for w in plan)
             else ""))
    for w in plan:
        print(f"  {w['day']} {w['name']:<30} {w['planned_duration'] // 60:>3}m TSS {w['tss']:.0f}")
    if goal == "race" and race_date:
        _print_race_tsb_projection(events, plan, metrics, race_date)
    return plan


def _print_race_tsb_projection(events, plan, metrics, race_date):
    """Projeta o TSB no dia da prova a partir do Expected PMC e compara com a
    faixa-alvo da literatura (Joe Friel ~+20; Science to Sport -10..+20 por
    atleta = #16). Aviso para o atleta/treinador, nao bloqueia o plano."""
    if metrics is None or metrics.ctl is None or metrics.atl is None:
        print("Projecao de TSB no dia da prova: indisponivel (metricas da API "
              "nao carregadas).")
        return
    fc = forecast_pmc(events, plan, initial_ctl=metrics.ctl,
                      initial_atl=metrics.atl, horizon=race_date)
    row = next((r for r in fc["series"] if r["day"] == race_date), None)
    if row is None:
        print("Projecao de TSB no dia da prova: fora do horizonte do plano "
              "(prova alem de 'days-plan').")
        return
    hint = {
        "ok": "dentro da faixa-alvo",
        "cansado": "chega a prova CANSADO (TSB < -10): considere antecipar o taper",
        "acima": "ACIMA do pico (TSB > +20): passou da faixa-alvo",
    }[_tsb_race_verdict(row["tsb"])]
    print(f"Projecao de TSB no dia da prova {race_date}: {row['tsb']:+.1f} -> "
          f"{hint} | alvo -10..+20 (Friel ~+20; por atleta = #16)")


def cmd_recovery(args):
    """Historico real do Intervals -> PMC (ancorado) -> estimativa de
    retorno a antiga forma + prescricao segura de rampa de volume.

    Usa somente treinos FEITOS (com atividade pareada); planejado-nao-feito nao
    conta como carga real. A serie ancorada parte dos valores reais
    `icu_ctl`/`icu_atl` do Intervals (fallback: reconstrucao local de zero).
    O pico historico e a melhor janela de 30 dias sao o "onde voce esteve"; a
    estimativa projeta o prazo de volta ao CTL de pico sob rampas
    conservadora/realista/otimista (CTL calibrado para a moeda TSS do plano),
    e a prescricao da a rampa semanal.
    """
    client = get_client()
    events = recovery.fetch_full_history(client)
    done = [e for e in events
            if e.get("paired_activity_id") or e.get("activity_id")]
    daily = recovery.actual_daily_load(events)
    rows, anchored = _pmc_rows(events, date(2011, 1, 1), date.today())
    if not rows:
        print("Sem treinos feitos com carga no historico.")
        return None
    st_real = recovery.state(rows)
    print(f"historico: {len(events)} eventos | treinos feitos com carga: "
          f"{len(done)}")
    print(f"periodo coberto: {st_real['first_day']} a {st_real['last_day']}")
    if anchored:
        print("(PMC real do Intervals: serie ancorada nos valores da API)")
    else:
        print("(PMC reconstruido local: sem icu_ctl/icu_atl no historico)")

    st = st_real
    vol = recovery.weekly_volume(daily)
    if anchored:
        st = recovery.calibrated_state(st, vol) or st
    print("\n=== AGORA ===")
    print(f"CTL {st_real['current_ctl']:.1f} | ATL {st_real['current_atl']:.1f} | "
          f"TSB {st_real['current_tsb']:+.1f}")
    print(f"volume semanal recente (28d): {vol:.0f} TSS")

    print("\n=== ONDE VOCE JA ESTEVE ===")
    print(f"pico de CTL: {st_real['peak_ctl']:.1f} em {st_real['peak_ctl_day']} "
          f"(TSB {st_real['peak_ctl_tsb']:+.1f})")
    print(f"melhor mes (CTL medio 30d): {st_real['window_avg']:.1f} "
          f"({st_real['window_start']} a {st_real['window_end']})")
    print(f"pico de TSB: {st_real['peak_tsb']:+.1f} em {st_real['peak_tsb_day']} "
          f"(CTL {st_real['peak_tsb_ctl']:.1f})")

    target = st["peak_ctl"]
    print("\n=== ESTIMATIVA DE RETORNO AO CTL PICO "
          f"({st_real['peak_ctl']:.0f} real) ===")
    scenarios = (
        ("conservador (+6/sem)", 6),
        ("realista    (+9/sem)", 9),
        ("otimista    (+12/sem)", 12),
    )
    for label, ramp in scenarios:
        r = recovery.estimate_return(st["current_ctl"], st["current_atl"],
                                     target, vol, ramp)
        w90 = _fmt_weeks(r["weeks_90"])
        w99 = _fmt_weeks(r["weeks_99"])
        print(f"  {label}: 90% do pico em {w90} | 100% em {w99}")
    print(f"  (sustentar o CTL pico {st_real['peak_ctl']:.0f} real exige ~"
          f"{target * 7:.0f} TSS/semana no plano)")

    if args.weeks > 0:
        ramp = args.ramp_pts
        print("\n=== PRESCRICAO SEGURA DE RETORNO "
              f"(rampa +{ramp}/sem, deload a cada 4 sem) ===")
        schedule = recovery.ramp_schedule(target, vol, ramp,
                                          weeks=args.weeks)
        line = []
        for i, wk in enumerate(schedule, start=1):
            tag = " (deload)" if i % 4 == 0 else ""
            line.append(f"sem {i}: {wk:.0f}{tag}")
        # quebra de linha a cada 4 semanas para legibilidade
        for i in range(0, len(line), 4):
            print("  " + " | ".join(line[i:i + 4]))
        print("  Dica: gere os treinos respeitando esses tetos com "
              "`build --recovery` (mesma rampa + deload).")
    else:
        print("\n(Dica: `recovery --weeks 12` imprime a rampa semanal segura.)")
    return st


def _fmt_weeks(weeks):
    if weeks is None:
        return "nao atingiu (horizonte)"  # pragma: no cover
    if weeks == 0:
        return "ja atingido"
    return f"~{weeks} sem (~{weeks / 4:.1f} mes)"



def cmd_summary(args):
    """Resumo dos treinos FEITOS por periodo (dia/semana/mes/trimestre/
    semestre/ano, duracao livre 'Nd'/'Nm'/'Ny', 'plan' ou 'custom').

    Janela terminando no dia-ancla (por padrao, ontem); 'custom' usa
    `--start`/`--end`; 'plan' cobre do primeiro ao ultimo dia do plano
    salvo. Usa apenas atividades pareadas (planejado-nao-feito fica fora).
    """
    client = get_client()
    anchor = args.date or (date.today() - timedelta(days=1))
    theme = getattr(args, "theme", None)
    if theme and theme not in report.THEMES:
        raise SystemExit(
            f"Tema invalido: {theme!r}. Temas disponiveis: "
            + ", ".join(report.THEMES))
    plan_days = _plan_days() if args.period == "plan" else None
    try:
        start, end = activity_summary.resolve_period(
            anchor, args.period, start=args.start, end=args.end,
            plan_days=plan_days)
    except ValueError as exc:
        raise SystemExit(f"Periodo invalido: {exc}")
    rows = activity_summary.done_activities(client, start, end)
    agg = activity_summary.summarize(rows)

    label = activity_summary.period_label(args.period)
    article = "DA" if args.period == "week" else "DO"
    print(f"=== RESUMO {article} {label.upper()} ({start} a {end}) ===")
    if not rows:
        print("Nenhum treino feito no periodo.")
        return agg

    print(f"Treinos feitos: {agg['sessions']} | "
          f"carga total: {agg['load']:.0f} TSS")
    parts = [
        f"Tempo: {activity_summary.fmt_time(agg['time_s'])}",
        f"Distancia: {activity_summary.fmt_dist(agg['distance_m'])}",
    ]
    if agg["elevation_m"]:
        parts.append(f"Elevacao: +{agg['elevation_m']:.0f} m")
    print(" | ".join(parts))
    power_parts = []
    if agg["avg_power"] is not None:
        power_parts.append(f"media {agg['avg_power']:.0f} W")
    if agg["np"] is not None:
        power_parts.append(f"NP {agg['np']:.0f} W")
    if power_parts:
        print("Potencia: " + " | ".join(power_parts))
    if agg["avg_hr"] is not None:
        print(f"FC: {agg['avg_hr']:.0f} bpm media")

    print("\nDetalhe por treino:")
    for r in rows:
        bits = [f"{r['day']}  {r['name']}"]
        if r["type"]:
            bits.append(f"({r['type']})")
        bits.append(activity_summary.fmt_time(r["time_s"]))
        if r["distance_m"]:
            bits.append(activity_summary.fmt_dist(r["distance_m"]))
        if r["load"]:
            bits.append(f"{r['load']:.0f} TSS")
        print("  " + "  ".join(bits))

    _summary_charts(client, start, end, rows, args.chart)
    _summary_export(client, args, start, end, rows, agg)
    return agg


def _plan_days():
    """Dias (date) cobertos pelo plano salvo, para o periodo 'plan'."""
    plan = load_plan(PLAN_FILE)
    days = [w["day"] for w in plan if w.get("day")]
    return [date.fromisoformat(d) for d in days]


def _pmc_rows(events, start, end):
    """Serie `[(day, ctl, atl, tsb)]` preferindo os valores REAIS do Intervals.

    Quando algum evento tem `icu_ctl`/`icu_atl` (pipeline interna do Intervals
    — mesmo numero que o site plota), ancora a serie nesses valores com
    decaimento EWMA entre dias (`pmc_series_anchored`). Senao cai na
    reconstrucao local sobre a carga real (`pmc_series(actual_daily_load)`).
    Filtra para a janela [start, end]. Retorna (rows, anchored): `anchored`
    indica se a serie veio dos valores reais (moeda do Intervals).
    """
    real = real_pmc_by_day(events)
    if real:
        rows = recovery.pmc_series_anchored(real, start, end)
    else:
        daily = recovery.actual_daily_load(events)
        rows = recovery.pmc_series(daily)
    return ([r for r in rows if start <= r[0] <= end], bool(real))


def _summary_chart_data(client, start, end, rows):
    """Dados dos graficos do resumo: (pmc_rows, weeks).

    `pmc_rows` = serie (day, ctl, atl, tsb) terminando em `end`; a janela
    acompanha o periodo (piso de 90 dias para dia/semana/mes; janelas
    maiores usam a extensao cheia). A serie parte dos valores reais do
    Intervals (`_pmc_rows`: `icu_ctl`/`icu_atl` com decaimento EWMA entre
    dias); sem valores reais, cai na reconstrucao local (`pmc_series`).
    `weeks` = carga semanal ISO ([]) quando `start` == `end` (periodo dia).
    """
    days_back = max(89, (end - start).days)
    pmc_start = end - timedelta(days=days_back)
    events = client.events(oldest=pmc_start.isoformat(), newest=end.isoformat())
    pmc_rows, _ = _pmc_rows(events, pmc_start, end)
    if start == end:
        return pmc_rows, []
    return pmc_rows, charts.weekly_load(rows)


def _summary_charts(client, start, end, rows, chart):
    """Graficos do resumo (padrao Pillar/Analog 'dashboard de 90 dias').

    PMC (janela do periodo, piso 90d) sempre em `auto`; barras de carga
    semanal apenas para periodo > 1 dia (ja que sai dos proprios treinos do
    periodo). `--chart none` desliga; `--chart pmc|load|all` escolhe um.
    """
    if chart == "none":
        return
    pmc_rows, weeks = _summary_chart_data(client, start, end, rows)
    pmc_parts = charts.pmc_chart(pmc_rows) if chart in ("auto", "all", "pmc") else []
    load_parts = (charts.load_chart(weeks)
                  if chart in ("auto", "all", "load") and start != end
                  else [])

    if pmc_parts:
        print("\n=== PMC (fitness/fadiga/form) ===")
        for line in pmc_parts:
            print("  " + line)
    if load_parts:
        print("\n=== CARGA SEMANAL ===")
        for line in load_parts:
            print("  " + line)
    return


def _summary_export(client, args, start, end, rows, agg):
    """Exporta (--export) o resumo com graficos em SVG para HTML/PDF.

    A extensao do caminho decide: .html escreve direto; .pdf renderiza o HTML
    via chromium headless. Nao altera a saida no terminal.
    """
    path = getattr(args, "export", None)
    if not path:
        return
    pmc_rows, weeks = _summary_chart_data(client, start, end, rows)
    theme = getattr(args, "theme", None) or report.DEFAULT_THEME
    html = report.render_summary_html(
        title=(f"Resumo {activity_summary.period_label(args.period)}"
               f" - {start} a {end}"),
        start=start, end=end, agg=agg, rows=rows,
        pmc_rows=pmc_rows, weeks=weeks, theme=theme)
    report.write(path, html)
    print(f"Exportado: {path}")


def cmd_reconcile(args):
    plan = load_plan(PLAN_FILE)
    client = get_client()
    ftp = get_ftp()
    newest = date.today() + timedelta(days=1)
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    plan, missed = reconcile(plan, events, ftp=ftp,
                             training_days=get_training_days())
    meta = load_plan_meta(PLAN_FILE)
    save_plan(plan, PLAN_FILE, goal=meta["goal"], race_date=meta["race_date"],
              ftp_test_date=meta["ftp_test_date"],
              ftp_candidates=meta["ftp_candidates"])
    print(describe_training_days(env_value=os.environ.get("TRAINING_DAYS", "")))
    if missed:
        print(f"Treinos perdidos detectados: {[m['day'] for m in missed]}")
        print("Plano ajustado: recuperacao inserida e proximo limiar reduzido.")
    else:
        print("Nenhum treino perdido; plano mantido.")
    hr_hint = _hr_mode_hint()
    if hr_hint:
        print(hr_hint)
    if args.show:
        for w in plan:
            print(f"  {w['day']} {w['name']:<30} TSS {w['tss']:.0f}")
    return plan


def get_cue_lang():
    load_env(PROJECT_ROOT / ".env")
    lang = os.environ.get("CUE_LANG", "pt").strip().lower()
    if lang not in CUE_LANGS:
        print(f"aviso: CUE_LANG={lang!r} invalido; usando 'pt'")
        return "pt"
    return lang


def _prev_same_focus(plan, workout):
    """Treino anterior do mesmo foco no plano (para mensagem de progressao)."""
    prev = None
    for w in plan:
        if w["focus"] == workout["focus"] and w["day"] < workout["day"]:
            prev = w
    return prev


def cmd_ftp_scan(args):
    """Examina treinos feitos fora do plano (janela) e propoe novo FTP.

    Fluxo (issue #6): eventos pareados nao-hermes -> detalhe -> filtros baratos
    -> stream de watts -> analise local (20 min x 0.95) -> relatorio ->
    confirmacao obrigatoria -> .env FTP + PUT indoor_ftp no Intervals."""
    client = get_client()
    ftp = get_ftp()
    newest = date.today() + timedelta(days=1)
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    extras = ftp_scan.extra_activities(events)
    if not extras:
        print(f"Sem treinos fora do plano na janela de {args.days} dias.")
        return None
    print(f"Treinos fora do plano na janela de {args.days} dias: {len(extras)}")
    scanned = []
    for e in extras:
        activity = client.activity(e["activity_id"])
        reason = ftp_scan.skip_reason(activity, ftp)
        if reason:
            print(f"  - {e['day']} {e['name'][:44]:<44} ignorado ({reason})")
            continue
        streams = client.activity_streams(e["activity_id"],
                                          types=("watts", "time"))
        rec = ftp_scan.estimate_ride(e["activity_id"], e["day"], e["name"],
                                     activity, streams.get("watts") or [],
                                     streams.get("time") or [], ftp)
        scanned.append(rec)
        status = ("-> sugere FTP" if rec["suggests_new"] else
                  "-> sem novidade" if rec["quality_ok"] else "-> invalido")
        print(f"  - {e['day']} {e['name'][:36]:<36} "
              f"20min {rec['best20']:.0f}W | prop {rec['proposed_ftp']}W "
              f"{status} {rec['reason']}".rstrip())
    if not scanned:
        print("Nenhum treino analisavel na janela.")
        return None

    valid = [c for c in scanned if c["suggests_new"]]
    if not valid:
        _record_ftp_candidates(scanned)
        print("Nenhum candidato valido: os esforcos fora do plano nao "
              "sustentam novo FTP agora.")
        return scanned

    chosen = ftp_scan.best_candidate(valid)
    print("\nCandidato a aplicar:")
    print(f"  {chosen['day']} {chosen['name']} ({chosen['activity_id']}): "
          f"FTP {ftp}W -> {chosen['proposed_ftp']}W "
          f"(20min {chosen['best20']:.0f}W x 0.95)")
    answer = input("Aplicar novo FTP no .env e no Intervals (indoor_ftp)? "
                   "(s/N) ").strip().lower()
    _record_ftp_candidates(scanned)
    if answer != "s":
        print("Nao aplicado; candidato registrado na meta para revisao.")
        return scanned

    _env_set("FTP", str(chosen["proposed_ftp"]))
    bak = PROJECT_ROOT / ".env.bak"
    if bak.exists():
        _env_set("FTP", str(chosen["proposed_ftp"]), path=bak)
    else:
        bak.write_text(ENV_FILE.read_text(encoding="utf-8"),
                       encoding="utf-8")
    settings = client.sport_settings()
    ride = ftp_scan.ride_settings(settings)
    if ride is None:
        print("aviso: entrada Ride das sport-settings nao encontrada; .env "
              "atualizado, Intervals NAO (verifique manualmente).")
    else:
        payload = ftp_scan.sanitize_ride_payload(
            ride, indoor_ftp=chosen["proposed_ftp"])
        st, _ = client.put_sport_settings(ride["id"], payload)
        print(f"Intervals indoor_ftp atualizado (HTTP {st}) "
              f"-> {chosen['proposed_ftp']}W")
    chosen["applied"] = True
    _record_ftp_candidates([chosen])
    print(f"FTP atualizado para {chosen['proposed_ftp']}W "
          "(.env + Intervals).")
    return scanned


def cmd_push(args):
    load_env(PROJECT_ROOT / ".env")
    plan = load_plan(PLAN_FILE)
    client = get_client()
    lang = get_cue_lang()
    ftp = get_ftp()
    fthr = get_fthr()
    start = args.start or (date.today() + timedelta(days=1)).isoformat()
    batch = [event_payload(w, ftp, lang=lang,
                           prev=_prev_same_focus(plan, w), fthr=fthr)
             for w in plan if w["day"] >= start]

    newest = (max((w["day"] for w in plan), default=None)
              or (date.fromisoformat(start) + timedelta(days=120)).isoformat())
    recent = client.events(oldest=start, newest=newest)
    orphans = orphan_external_ids(plan, recent, start=start)

    if args.dry_run:
        print(f"dry-run: enviaria {len(batch)} eventos ao calendario")
        for p in batch:
            print(f"  {p['start_date_local']} {p['name']}")
        if orphans:
            print(f"dry-run: removeria {len(orphans)} orfaos: {orphans}")
        return

    if orphans:
        st, body = client.delete_events(orphans)
        print(f"Orfaos removidos (HTTP {st}): {body.get('eventsDeleted')}")
    status, body = client.create_events(batch)
    print(f"Calendario atualizado (HTTP {status}): {len(body)} eventos")


def cmd_all(args):
    cmd_build(args)
    cmd_reconcile(args)
    cmd_push(args)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Plano de treinos Hermes: historico -> plano -> calendario")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="Mostra TSB/CTL/ATL atuais")
    p_info.add_argument("--days", type=int, default=60)
    p_info.set_defaults(func=cmd_info)

    p_ftp = sub.add_parser("ftp-check", help="Indica se ja e hora de (re)fazer um teste de FTP")
    p_ftp.add_argument("--days", type=int, default=120,
                       help="Janela de historico para procurar o ultimo teste (dias)")
    p_ftp.add_argument("--weeks", type=int, default=8,
                       help="Janela em semanas entre testes")
    p_ftp.set_defaults(func=cmd_ftp_check)

    p_scan = sub.add_parser(
        "ftp-scan",
        help="Examina treinos fora do plano e propoe novo FTP (issue #6)")
    p_scan.add_argument("--days", type=int, default=45,
                        help="Janela de historico de treinos fora do plano (dias)")
    p_scan.set_defaults(func=cmd_ftp_scan)

    p_check = sub.add_parser(
        "check",
        help="Prontidao do dia: wellness + sugestao de troca (nao obrigatoria)")
    p_check.add_argument("--days", type=int, default=14,
                         help="Janela de wellness a considerar (dias)")
    p_check.add_argument("--apply", action="store_true",
                         help="Aplica a troca sugerida (recuperacao leve) no "
                              "plan.json; rode `push` para publicar")
    p_check.set_defaults(func=cmd_check)

    p_per = sub.add_parser(
        "periodization",
        help="Explica os modelos de periodizacao e sugere para o GOAL atual")
    p_per.add_argument("--model", metavar="NOME",
                       help="Detalha um modelo especifico "
                            "(polarized|pyramidal|undulating|linear|block)")
    p_per.add_argument("--no-tsb", action="store_true",
                       help="Nao consulta o TSB ao sugerir")
    p_per.add_argument("--days", type=int, default=60,
                       help="Janela de historico para o TSB (dias)")
    p_per.set_defaults(func=cmd_periodization)

    p_model = sub.add_parser(
        "model",
        help="Metricas do motor Banister local vs Intervals + projecao do plano")
    p_model.add_argument("--days", type=int, default=60,
                         help="Janela de historico de TSS (dias)")
    p_model.set_defaults(func=cmd_model)

    p_adh = sub.add_parser(
        "adherence",
        help="Relatorio de cumprimento do plano por semana (feito/perdido/pendente)")
    p_adh.add_argument("--days", type=int, default=45,
                       help="Janela de historico de eventos para casar (dias)")
    p_adh.set_defaults(func=cmd_adherence)

    p_rec = sub.add_parser(
        "recovery",
        help="Historico real -> PMC -> estimativa de retorno a antiga forma + "
             "prescricao segura de rampa de volume")
    p_rec.add_argument(
        "--weeks", type=int, default=12,
        help="Semanas da prescricao segura de rampa (0 = so a estimativa)")
    p_rec.add_argument("--ramp-pts", type=int, default=9,
                       help="Crescimento semanal de TSS na prescricao (default 9)")
    p_rec.set_defaults(func=cmd_recovery)

    p_sum = sub.add_parser(
        "summary",
        help="Resumo dos treinos feitos por periodo: dia/semana/mes/"
             "trimestre/semestre/ano, duracao (45d/6m/1y), plan ou custom")
    p_sum.add_argument(
        "--period", default="day",
        help="Janela do resumo: day|week|month|quarter|semester|year, "
             "duracao livre (ex.: 45d, 6m, 1y), plan (do inicio ao fim do "
             "plano salvo) ou custom (com --start/--end); default: day")
    p_sum.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Dia-ancla do periodo (default: ontem)")
    p_sum.add_argument(
        "--start", metavar="YYYY-MM-DD",
        help="Inicio do periodo (custom; com --end)")
    p_sum.add_argument(
        "--end", metavar="YYYY-MM-DD",
        help="Fim do periodo (custom; com --start)")
    p_sum.add_argument(
        "--chart", choices=("auto", "none", "pmc", "load", "all"),
        default="auto",
        help="Graficos no resumo: PMC CTL/ATL/TSB + carga semanal "
             "(default auto = PMC sempre + carga p/ semana/mes)")
    p_sum.add_argument(
        "--export", metavar="ARQUIVO",
        help="Exporta o resumo com graficos (SVG) para um arquivo; "
             "a extensao decide o formato: .html direto, .pdf via chromium "
             "headless")
    p_sum.add_argument(
        "--theme", metavar="TEMA",
        help=f"Tema do relatorio (default: {report.DEFAULT_THEME}); no HTML "
             "o leitor pode trocar pelo menu (tecla T). Temas: "
             + ", ".join(report.THEMES))
    p_sum.set_defaults(func=cmd_summary)

    p_build = sub.add_parser("build", help="Gera o plano a partir do historico")
    p_build.add_argument("--days", type=int, default=60,
                         help="Janela de historico (dias)")
    p_build.add_argument("--days-plan", type=int, default=14,
                         help="Quantos dias olhar para frente")
    p_build.add_argument("--ftp-test", metavar="YYYY-MM-DD",
                         help="Agenda o Ramp Test (FTP) e protege as 48h antes")
    p_build.add_argument("--no-power", action="store_true",
                         help="Prescricao sem medidor de potencia: alvos em "
                              "%%FTHR + RPE (exige FTHR no .env)")
    p_build.set_defaults(func=cmd_build)

    p_rec = sub.add_parser("reconcile",
                           help="Compara plano x treinos feitos e ajusta")
    p_rec.add_argument("--days", type=int, default=14)
    p_rec.add_argument("--show", action="store_true")
    p_rec.set_defaults(func=cmd_reconcile)

    p_push = sub.add_parser("push", help="Publica o plano")
    p_push.add_argument("--start", help="Publica apenas a partir desta data (YYYY-MM-DD)")
    p_push.add_argument("--dry-run", action="store_true")
    p_push.set_defaults(func=cmd_push)

    p_all = sub.add_parser("all",
                           help="build + reconcile + push (calendario)")
    p_all.add_argument("--days", type=int, default=60)
    p_all.add_argument("--days-plan", type=int, default=14)
    p_all.add_argument("--ftp-test", metavar="YYYY-MM-DD",
                       help="Agenda o Ramp Test (FTP) e protege as 48h antes")
    p_all.add_argument("--no-power", action="store_true",
                       help="Prescricao sem medidor de potencia (%%FTHR + RPE)")
    p_all.add_argument("--recovery", action="store_true",
                       help="Orca o plano pelos tetos da rampa de retorno a forma")
    p_all.add_argument("--ramp-pts", type=int, default=9,
                       help="Crescimento semanal de TSS da rampa (default 9)")
    p_all.add_argument("--recovery-weeks", type=int, default=12,
                       help="Semanas da rampa de retorno (default 12)")
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except IntervalsApiError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    except requests.exceptions.RequestException as exc:
        print("erro: falha de comunicacao com o Intervals.icu "
              f"({exc.__class__.__name__}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
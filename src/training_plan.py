import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS,
                       wellness_summary, format_wellness)
    from intervals_client import IntervalsClient
    from impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                  forecast_pmc)
    from plan import (build_plan, event_payload, load_plan, load_plan_meta,
                      reconcile, save_plan, orphan_external_ids,
                      parse_training_days, parse_goal, parse_weekly_hours,
                      parse_long_day, parse_fthr, GOAL_LABELS, FOCUS_LABELS_PT,
                      REST, DEFAULT_FTP, CUE_LANGS, GOALS, adherence_report,
                      _tsb_race_verdict)
    import ftp_scan
    import recovery
    import activity_summary
    import charts
    import report
except ImportError:
    from .coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS,
                        wellness_summary, format_wellness)
    from .intervals_client import IntervalsClient
    from .impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                   forecast_pmc)
    from .plan import (build_plan, event_payload, load_plan, load_plan_meta,
                       reconcile, save_plan, orphan_external_ids,
                       parse_training_days, parse_goal, parse_weekly_hours,
                       parse_long_day, parse_fthr, GOAL_LABELS,
                       FOCUS_LABELS_PT, REST, DEFAULT_FTP, CUE_LANGS, GOALS,
                       adherence_report, _tsb_race_verdict)
    from . import ftp_scan
    from . import recovery
    from . import activity_summary
    from . import charts
    from . import report

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
    local = engine.compute_metrics(series)
    api = latest_metrics(events)
    print(f"eventos na janela: {len(events)} | dias com TSS: {len(series)}")
    print(f"Motor local (Banister): CTL {local['ctl_fitness']} / "
          f"ATL {local['atl_fatigue']} / TSB {local['tsb_form']}")
    if api and api.ctl is not None and api.atl is not None:
        print(f"Intervals.icu        : CTL {api.ctl:.1f} / "
              f"ATL {api.atl:.1f} / TSB {api.tsb:.1f}")
        print(f"Diferenca            : CTL {local['ctl_fitness'] - api.ctl:+.1f} / "
              f"ATL {local['atl_fatigue'] - api.atl:+.1f} / "
              f"TSB {local['tsb_form'] - api.tsb:+.1f}")
    else:
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
    plan = build_plan(events, tsb, ftp=ftp, days=args.days_plan,
                      existing=existing, training_days=get_training_days(),
                      goal=goal, race_date=race_date, ftp_test_date=ftp_test_date,
                      weekly_hours=weekly_hours, long_day=long_day,
                      hr_mode=hr_mode)
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
    race_info = f" | prova em {race_date}" if goal == "race" and race_date else ""
    test_info = f" | Ramp Test em {ftp_test_date}" if ftp_test_date else ""
    print(f"Plano: {plano_label}{race_info}{test_info} | TSB atual {tsb:.1f} | FTP {ftp}W")
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
    """Historico real do Intervals -> PMC reconstruido -> estimativa de
    retorno a antiga forma + prescricao segura de rampa de volume.

    Usa somente treinos FEITOS (com atividade pareada); planejado-nao-feito nao
    conta como carga real. O pico historico e a melhor janela de 30 dias sao o
    "onde voce esteve"; a estimativa projeta o prazo de volta ao CTL de pico sob
    rampas conservadora/realista/otimista, e a prescricao da a rampa semanal.
    """
    client = get_client()
    events = recovery.fetch_full_history(client)
    done = [e for e in events
            if e.get("paired_activity_id") or e.get("activity_id")]
    daily = recovery.actual_daily_load(events)
    rows = recovery.pmc_series(daily)
    if not rows:
        print("Sem treinos feitos com carga no historico.")
        return None
    st = recovery.state(rows)
    print(f"historico: {len(events)} eventos | treinos feitos com carga: "
          f"{len(done)}")
    print(f"periodo coberto: {st['first_day']} a {st['last_day']}")

    print("\n=== AGORA ===")
    vol = recovery.weekly_volume(daily)
    print(f"CTL {st['current_ctl']:.1f} | ATL {st['current_atl']:.1f} | "
          f"TSB {st['current_tsb']:+.1f}")
    print(f"volume semanal recente (28d): {vol:.0f} TSS")

    print("\n=== ONDE VOCE JA ESTEVE ===")
    print(f"pico de CTL: {st['peak_ctl']:.1f} em {st['peak_ctl_day']} "
          f"(TSB {st['peak_ctl_tsb']:+.1f})")
    print(f"melhor mes (CTL medio 30d): {st['window_avg']:.1f} "
          f"({st['window_start']} a {st['window_end']})")
    print(f"pico de TSB: {st['peak_tsb']:+.1f} em {st['peak_tsb_day']} "
          f"(CTL {st['peak_tsb_ctl']:.1f})")

    target = st["peak_ctl"]
    print("\n=== ESTIMATIVA DE RETORNO AO CTL "
          f"{target:.0f} ===")
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
        print(f"  {label}: 90% em {w90} | 100% em {w99}")
    print(f"  (sustentar o CTL {target:.0f} exige ~"
          f"{target * 7:.0f} TSS/semana)")

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
        print("  Dica: gere os treinos em si com `build` e `GOAL=back-to-fitness`")
        print("  respeitando esses tetos semanais; valide a prescricao com o treinador.")
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
    """Resumo dos treinos FEITOS por periodo (dia/semana/mes).

    Janela terminando no dia-ancla (por padrao, ontem): dia = 1 dia, semana =
    7 dias, mes = 30 dias. Usa apenas atividades pareadas (planejado-nao-feito
    fica fora).
    """
    client = get_client()
    anchor = args.date or (date.today() - timedelta(days=1))
    theme = getattr(args, "theme", None)
    if theme and theme not in report.THEMES:
        raise SystemExit(
            f"Tema invalido: {theme!r}. Temas disponiveis: "
            + ", ".join(report.THEMES))
    start, end = activity_summary.period_range(anchor, args.period)
    rows = activity_summary.done_activities(client, start, end)
    agg = activity_summary.summarize(rows)

    label = activity_summary.PERIOD_LABELS[args.period]
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

    _summary_charts(client, args.period, anchor, rows, args.chart)
    _summary_export(client, args, anchor, rows, agg, start, end)
    return agg


def _summary_chart_data(client, period, anchor, rows):
    """Dados dos graficos do resumo: (pmc_rows, weeks).

    `pmc_rows` = serie (day, ctl, atl, tsb) trailing 90d; `weeks` =
    carga semanal ISO ([]) quando `period` == dia.
    """
    start = anchor - timedelta(days=89)
    events = client.events(oldest=start.isoformat(), newest=anchor.isoformat())
    daily = recovery.actual_daily_load(events)
    pmc_rows = [r for r in recovery.pmc_series(daily) if start <= r[0] <= anchor]
    if period == "day":
        return pmc_rows, []
    return pmc_rows, charts.weekly_load(rows)


def _summary_charts(client, period, anchor, rows, chart):
    """Graficos do resumo (padrao Pillar/Analog 'dashboard de 90 dias').

    PMC (trailing 90d) sempre em `auto`; barras de carga semanal apenas para
    semana/mes (ja que sai dos proprios treinos do periodo). `--chart none`
    desliga; `--chart pmc|load|all` escolhe um.
    """
    if chart == "none":
        return
    pmc_rows, weeks = _summary_chart_data(client, period, anchor, rows)
    pmc_parts = charts.pmc_chart(pmc_rows) if chart in ("auto", "all", "pmc") else []
    load_parts = (charts.load_chart(weeks)
                  if chart in ("auto", "all", "load") and period != "day"
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


def _summary_export(client, args, anchor, rows, agg, start, end):
    """Exporta (--export) o resumo com graficos em SVG para HTML/PDF.

    A extensao do caminho decide: .html escreve direto; .pdf renderiza o HTML
    via chromium headless. Nao altera a saida no terminal.
    """
    path = getattr(args, "export", None)
    if not path:
        return
    pmc_rows, weeks = _summary_chart_data(client, args.period, anchor, rows)
    theme = getattr(args, "theme", None) or report.DEFAULT_THEME
    html = report.render_summary_html(
        title=(f"Resumo {activity_summary.PERIOD_LABELS[args.period]}"
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
        help="Resumo dos treinos feitos por periodo: dia/semana/mes")
    p_sum.add_argument(
        "--period", choices=("day", "week", "month"), default="day",
        help="Janela do resumo (default: dia)")
    p_sum.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Dia-ancla do periodo (default: ontem)")
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
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
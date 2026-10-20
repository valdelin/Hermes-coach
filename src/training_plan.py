import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

if __package__ in (None, ""):
    # Execucao direta mantem `src/` como diretorio do script (imports legados
    # top-level), mas dependencias transitivas tambem usam `src.*`. A raiz do
    # projeto torna esse pacote disponivel sem a Application manipular paths.
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.append(project_root)

try:
    from coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS,
                       wellness_summary, format_wellness, real_pmc_by_day)
    from intervals_client import IntervalsClient, IntervalsApiError
    from intervals_adapter import IntervalsAdapter
    from impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                  forecast_pmc)
    from plan import (build_plan, event_payload, load_plan, load_plan_meta,
                       reconcile, save_plan, orphan_external_ids,
                        manual_duplicate_ids,
                        parse_training_days, parse_goal, parse_weekly_hours,
                        parse_min_regular_duration_minutes,
                        parse_active_recovery_days,
                        parse_long_day, parse_fthr, parse_periodization,
                      GOAL_LABELS, FOCUS_LABELS_PT, PERIODIZATIONS,
                      PERIODIZATION_LABELS, REST, DEFAULT_FTP, CUE_LANGS,
                      GOALS, adherence_report, _tsb_race_verdict,
                      GOAL_BUDGET_SCALE, weekly_budget, avg_load,
                       BUDGET_WINDOW_DAYS, SITUACOES_READINESS,
                       readiness_eligibility, TSB_ADAPT_LIMIT,
                       planned_workout_profile, FTP_TEST_INTENT_KEY)
    import ftp_scan
    import ftp_evidence
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
    from .intervals_adapter import IntervalsAdapter
    from .impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                   forecast_pmc)
    from .plan import (build_plan, event_payload, load_plan, load_plan_meta,
                       reconcile, save_plan, orphan_external_ids,
                        manual_duplicate_ids,
                        parse_training_days, parse_goal, parse_weekly_hours,
                       parse_min_regular_duration_minutes,
                       parse_active_recovery_days,
                       parse_long_day, parse_fthr, parse_periodization,
                      GOAL_LABELS, FOCUS_LABELS_PT, PERIODIZATIONS,
                      PERIODIZATION_LABELS, REST, DEFAULT_FTP, CUE_LANGS,
                      GOALS, adherence_report, _tsb_race_verdict,
                      GOAL_BUDGET_SCALE, weekly_budget, avg_load,
                       BUDGET_WINDOW_DAYS, planned_workout_profile,
                       FTP_TEST_INTENT_KEY)
    from .plan import (build_plan, event_payload, load_plan, load_plan_meta,
                       reconcile, save_plan, orphan_external_ids,
                      manual_duplicate_ids,
                       parse_training_days, parse_goal, parse_weekly_hours,
                       parse_long_day, parse_fthr, parse_periodization,
                       GOAL_LABELS, FOCUS_LABELS_PT, PERIODIZATIONS,
                       PERIODIZATION_LABELS, REST, DEFAULT_FTP, CUE_LANGS,
                       GOALS, adherence_report, _tsb_race_verdict,
                      GOAL_BUDGET_SCALE, weekly_budget, avg_load,
                       BUDGET_WINDOW_DAYS, SITUACOES_READINESS,
                       readiness_eligibility, TSB_ADAPT_LIMIT,
                       planned_workout_profile, FTP_TEST_INTENT_KEY)
    from . import ftp_scan
    from . import ftp_evidence
    from . import recovery
    from . import activity_summary
    from . import charts
    from . import report
    from . import readiness
    from . import periodization

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "plan.json"
ENV_FILE = PROJECT_ROOT / ".env"

try:
    from application import (load_env, get_env, Application, build_workouts,
                             reconcile_workouts, push_workouts,
                             summarize_period, recovery_outlook,
                             assess_daily_readiness)
except Exception:
    from .application import (load_env, get_env, Application, build_workouts,
                              reconcile_workouts, push_workouts,
                              summarize_period, recovery_outlook,
                              assess_daily_readiness)


def get_client():
    load_env(PROJECT_ROOT / ".env")
    athlete_id = os.environ.get("INTERVALS_ATHLETE_ID")
    api_key = os.environ.get("INTERVALS_API_KEY")
    if not athlete_id or not api_key:
        sys.exit("Faltam INTERVALS_ATHLETE_ID/INTERVALS_API_KEY no .env")
    return IntervalsClient(athlete_id, api_key)


def get_provider() -> "IntervalsAdapter":
    """Composition root do provider (UI-3): client cru do Intervals por tras do
    adapter, que traduz para os contratos normalizados da Application."""
    return IntervalsAdapter(get_client())


def _make_app(client_factory=None) -> "Application":
    """Composition root da CLI: injeta explicitamente um provider (o adapter do
    Intervals por padrao) e nao deixa a Application resolver um global por conta
    propria. Isso mantem a fronteira de mock dos testes intacta e evita que a
    camada de aplicacao localize dependencias globais sozinha."""
    if client_factory is None:
        client_factory = get_provider
    return Application(plan_path=PLAN_FILE, env_path=ENV_FILE,
                       client_factory=client_factory)


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


def get_active_recovery_days():
    load_env(PROJECT_ROOT / ".env")
    return parse_active_recovery_days(
        os.environ.get("ACTIVE_RECOVERY_DAYS", ""), get_training_days())


def get_min_regular_duration_sec():
    """Duracao minima opcional das sessoes regulares, em segundos."""
    load_env(PROJECT_ROOT / ".env")
    value = os.environ.get("MIN_REGULAR_DURATION_MINUTES", "")
    duration = parse_min_regular_duration_minutes(value)
    if value.strip() and duration is None:
        print("aviso: MIN_REGULAR_DURATION_MINUTES="
              f"{value!r} invalido; sem minimo de duracao regular")
    return duration


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
    build protege as 48h antes do teste e cria o evento informativo do
    teste de FTP (sem passos prescritivos, ver FTP-H8)."""
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
              ftp_test_date=meta["ftp_test_date"], ftp_candidates=merged,
              absorbed_ids=meta["absorbed_ids"])
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
        raw = input("Qual a data do teste de FTP? (YYYY-MM-DD) ").strip()
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
            client = _make_app().client()
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
    client = _make_app().client()
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


def _agora():
    """Instante local usado para avaliar a sessao de hoje.

    Ponto unico de leitura do relogio, para que os testes possam congelar o
    horario sem refatorar `date.today()` no resto do projeto. O projeto nao tem
    configuracao de fuso suportada (ver `readiness_eligibility`), entao "local"
    aqui e o horario local da maquina, que e o que todo o resto do motor usa.
    """
    return datetime.now()


def cmd_check(args):
    """Prontidao do dia (#31 / #58 Passo A): avalia a sessao de HOJE.

    Este e o ponto de entrada diario da avaliacao. Ele existe desde a #31 como
    "sugere uma troca", mas usava o motor legado (`assess_readiness` /
    `suggest_swap` / `recovery_workout`), que trocava a sessao por Z2 900 s
    diante de QUALQUER sinal ligado e nao checava se o treino ja tinha
    acontecido. Agora:

    - a decisao vem do mesmo motor do `build` (`readiness_decision` +
      `_adapt_session`), entao `check` e `build` nao podem divergir;
    - a leitura vale para o dia que ela DESCREVE, e nao e transferida;
    - a sessao so e tocada se ainda nao tiver comecado, com base no que o
      Intervals efetivamente informa (`readiness_eligibility`);
    - `NONE` ou dado ausente nao mexem em nada.

    Tres etapas, deliberadamente separadas:

    1. PROPOSTA  — sempre calculada e impressa (inclusive sem `--apply`);
    2. APLICACAO — so com `--apply`, e so se a sessao for elegivel. Escreve
       apenas no `plan.json` local; `--dry-run` bloqueia essa escrita;
    3. PUBLICACAO — nunca aqui. Continua sendo o `push`, comando separado.

    O alerta de doenca e o `COACH_WEBHOOK` seguem como na #31.
    """
    app = _make_app()
    today = date.today()
    plan = app.load_plan()
    meta = app.load_plan_meta()
    # Orquestracao (events/wellness/prontidao/elegibilidade/sem-com) vive no
    # caso de uso; aqui so ha leitura de args, formatacao e `--apply`.
    result = assess_daily_readiness(
        app.client(),
        plan=plan,
        meta=meta,
        today=today,
        now=_agora(),
        days=args.days,
        ftp=get_ftp(),
        training_days=get_training_days(),
        weekly_hours=get_weekly_hours(),
        active_recovery_days=get_active_recovery_days(),
        min_regular_duration_sec=get_min_regular_duration_sec(),
        long_day=get_long_day(),
        periodization=get_periodization(),
        tsb_adapt_limit=TSB_ADAPT_LIMIT,
        latest_metrics_fn=latest_metrics,
        build_plan_fn=build_plan,
        readiness_module=readiness,
        eligibility_fn=readiness_eligibility,
    )
    metrics = result.metrics
    if metrics:
        print(f"TSB {metrics.tsb:.1f} (CTL {metrics.ctl:.1f} / "
              f"ATL {metrics.atl:.1f})")
    else:
        print("TSB: sem metricas na janela.")

    # --- Etapa 0: estado da sessao de hoje -------------------------------
    treino = result.treino
    elegibilidade = result.elegibilidade
    if treino is not None:
        print(f"Treino de hoje: {treino['name']} "
              f"({treino['planned_duration'] // 60}m, "
              f"TSS {treino['tss']:.0f})")
    else:
        print("Hoje nao tem treino no plano.")
    print(f"Estado da sessao: {elegibilidade.state} ({elegibilidade.reason})")

    # --- Etapa 1: proposta ------------------------------------------------
    decisao = result.decisao
    trace = result.trace
    print(f"Prontidao: {decisao.reason}")
    if trace.illness_alert:
        print("ALERTA DE DOENCA: considere descanso e monitore amanha.")
        # O payload de alerta da #31 fala do `Readiness` legado, entao o
        # webhook continua recebendo aquele objeto. A DECISAO do Passo A e a
        # que governa a sessao; as duas nao sao misturadas.
        _notify_coach_if_configured(
            readiness.assess_readiness(result.wellness, days=args.days), today)

    if result.status == "not_adaptive":
        print("Sem alteracao por prontidao: "
              + ("nao ha dado de wellness para avaliar."
                 if result.avaliacao is None
                 else "a leitura nao pede adaptacao."))
        return None

    # Validade temporal: a leitura so vale para o dia que descreve.
    if result.status == "wrong_day":
        quando = decisao.applies_to_day or "dia desconhecido"
        print(f"Leitura de {quando} nao descreve hoje ({today.isoformat()}); "
              "nao foi transferida para outra sessao.")
        return None

    if result.status == "not_eligible":
        print(f"Proposta: nao aplicada — {elegibilidade.reason}.")
        return None

    # --- Etapa 1b: proposta concreta, pelo MESMO motor do build ------------
    # Nao existe um segundo motor aqui. `check` chama `build_plan` com
    # `start=hoje` e compara TRES versoes do mesmo dia:
    #
    #   sem   = build_plan(..., start=hoje, readiness=None)
    #   com   = build_plan(..., start=hoje, readiness=decisao)
    #   atual = o que esta no plan.json
    #
    # Isso resolve a cumulatividade por construcao: `build_plan` SEMPRE
    # reconstrue o dia a partir do template, entao rodar `check --apply` duas
    # vezes com a mesma leitura produz a MESMA proposta, e nao 38 -> 30 -> 22.
    # E o default de `start=None` (amanha) fica intacto: quem pede hoje e
    # explicitamente o `check`.
    tsb = result.tsb
    sem, com = result.sem, result.com
    autor = result.autor

    if result.status == "tsb_wins":
        # A regra mais restritiva venceu e foi o TSB: a leitura nao
        # acrescenta nada. Dizer isso e melhor que um "nada a alterar"
        # opaco, porque o operador precisa saber que o TSB ja manda.
        print(f"Proposta: nada atribuivel a prontidao — o TSB "
              f"({tsb:.0f}) ja determina a sessao de hoje "
              f"({sem['tss']:.0f} TSS). A leitura nao acrescenta nada e "
              "nao recebe credito no orcamento; `build` e a autoridade "
              "do TSB.")
        return None
    if result.status == "nothing":
        print("Proposta: nada a alterar.")
        return None
    if result.status == "already":
        print("Proposta: ja aplicada a sessao de hoje; "
              "reexecucoes com a mesma leitura nao reduzem de novo.")
        return com
    if result.status == "divergent":
        # O plan.json diverge da reconstrucao sem prontidao, entao a diferenca
        # NAO e atribuivel a leitura de hoje. Propoe e nao aplica.
        print(f"Proposta: a sessao de hoje no plano ({treino['tss']:.0f} TSS) "
              f"diverge da reconstrucao sem prontidao ({sem['tss']:.0f} TSS), "
              "entao a diferenca nao e atribuivel a leitura de hoje. "
              "Rode `build` para repor a base antes de aplicar.")
        return com
    print(f"PROPOSTA ({autor}): {treino['name']} -> {com['name']} "
          f"(TSS {treino['tss']:.0f} -> {com['tss']:.0f}, "
          f"{treino['planned_duration'] // 60}m -> "
          f"{com['planned_duration'] // 60}m, "
          f"foco {treino['focus']} -> {com['focus']}).")

    # --- Etapa 2: aplicacao local, so com --apply -------------------------
    if not getattr(args, "apply", False):
        print("Nada foi gravado. Rode `check --apply` para gravar a proposta "
              "no plan.json, ou `build` para repropor o plano inteiro.")
        return com
    if getattr(args, "dry_run", False):
        print("[dry-run] proposta NAO gravada em "
              f"{PLAN_FILE.name}; nada foi publicado.")
        return com
    novo_plano = [com if w["day"] == today.isoformat() else w for w in plan]
    app.save_plan(novo_plano, goal=meta.get("goal"),
                  race_date=meta.get("race_date"),
                  ftp_test_date=meta.get("ftp_test_date"),
                  ftp_candidates=meta.get("ftp_candidates"),
                  absorbed_ids=meta["absorbed_ids"])
    print(f"Aplicado no {PLAN_FILE.name}: sessao de hoje ajustada por "
          f"{autor}. O plano NAO foi publicado no calendario.")
    print("Rode `push` para publicar. A proposta so vai ao calendario por "
          "essa etapa explicita.")
    return com


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
    client = _make_app().client()
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
        print("Sugestao: agende um teste de FTP na plataforma que voce usa em um dia descansado;")
        print("  rode `build --ftp-test YYYY-MM-DD` para proteger as 48h antes")
        print("  (D-2 facil, D-1 spin) e publicar o evento do teste no plano.")
    hint = _pending_ftp_hint()
    if hint:
        print(hint)


def cmd_model(args):
    client = _make_app().client()
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
    app = _make_app()
    newest = date.today()
    # UI-5: presenca/periodo do plano vem da View (contrato de leitura); o
    # provider so entra para o cruzamento com o que foi de fato feito.
    state = app.get_application_state(today=newest)
    if not state.plan.has_plan:
        print("sem plan.json: rode `build` primeiro.")
        return
    client = app.client()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    report = adherence_report(app.load_plan(), events)
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
    app = _make_app()
    provider = app.client()
    ftp = get_ftp()
    fthr = get_fthr()
    goal = get_goal()
    periodization = get_periodization()
    race_date = get_race_date()
    weekly_hours = get_weekly_hours()
    min_regular_duration_sec = get_min_regular_duration_sec()
    active_recovery_days = get_active_recovery_days()
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
    existing = app.load_plan() or None
    dry_run = bool(getattr(args, "dry_run", False))
    # Orquestracao (events/wellness/prontidao/rampa/plano) vive no caso de uso.
    result = build_workouts(
        provider,
        today=date.today(),
        days=args.days,
        days_plan=args.days_plan,
        ftp=ftp,
        fthr=fthr,
        goal=goal,
        periodization=periodization,
        race_date=race_date,
        weekly_hours=weekly_hours,
        min_regular_duration_sec=min_regular_duration_sec,
        active_recovery_days=active_recovery_days,
        long_day=long_day,
        hr_mode=hr_mode,
        ftp_test_date=ftp_test_date,
        training_days=get_training_days(),
        existing=existing,
        latest_metrics_fn=latest_metrics,
        build_plan_fn=build_plan,
        readiness_module=readiness,
        recovery_module=recovery,
        pmc_rows_fn=_pmc_rows,
        recovery=getattr(args, "recovery", False),
        ramp_pts=getattr(args, "ramp_pts", 9),
        recovery_weeks=getattr(args, "recovery_weeks", 12),
        phase_report={},
    )
    plan = result.plan
    if result.recovery_warning:
        print(result.recovery_warning)
    if dry_run:
        # `--dry-run` mostra a proposta (ja adaptada) e NAO toca em disco.
        # Publicacao e sempre um comando separado (`push`), que continua
        # exigindo aprovacao explicita; aqui nao ha nada a publicar.
        print(f"[dry-run] plano adaptado nao seria gravado em {PLAN_FILE.name}; "
              "nada foi publicado.")
    else:
        # Preserva estado registrado na meta: build nao apaga candidatos de FTP
        # nem marcas de faltas ja absorvidas.
        existing_meta = app.load_plan_meta()
        app.save_plan(plan, goal=goal, race_date=race_date,
                      ftp_test_date=ftp_test_date,
                      ftp_candidates=existing_meta.get("ftp_candidates"),
                      absorbed_ids=existing_meta["absorbed_ids"])
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
    test_info = f" | Teste de FTP em {ftp_test_date}" if ftp_test_date else ""
    print(f"Plano: {plano_label}{race_info}{test_info} | TSB atual {result.tsb:.1f} | FTP {ftp}W")
    _print_readiness_decision(result.decisao, result.trace, dry_run,
                              result.readiness_report)
    if result.ramp_label:
        print(result.ramp_label)
    if hr_mode:
        print(f"Prescricao sem medidor de potencia: alvos em %FTHR + RPE "
              f"(FTHR {fthr} bpm); carga estimada por FC no Intervals.")
    _print_phase_advisory(result.phase_report)
    est_tss = sum(w["tss"] for w in plan)
    print(f"Plano gerado: {len(plan)} treinos | TSS estimado {est_tss:.0f}"
          + (" | preparacao p/ teste em " + ftp_test_date
             if ftp_test_date and any(
                 w.get(FTP_TEST_INTENT_KEY) for w in plan)
             else ""))
    for w in plan:
        print(f"  {w['day']} {w['name']:<30} {w['planned_duration'] // 60:>3}m TSS {w['tss']:.0f}")
    if goal == "race" and race_date:
        _print_race_tsb_projection(result.events, plan, result.metrics,
                                   race_date)
    return plan


def _print_phase_advisory(phase_report):
    """Rotulo advisory da fase do plano (observacional; nao e recomendacao).

    Deriva do `phase_report` preenchido pelo seam do `build_plan`. O rotulo
    nao entra no nome da sessao, no plan.json nem no payload do Intervals.
    """
    fases = sorted({entrada["phase"] for entrada in phase_report.values()})
    if fases:
        print(f"Fase do plano: {', '.join(fases)}")


def _print_readiness_decision(decisao, trace, dry_run=False, report=None):
    """Explica a decisao de prontidao que moldou o plano (issue #58 Passo A).

    Explicito por tres razoes:

    1. **Rastreabilidade.** O atleta ve a cobertura e os eixos realmente
       observados, nao so um veredito. Ele precisa distinguir "prontidao ruim"
       de "nao ha sensor".
    2. **Legibilidade da adaptacao.** Um plano com `3x480s` onde antes havia
       `4x480s` parece um bug sem esta linha. Aqui ela diz que foi reducao de
       volume por prontidao, em que dia, e que os demais dias nao mudaram.
    3. **Limite do motor.** O alerta de possivel doenca aparece como ALERTA,
       nunca como "diagnostico", e o aviso e explicito: uma sessao leve nao e
       garantia de adequacao para ninguem. O texto e um recurso conservador de
       convencao, nao prescricao clinica.

    Quando a leitura NAO foi aplicada, a linha diz o motivo. Sem isso, um sinal
    ruim que nao chega a tocar em nada seria indistinguivel de "prontidao boa".

    Nao altera `plan.json`: o motivo e saida de CLI, para nao mexer no formato
    persistido.
    """
    verbos = {"none": "sem", "reduce": "REDUZIDO", "replace": "TROCA"}
    print(f"Prontidao: {verbos[decisao.action.value]} | {decisao.reason}")
    if trace.reference_day:
        print(f"  leitura de {trace.reference_day}")
    if trace.observations:
        eixos = ", ".join(
            f"{o.axis.split('_')[0]} {'ruim' if o.flagged else 'ok'}"
            for o in trace.observations)
        print(f"  eixos observados: {eixos} "
              f"(cobertura {decisao.coverage:.0%} de 7; "
              f"{len(trace.missing)} sem fonte hoje)")
    elif trace.missing:
        print(f"  cobertura {decisao.coverage:.0%} de 7 eixos: sem fonte "
              "(Leitura, carga recente, percepcao e consistencia sao derivadas, "
              "nao chegam em /wellness).")
    if trace.stale_days is not None and trace.stale_days > 1:
        print(f"  atencao: ultimo registro ha {trace.stale_days} dias; a "
               "janela pode nao refletir o estado de hoje.")
    if decisao.illness_alert:
        print("  ALERTA: possivel doenca/recuperacao comprometida. Esto nao e "
              "diagnostico. Treino leve nao e garantia de adequacao para ninguem; "
              "avalia com quem te acompanha antes de treinar.")
    if decisao.is_adaptive:
        aplicada_em = (report or {}).get("aplicada_em") or []
        situacao = (report or {}).get("situacao", "aplicada")
        texto = SITUACOES_READINESS.get(situacao, situacao)
        if situacao == "aplicada" and aplicada_em:
            print(f"  efeito: {texto} em {', '.join(aplicada_em)}; os demais "
                  "dias nao ganharam carga.")
        else:
            print(f"  efeito: nao aplicada — {texto}.")
    if dry_run and decisao.is_adaptive:
        print("  (dry-run: proposta acima, nada gravado)")


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
    app = _make_app()
    outlook = recovery_outlook(
        app.client(), recovery_module=recovery, pmc_rows_fn=_pmc_rows,
        ramp_pts=args.ramp_pts, weeks=args.weeks, today=date.today())
    if outlook is None:
        print("Sem treinos feitos com carga no historico.")
        return None
    st_real = outlook.st_real
    st = outlook.st
    vol = outlook.vol
    anchored = outlook.anchored
    print(f"historico: {outlook.event_count} eventos | treinos feitos com "
          f"carga: {outlook.done_count}")
    print(f"periodo coberto: {st_real['first_day']} a {st_real['last_day']}")
    if anchored:
        print("(PMC real do Intervals: serie ancorada nos valores da API)")
    else:
        print("(PMC reconstruido local: sem icu_ctl/icu_atl no historico)")

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

    target = outlook.target
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
        schedule = outlook.schedule
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
    app = _make_app()
    client = app.client()
    anchor = args.date or (date.today() - timedelta(days=1))
    theme = getattr(args, "theme", None)
    if theme and theme not in report.THEMES:
        raise SystemExit(
            f"Tema invalido: {theme!r}. Temas disponiveis: "
            + ", ".join(report.THEMES))
    plan_days = _plan_days() if args.period == "plan" else None
    try:
        result = summarize_period(
            client, period=args.period, anchor=anchor, start=args.start,
            end=args.end, plan_days=plan_days,
            resolve_period_fn=activity_summary.resolve_period,
            done_activities_fn=activity_summary.done_activities,
            summarize_fn=activity_summary.summarize)
    except ValueError as exc:
        raise SystemExit(f"Periodo invalido: {exc}")
    start, end = result.start, result.end
    rows, agg = result.rows, result.agg

    label = activity_summary.period_label(args.period)
    article = "DA" if args.period == "week" else "DO"
    print(f"=== RESUMO {article} {label.upper()} ({start} a {end}) ===")
    if not rows:
        # Ausencia de treino FEITO nao e ausencia de relatorio: o Hermes
        # ainda tem sessao planejada, prontidao, estado do plano,
        # consistencia e contexto de carga. O console mantem a mensagem
        # curta (o comportamento humano nao muda), mas `--export` nao pode
        # abortar aqui -- era esse o early return que engolia o arquivo.
        print("Nenhum treino feito no periodo.")
    else:
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
    _summary_export(app, client, args, start, end, rows, agg, today=date.today())
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


def _planned_profile_for_day(plan, target_day):
    """Perfil do treino canônico daquele dia, ou ``None`` sem sessão.

    A seleção usa a data do objeto persistido; o perfil vem exclusivamente dos
    ``params`` da própria sessão, antes de qualquer renderer HTML.
    """
    target = target_day.isoformat() if isinstance(target_day, date) else str(target_day)
    workout = next((item for item in plan if item.get("day") == target), None)
    return planned_workout_profile(workout) if workout else None


def _report_plan_status(app, target_day):
    """Projeção read-only do lifecycle para o relatório HTML.

    O controller entrega contagens e semanas já classificadas; o renderer só
    apresenta esse estado e não tenta inferir conclusão a partir de texto.
    """
    view = app.plan_view(today=target_day).to_dict()
    buckets = {}
    today_item = None
    for workout in view["workouts"]:
        day = date.fromisoformat(str(workout["day"])[:10])
        state = workout.get("lifecycle_effective")
        kind = ("done" if state == "completed" else
                "missed" if state == "missed" else "pending")
        key = day.isocalendar()[:2]
        bucket = buckets.setdefault(key, {
            "week": f"{key[0]}-W{key[1]:02d}", "done": 0,
            "missed": 0, "pending": 0,
        })
        bucket[kind] += 1
        if workout.get("day") == target_day.isoformat():
            today_item = workout
    weeks = []
    for _, bucket in sorted(buckets.items()):
        occurred = bucket["done"] + bucket["missed"]
        weeks.append({**bucket, "pct": (bucket["done"] / occurred * 100
                                         if occurred else None)})
    summary = {
        key: sum(week[key] for week in weeks)
        for key in ("done", "missed", "pending")
    }
    return {"today": today_item, "weeks": weeks, "summary": summary}


def _vo2_indicators(end=None):
    """VO2max do atleta para o relatorio -- hoje, SEM FONTE REAL.

    Auditoria (PROMPT 37, secoes 29-32): `AthletePhysiologicalProfile.vo2max`
    existe como campo e nunca e preenchido; nao ha campo de provider, nem
    persistencia local, nem serie historica. Devolver `None` e o estado
    honesto -- o renderer mostra "Indisponivel". NUNCA estimar a partir de
    CP/W' ou de potencia: isso fabricaria dado fisiologico.
    """
    return None


def _ftp_indicators(end=None):
    """FTP atual (configuracao real) + serie de FTPs realmente aplicados.

    Atual: a variavel `FTP` do `.env`, a MESMA referencia de potencia que
    `build`/`push` usam. `DEFAULT_FTP` nao e medicao, entao nao preenche o
    indicador quando `FTP` nao esta configurado (secoes 34-35).

    Serie: somente `ftp_candidates` do `plan.json` com `applied=True`
    (`ftp-scan`), que registra o dia em que o FTP foi de fato trocado
    (secao 36). `PlannedWorkout.ftp_watts` NAO entra aqui: ele reproduz a
    prescricao historica da sessao, nao uma medicao de FTP (secao 37).
    Janela: ate 12 meses terminando em `end` (secao 40).
    """
    load_env(PROJECT_ROOT / ".env")
    raw = (os.environ.get("FTP") or "").strip()
    value = int(raw) if raw.isdigit() else None
    origin = ".env FTP" if value is not None else None

    series = []
    meta = load_plan_meta(PLAN_FILE)
    for candidate in (meta.get("ftp_candidates") or {}).values():
        if not isinstance(candidate, dict) or not candidate.get("applied"):
            continue
        day = str(candidate.get("day") or "")[:10]
        watts = candidate.get("proposed_ftp")
        if not day or watts is None:
            continue
        try:
            series.append((day, int(watts)))
        except (TypeError, ValueError):
            continue
    series.sort(key=lambda point: point[0])
    if end is not None:
        cutoff = (end - timedelta(days=365)).isoformat()
        series = [point for point in series if point[0] >= cutoff]

    if value is None and series:
        value, origin = series[-1][1], "FTP aplicado (ftp-scan)"
    measured_on = series[-1][0] if series and value == series[-1][1] else None
    return {"value": value, "unit": "W", "source": origin,
            "date": measured_on, "series": series}


def _summary_export(app, client, args, start, end, rows, agg, *, today=None):
    """Exporta (--export) o resumo com graficos em SVG para HTML/PDF.

    A extensao do caminho decide: .html escreve direto; .pdf renderiza o HTML
    via chromium headless. Nao altera a saida no terminal.
    """
    path = getattr(args, "export", None)
    if not path:
        return
    pmc_rows, weeks = _summary_chart_data(client, start, end, rows)
    target_day = today or date.today()
    plan = app.load_plan()
    profile = _planned_profile_for_day(plan, target_day)
    plan_status = (_report_plan_status(app, target_day)
                   if hasattr(app, "plan_view") else None)
    readiness_view = app.get_readiness_view(today=target_day)
    readiness_data = readiness_view.to_dict() if readiness_view else None
    theme = getattr(args, "theme", None) or report.DEFAULT_THEME
    html = report.render_summary_html(
        title=report.summary_heading(args.period),
        start=start, end=end, agg=agg, rows=rows,
        pmc_rows=pmc_rows, weeks=weeks, planned_workout=profile,
        readiness=readiness_data, plan_status=plan_status,
        vo2=_vo2_indicators(), ftp=_ftp_indicators(end=end), theme=theme)
    report.write(path, html)
    print(f"Exportado: {path}")


def cmd_reconcile(args):
    app = _make_app()
    plan = app.load_plan()
    training_days = get_training_days()
    meta = app.load_plan_meta()
    result = reconcile_workouts(
        app.client(),
        plan=plan,
        meta=meta,
        ftp=get_ftp(),
        training_days=training_days,
        days=args.days,
        today=date.today(),
        budget_window_days=BUDGET_WINDOW_DAYS,
        goal_budget_scale=GOAL_BUDGET_SCALE,
        reconcile_fn=reconcile,
        weekly_budget_fn=weekly_budget,
        avg_load_fn=avg_load,
    )
    plan, missed, info = result.plan, result.missed, result.info
    # `--show` e a fronteira consultiva: calcula e exibe a reconciliacao sem
    # regravar plan.json. Sem a flag, preserva o fluxo mutavel historico.
    if not getattr(args, "show", False):
        app.save_plan(plan, goal=meta["goal"], race_date=meta["race_date"],
                      ftp_test_date=meta["ftp_test_date"],
                      ftp_candidates=meta["ftp_candidates"],
                      absorbed_ids=info["absorbed_ids"])
    print(describe_training_days(env_value=os.environ.get("TRAINING_DAYS", "")))
    if missed:
        print(f"Treinos perdidos detectados: {[m['day'] for m in missed]}")
        absorbed = info["absorbed_tss"]
        lost = info["missed_tss"]
        absorbable = info["absorbable_tss"]
        if absorbed > 0:
            pct = 100.0 * absorbed / absorbable if absorbable else 0.0
            print(f"Plano ajustado: carga redistribuida dentro do orcamento "
                  f"semanal (+{absorbed:.0f} de {absorbable:.0f} TSS absorviveis, "
                  f"{pct:.0f}%).")
        elif info["already_absorbed_tss"] > 0:
            print("Plano mantido: a falta ja foi absorvida em execucao anterior.")
        elif absorbable <= 0:
            print("Plano mantido: falta nao absorvivel por volume "
                  "(active recovery ou alta intensidade); o TSB real "
                  "reprioriza no proximo build.")
        else:
            print("Plano mantido: a falta excede a folga do orcamento "
                  "semanal; absorvida pelo proprio TSB no proximo build.")
        not_replaceable = (lost - absorbable - info["already_absorbed_tss"])
        if not_replaceable > 0.5:
            print(f"  ({not_replaceable:.0f} TSS de alta intensidade nao se "
                  f"substitui com mais volume; ficam para o proximo build.)")
    else:
        print("Nenhum treino perdido; plano mantido.")
    hr_hint = _hr_mode_hint()
    if hr_hint:
        print(hr_hint)
    # `all` chama este comando sem declarar --show; ler args.show direto
    # derrubava o pipeline com AttributeError no caminho real.
    if getattr(args, "show", False):
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
    client = _make_app().client()
    app = _make_app()
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
        if rec["quality_ok"] and rec["proposed_ftp"]:
            _record_scan_evidence(app, rec, activity)
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


def _record_scan_evidence(app, rec, activity):
    """Registra o candidato do ftp-scan como evidencia (FTP-H2).

    Evidencia permanece evidencia — nao promove referencia, nao toca .env.
    Idempotente: a mesma activity_id gera o mesmo id e execucoes repetidas do
    scan apenas preservam o primeiro registro."""
    try:
        observed = ftp_evidence.observed_at_from_provider(
            activity.get("start_date_local"), default_day=rec["day"])
    except ValueError:
        observed = ftp_evidence.observed_at_from_provider(None, default_day=rec["day"])
    evidence = ftp_evidence.FtpEvidence(
        id=f"scan-{rec['activity_id']}",
        value_watts=rec["proposed_ftp"],
        observed_at=observed,
        recorded_at=datetime.now(timezone.utc),
        source=ftp_evidence.FtpEvidenceSource.FTP_SCAN,
        protocol=ftp_evidence.FtpProtocol.FTP_20_MIN,
        activity_id=rec["activity_id"],
        provider="intervals",
        best20=rec["best20"],
        quality_ok=bool(rec["quality_ok"]),
        proposes_new=bool(rec["suggests_new"]),
        notes="candidato do ftp-scan (treino fora do plano)",
    )
    try:
        app.record_ftp_evidence(evidence)
    except ValueError:
        pass  # ja registrado em execucao anterior


def cmd_ftp_evidence(args):
    """Lista a evidencia de FTP registrada e o Advice (FTP-H2). Read-only."""
    app = _make_app()
    now = datetime.now(timezone.utc)
    current = app.get_current_ftp_reference(now)
    if current is None:
        print("FTP canonico: nenhum (FtpHistory vazio ou sem referencia vigente).")
    else:
        print(f"FTP canonico: {current.value_watts:.0f}W (id {current.id}, "
              f"vigente desde {current.effective_from.date()})")
    entries = app.get_ftp_evidence()
    if not entries:
        print("Nenhuma evidencia de FTP registrada (ftp_evidence.json vazio).")
    for entry in sorted(entries, key=lambda item: item.observed_at, reverse=True):
        gate = ("sugere novo" if entry.proposes_new else
                "dentro" if entry.quality_ok else "invalido")
        tail = f" | 20min {entry.best20:.0f}W" if entry.best20 else ""
        print(f"  {entry.id:<22} {entry.observed_at.date()}  "
              f"{entry.source.value:<20} {entry.value_watts:.0f}W  "
              f"[{gate}]{tail}")
    advice = app.get_ftp_advice(now)
    print(f"\nAdvice: {advice.kind.value}")
    if advice.reason:
        print(f"  {advice.reason}")
    if advice.suggests_confirmation and advice.evidence_id:
        print(f"  acao: `ftp-confirm {advice.evidence_id}` cria a referencia "
              "canonica (com sua confirmacao explicita).")
    print("Observacao: evidencia nao muda prescricao, .env nem calendario "
          "(isso e escopo do FTP-H6).")


def cmd_ftp_confirm(args):
    """Confirma uma evidencia e cria a `FtpReference` canonica (FTP-H2).

    Unica ponte evidencia -> estado canonico: exige confirmacao explicita do
    usuario e nunca toca build, `.env`, provider nem calendario (FTP-H6)."""
    app = _make_app()
    now = datetime.now(timezone.utc)
    evidence_by_id = {item.id: item for item in app.get_ftp_evidence()}
    if args.evidence_id not in evidence_by_id:
        print(f"evidencia FTP inexistente: {args.evidence_id} "
              "(rode `ftp-evidence` para listar).")
        return None
    evidence = evidence_by_id[args.evidence_id]
    current = app.get_current_ftp_reference(now)
    print(f"Evidencia: {evidence.id}  {evidence.observed_at.date()}  "
          f"{evidence.source.value}  {evidence.value_watts:.0f}W")
    if evidence.best20 is not None:
        print(f"  20min {evidence.best20:.0f}W | quality_ok "
              f"{bool(evidence.quality_ok)} | proposes_new "
              f"{bool(evidence.proposes_new)}")
    if current is None:
        print("FTP canonico atual: nenhum")
    else:
        print(f"FTP canonico atual: {current.value_watts:.0f}W (id {current.id})")
    ref_id = args.reference_id or f"ftp-{evidence.id}"
    if args.effective_from:
        effective = datetime.combine(
            date.fromisoformat(args.effective_from),
            datetime.min.time(), timezone.utc)
    else:
        effective = now
    print(f"Vai criar referencia canonica: {ref_id}  "
          f"{evidence.value_watts:.0f}W  vigente desde {effective.date()}")
    answer = input("Confirmar e criar a referencia canonica? (s/N) ").strip().lower()
    if answer != "s":
        print("Nao confirmado; nenhuma referencia foi criada.")
        return None
    reference = app.confirm_ftp_evidence(
        args.evidence_id, now=now, effective_from=effective,
        reference_id=ref_id)
    print(f"FTP canonico registrado: {reference.value_watts:.0f}W a partir "
          f"de {reference.effective_from.date()} (id {reference.id}).")
    print("Nota: prescricao/build continuam via .env (legado) ate o FTP-H6; "
          "este registro e o novo estado canonico de perfil.")
    return reference


def cmd_push(args):
    load_env(PROJECT_ROOT / ".env")
    app = _make_app()
    plan = app.load_plan()
    lang = get_cue_lang()
    # `all` nao declara --start; o default e o mesmo do subparser `push`.
    start = getattr(args, "start", None) or (date.today()
                                             + timedelta(days=1)).isoformat()
    result = push_workouts(
        app.client(),
        plan=plan,
        start=start,
        ftp=get_ftp(),
        fthr=get_fthr(),
        lang=lang,
        event_payload_fn=event_payload,
        prev_same_focus_fn=_prev_same_focus,
        orphan_external_ids_fn=orphan_external_ids,
        manual_duplicate_ids_fn=manual_duplicate_ids,
        dry_run=bool(getattr(args, "dry_run", False)),
    )
    if result.dry_run:
        print(f"dry-run: enviaria {len(result.batch)} eventos ao calendario")
        for p in result.batch:
            print(f"  {p['start_date_local']} {p['name']}")
        if result.orphans:
            print(f"dry-run: removeria {len(result.orphans)} orfaos: "
                  f"{result.orphans}")
        if result.dup_ids:
            print(f"dry-run: removeria {len(result.dup_ids)} duplicatas manuais "
                  f"(ids): {result.dup_ids}")
        if result.beyond:
            print(f"dry-run: {len(result.beyond)} orfaos ALÉM do horizonte do "
                  f"plano (mantidos, de plano anterior mais longo): "
                  f"{result.beyond}")
        return

    if result.orphans:
        print(f"Orfaos removidos (HTTP {result.orphan_status}): "
              f"{result.orphans_deleted}")
    for did, cst in result.dup_statuses:
        print(f"Duplicata manual removida (id {did}, HTTP {cst})")
    if result.beyond:
        print(f"{len(result.beyond)} eventos hermes-plan além do horizonte do "
              "plano mantidos (de plano anterior mais longo).")
    print(f"Calendario atualizado (HTTP {result.create_status}): "
          f"{result.created} eventos")


def cmd_all(args):
    # Issue #58 Passo A: `all --dry-run` precisa parar depois do build. Sem
    # isso, `reconcile` e `push` leriam o plan.json ANTIGO (o build dry-run nao
    # grava) e reconciliariam o calendario contra um plano que nunca foi
    # gerado -- um relato de mudancas que nao existem.
    if getattr(args, "dry_run", False):
        cmd_build(args)
        print("dry-run: encerrando apos build. Apenas o planejamento foi "
              "simulado; a reconciliacao nao foi executada nem simulada, e "
              "nada foi publicado ou gravado.")
        return
    cmd_build(args)
    cmd_reconcile(args)
    cmd_push(args)


def _iso_date(text):
    """`--date` -> `date` na borda do argparse.

    O anchor era o UNICO parametro do summary aceito como `str` OU `date`
    (default `date`, explicito `str`): era essa a mistura de tipos -- nao o
    parsing do `--start/--end`, que e `str` do fim ao fim e e convertido uma
    unica vez dentro de `resolve_period`. Com a mistura, `period_range`/
    `resolve_period` estouravam TypeError e `done_activities` AttributeError.
    Converte-se UMA vez, aqui; o core so ve o tipo canonico. Erro vira
    `ArgumentTypeError` para o argparse reportar erro de uso com exit 2.
    """
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"data invalida {text!r}; use YYYY-MM-DD") from None


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

    p_evidence = sub.add_parser(
        "ftp-evidence",
        help="Lista a evidencia de FTP registrada e o Advice (FTP-H2; read-only)")
    p_evidence.set_defaults(func=cmd_ftp_evidence)

    p_confirm = sub.add_parser(
        "ftp-confirm",
        help="Confirma uma evidencia e cria a referencia canonica de FTP (FTP-H2)")
    p_confirm.add_argument(
        "evidence_id", help="id da evidencia (veja `ftp-evidence`)")
    p_confirm.add_argument(
        "--reference-id", default=None,
        help="id da referencia canonica (default: ftp-<evidencia>)")
    p_confirm.add_argument(
        "--effective-from", default=None, metavar="YYYY-MM-DD",
        help="inicio de vigencia da referencia (default: agora)")
    p_confirm.set_defaults(func=cmd_ftp_confirm)

    p_check = sub.add_parser(
        "check",
        help="Prontidao do dia: wellness + sugestao de troca (nao obrigatoria)")
    p_check.add_argument("--days", type=int, default=14,
                         help="Janela de wellness a considerar (dias)")
    p_check.add_argument("--apply", action="store_true",
                         help="Grava a proposta de prontidao no plan.json "
                              "(ainda nao publica); rode `push` para publicar")
    p_check.add_argument("--dry-run", action="store_true",
                         help="Mostra a proposta de prontidao sem gravar no "
                              "plan.json e sem publicar")
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
        "--date", type=_iso_date, metavar="YYYY-MM-DD",
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
                         help="Agenda o teste de FTP e protege as 48h antes")
    p_build.add_argument("--no-power", action="store_true",
                         help="Prescricao sem medidor de potencia: alvos em "
                              "%%FTHR + RPE (exige FTHR no .env)")
    p_build.add_argument("--dry-run", action="store_true",
                         help="Mostra o plano proposto (ja adaptado pela "
                              "prontidao) sem gravar em plan.json e sem "
                              "publicar nada")
    p_build.set_defaults(func=cmd_build)

    p_rec = sub.add_parser("reconcile",
                           help="Compara plano x treinos feitos e ajusta")
    p_rec.add_argument("--days", type=int, default=14)
    p_rec.add_argument("--show", action="store_true",
                       help="mostra a reconciliacao sem gravar plan.json")
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
                       help="Agenda o teste de FTP e protege as 48h antes")
    p_all.add_argument("--no-power", action="store_true",
                       help="Prescricao sem medidor de potencia (%%FTHR + RPE)")
    p_all.add_argument("--dry-run", action="store_true",
                         help="Mostra o plano proposto (ja adaptado pela "
                              "prontidao) sem gravar nem publicar; encerra "
                              "depois do build")
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

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from coach import (latest_metrics, suggest_ftp_test, FOCUS_LABELS)
from intervals_client import IntervalsClient
from plan import (build_plan, event_payload, load_plan, reconcile, save_plan,
                  orphan_external_ids, FOCUS_LABELS_PT, REST, DEFAULT_FTP,
                  CUE_LANGS)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "plan.json"


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


def cmd_ftp_check(args):
    client = get_client()
    ftp = get_ftp()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    sug = suggest_ftp_test(events, ftp, weeks=args.weeks)
    print(f"FTP atual: {ftp}W")
    print(f"Ultimo teste de FTP: {sug.last_test or 'nenhum detectado'}"
          + (f" ({sug.days_since} dias)" if sug.days_since else ""))
    print(f"Reteste devido: {'SIM' if sug.due else 'nao'}  |  {sug.reason}")
    if sug.due:
        print("Sugestao: agende um Ramp Test no app Zwift em um dia descansado;")
        print("depois informe o novo FTP para atualizar o .env e o plano.")


def cmd_build(args):
    client = get_client()
    ftp = get_ftp()
    newest = date.today()
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    metrics = latest_metrics(events)
    tsb = metrics.tsb if metrics else 0.0
    plan = build_plan(events, tsb, ftp=ftp, days=args.days_plan)
    save_plan(plan, PLAN_FILE)
    print(f"Plano gerado: {len(plan)} treinos | TSB atual {tsb:.1f} | FTP {ftp}W")
    for w in plan:
        print(f"  {w['day']} {w['name']:<30} {w['planned_duration'] // 60:>3}m TSS {w['tss']:.0f}")
    return plan


def cmd_reconcile(args):
    plan = load_plan(PLAN_FILE)
    client = get_client()
    ftp = get_ftp()
    newest = date.today() + timedelta(days=1)
    oldest = newest - timedelta(days=args.days)
    events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat())
    plan, missed = reconcile(plan, events, ftp=ftp)
    save_plan(plan, PLAN_FILE)
    if missed:
        print(f"Treinos perdidos detectados: {[m['day'] for m in missed]}")
        print("Plano ajustado: recuperacao inserida e proximo limiar reduzido.")
    else:
        print("Nenhum treino perdido; plano mantido.")
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


def cmd_push(args):
    load_env(PROJECT_ROOT / ".env")
    plan = load_plan(PLAN_FILE)
    client = get_client()
    lang = get_cue_lang()
    start = args.start or (date.today() + timedelta(days=1)).isoformat()
    batch = [event_payload(w, get_ftp(), lang=lang,
                           prev=_prev_same_focus(plan, w))
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

    p_build = sub.add_parser("build", help="Gera o plano a partir do historico")
    p_build.add_argument("--days", type=int, default=60,
                         help="Janela de historico (dias)")
    p_build.add_argument("--days-plan", type=int, default=14,
                         help="Quantos dias olhar para frente")
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
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
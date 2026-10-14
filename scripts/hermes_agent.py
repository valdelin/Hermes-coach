#!/usr/bin/env python3
"""Orquestrador local determinístico do Hermes Coach.

Facade sobre ``src/training_plan.py`` e ``scripts/``: despacha comandos
existentes, encadeia workflows conhecidos e exige confirmação antes de
operações mutáveis. Sem LLM, sem gateway, sem shell arbitrário.

NÃO é: motor de domínio, fonte de verdade, storage canônico, provider nem
prescription engine. Nenhuma lógica de negócio vive aqui; o backend é o CLI
existente (``python3 src/training_plan.py <subcomando>``).
"""

import argparse
import os
import shlex
import subprocess
import sys
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINING_SCRIPT = "src/training_plan.py"
SYNC_VAULT_SCRIPT = "scripts/sync_vault_docs.py"
DAILY_SCRIPT = "scripts/daily_reconcile.sh"

CONFIRM_YES = {"y", "yes", "s", "sim"}
INSIGHT_ENABLED_ENV = "HERMES_INSIGHT_ENABLED"
_INSIGHT_TRUTHY = frozenset({"1", "true", "yes", "on"})


class CommandEffect(str, Enum):
    """Maior efeito persistente que um comando pode produzir."""

    READ_ONLY = "read_only"
    LOCAL_WRITE = "local_write"
    REFERENCE_CHANGE = "reference_change"
    EXTERNAL_WRITE = "external_write"


def _has_flag(argv: tuple[str, ...], flag: str) -> bool:
    return flag in argv or any(arg.startswith(f"{flag}=") for arg in argv)


def training_effect(subcommand: str, argv=()) -> CommandEffect:
    """Classifica o efeito do CLI subjacente de forma conservadora.

    `raw` usa a mesma tabela, logo nao pula confirmacao por escolher outra
    superficie. Desconhecidos caem em LOCAL_WRITE: um prompt extra e preferivel
    a executar uma mutacao nova sem autorizacao.
    """
    argv = tuple(argv)
    if subcommand in {
            "info", "model", "adherence", "ftp-check", "periodization",
            "recovery", "ftp-evidence"}:
        return CommandEffect.READ_ONLY
    if subcommand == "summary":
        return (CommandEffect.LOCAL_WRITE if _has_flag(argv, "--export")
                else CommandEffect.READ_ONLY)
    if subcommand == "check":
        return (CommandEffect.LOCAL_WRITE if _has_flag(argv, "--apply")
                and not _has_flag(argv, "--dry-run")
                else CommandEffect.READ_ONLY)
    if subcommand == "reconcile":
        return (CommandEffect.READ_ONLY if _has_flag(argv, "--show")
                else CommandEffect.LOCAL_WRITE)
    if subcommand == "build":
        return (CommandEffect.READ_ONLY if _has_flag(argv, "--dry-run")
                else CommandEffect.LOCAL_WRITE)
    if subcommand == "all":
        return (CommandEffect.READ_ONLY if _has_flag(argv, "--dry-run")
                else CommandEffect.EXTERNAL_WRITE)
    if subcommand == "push":
        return (CommandEffect.READ_ONLY if _has_flag(argv, "--dry-run")
                else CommandEffect.EXTERNAL_WRITE)
    if subcommand == "ftp-confirm":
        return CommandEffect.REFERENCE_CHANGE
    if subcommand == "ftp-scan":
        # FTP-H2 registra FtpEvidence e meta local antes da possivel aplicacao
        # externa, que o CLI continua confirmando em prompt proprio.
        return CommandEffect.EXTERNAL_WRITE
    return CommandEffect.LOCAL_WRITE


def training(subcommand: str, *args: str) -> list[str]:
    """Monta o comando do CLI existente com o interpretador atual."""
    return [sys.executable, TRAINING_SCRIPT, subcommand, *args]


def run(cmd: list[str]) -> int:
    """Mostra e executa ``cmd`` na raiz do repo; devolve o exit code."""
    print(f"$ {shlex.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return result.returncode


def confirm(question: str = "Continuar?") -> bool:
    """Pergunta ao usuário; EOF/erro de stdin cancelam por padrão."""
    try:
        answer = input(f"{question} [s/N] ").strip().lower()
    except (EOFError, OSError, RuntimeError):
        print("confirmacao indisponivel; operacao cancelada.", file=sys.stderr)
        return False
    return answer in CONFIRM_YES


def _maybe_confirm(args, question: str) -> bool:
    """Retorna False quando a operação foi cancelada pelo usuário."""
    if args.yes:
        return True
    return confirm(question)


def authorize(args, effect: CommandEffect, question: str) -> bool:
    """Aplica confirmacao local a todo efeito persistente conhecido ou novo."""
    if effect is CommandEffect.READ_ONLY:
        return True
    return _maybe_confirm(args, question)


# --------------------------------------------------------------------------
# Read-only
# --------------------------------------------------------------------------

def cmd_status(args) -> int:
    for subcommand, sub_args in (
        ("info", ("--days", "60")),
        ("model", ("--days", "60")),
        ("adherence", ("--days", "45")),
        ("ftp-check", ("--days", "120", "--weeks", "8")),
    ):
        code = run(training(subcommand, *sub_args))
        if code != 0:
            return code
    return 0


def cmd_info(args) -> int:
    return run(training("info", "--days", str(args.days)))


def cmd_model(args) -> int:
    return run(training("model", "--days", str(args.days)))


def cmd_adherence(args) -> int:
    return run(training("adherence", "--days", str(args.days)))


def cmd_ftp_check(args) -> int:
    return run(training("ftp-check", "--days", str(args.days),
                        "--weeks", str(args.weeks)))


def cmd_ftp_scan(args) -> int:
    if not authorize(
            args, training_effect("ftp-scan"),
            "ftp-scan registra evidencia local; o CLI pedira nova confirmacao "
            "antes de alterar .env ou Intervals. Continuar?"):
        print("cancelado.")
        return 0
    return run(training("ftp-scan", "--days", str(args.days)))


def cmd_periodization(args) -> int:
    cmd = ["periodization"]
    if args.model:
        cmd += ["--model", args.model]
    if args.no_tsb:
        cmd += ["--no-tsb"]
    cmd += ["--days", str(args.days)]
    return run(training(*cmd))


def cmd_sync_summary(args) -> int:
    cmd = ["summary", "--period", args.period]
    if args.date:
        cmd += ["--date", args.date]
    if args.start:
        cmd += ["--start", args.start]
    if args.end:
        cmd += ["--end", args.end]
    if args.chart:
        cmd += ["--chart", args.chart]
    if args.export:
        cmd += ["--export", args.export]
    if args.theme:
        cmd += ["--theme", args.theme]
    if not authorize(
            args, training_effect("summary", cmd[1:]),
            "summary --export escreve um relatorio local. Continuar?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_reconcile(args) -> int:
    cmd = ["reconcile", "--days", str(args.days)]
    if args.show:
        cmd += ["--show"]
    if not authorize(
            args, training_effect("reconcile", cmd[1:]),
            "reconcile ajusta e grava plan.json. Continuar?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_recovery(args) -> int:
    # Flags reais do argparse (`src/training_plan.py recover`): --weeks e
    # --ramp-pts. `--days/--show` pertencem ao subtcomando `reconcile`.
    return run(training("recovery", "--weeks", str(args.weeks),
                        "--ramp-pts", str(args.ramp_pts)))


def cmd_today(args) -> int:
    if args.apply:
        if not authorize(
                args, CommandEffect.LOCAL_WRITE,
                "check --apply grava a prontidão de hoje em plan.json?"):
            print("cancelado.")
            return 0
        code = run(training("check", "--apply"))
        if code != 0:
            return code
        return run(training("reconcile", "--show"))
    run(training("check", "--dry-run"))
    return run(training("reconcile", "--show"))


def cmd_check(args) -> int:
    cmd = ["check", "--days", str(args.days)]
    if args.apply:
        cmd += ["--apply"]
    if args.dry_run:
        cmd += ["--dry-run"]
    if not authorize(
            args, training_effect("check", cmd[1:]),
            "check --apply grava a proposta de prontidão em plan.json?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_build(args) -> int:
    cmd = ["build", "--days", str(args.days), "--days-plan", str(args.days_plan)]
    if args.ftp_test:
        cmd += ["--ftp-test", args.ftp_test]
    if args.no_power:
        cmd += ["--no-power"]
    if args.dry_run:
        cmd += ["--dry-run"]
    if not authorize(args, training_effect("build", cmd[1:]),
                     "build grava em plan.json?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_all(args) -> int:
    cmd = ["all"]
    if args.recovery:
        cmd += ["--recovery"]
    cmd += ["--ramp-pts", str(args.ramp_pts)]
    cmd += ["--recovery-weeks", str(args.recovery_weeks)]
    if args.dry_run:
        cmd += ["--dry-run"]
    if not authorize(
            args, training_effect("all", cmd[1:]),
            "all gera, reconcilia e publica no calendário do Intervals?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_push(args) -> int:
    cmd = ["push"]
    if args.start:
        cmd += ["--start", args.start]
    if args.dry_run:
        cmd += ["--dry-run"]
    if not authorize(
            args, training_effect("push", cmd[1:]),
            "push publica no calendário do Intervals?"):
        print("cancelado.")
        return 0
    return run(training(*cmd))


def cmd_raw(args) -> int:
    if not args.rest:
        print("raw exige um subcomando do CLI.")
        return 2
    effect = training_effect(args.rest[0], args.rest[1:])
    if not authorize(
            args, effect,
            f"raw executa `{shlex.join(args.rest)}` ({effect.value}). Continuar?"):
        print("cancelado.")
        return 0
    return run(training(*args.rest))


def cmd_daily(args) -> int:
    if not authorize(
            args, CommandEffect.EXTERNAL_WRITE,
            "daily roda scripts/daily_reconcile.sh (check --apply + "
            "reconcile + push do dia)?"):
        print("cancelado.")
        return 0
    return run(["bash", DAILY_SCRIPT])


def cmd_vault_check(args) -> int:
    return run([sys.executable, SYNC_VAULT_SCRIPT, "--check"])


def cmd_vault_sync(args) -> int:
    if not authorize(
            args, CommandEffect.LOCAL_WRITE,
            "vault-sync atualiza os espelhos do vault a partir do repo?"):
        print("cancelado.")
        return 0
    return run([sys.executable, SYNC_VAULT_SCRIPT, "--sync", *args.doc])


def cmd_tests(args) -> int:
    if args.target:
        return run([sys.executable, "-m", "unittest", args.target, "-v"])
    return run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])


def insight_enabled(value: str | None = None) -> bool:
    """Flag opt-in e fail-closed da presentation local do INSIGHT."""
    raw = os.environ.get(INSIGHT_ENABLED_ENV) if value is None else value
    return isinstance(raw, str) and raw.strip().lower() in _INSIGHT_TRUTHY


def build_insight_application():
    """Composition root local da query read-only do INSIGHT."""
    from src.application import Application
    return Application()


def print_insight_presentation(presentation) -> None:
    """Apresenta a saída terminal sem interpretá-la como ação de domínio."""
    print("INSIGHT")
    print(f"headline: {presentation.headline}")
    print(f"explanation: {presentation.explanation}")
    print(f"next_action_text: {presentation.next_action_text}")
    if presentation.caution_text is not None:
        print(f"caution_text: {presentation.caution_text}")


def cmd_insight(args) -> int:
    """Apresentação offline opt-in: View local -> fallback determinístico."""
    if not insight_enabled():
        print("Insight is disabled.")
        return 0
    from src.insight.render import fallback_presentation

    view = build_insight_application().get_insight_view(
        subject=args.subject, workout_id=args.workout_id)
    print_insight_presentation(fallback_presentation(view))
    return 0


# --------------------------------------------------------------------------
# Modo interativo
# --------------------------------------------------------------------------

INTERACTIVE_HELP = """\
Comandos:
  status        TSB/CTL/ATL + modelo + aderência + ftp-check (só leitura)
  hoje          prontidão de hoje (dry-run) + reconcile --show (só leitura)
  hoje aplicar  grava a prontidão de hoje em plan.json (mutável — confirma)
  build | plano gera o plano e grava plan.json (mutável — confirma)
  reconciliar   reconcile --show (só leitura)
  publicar      push no calendário do Intervals (mutável — confirma)
  diario        roda scripts/daily_reconcile.sh (mutável — confirma)
  ftp           ftp-check (só leitura)
  ftp-scan      examina treinos fora do plano (grava evidencia — confirma)
  resumo        summary do dia (só leitura)
  docs          vault-check (só leitura)
  testes        suíte de testes (só leitura)
  ajuda         esta ajuda
  sair          encerra a sessão

Operações mutáveis pedem confirmação antes de executar. Flags avançadas não
existem aqui: use o CLI normal (python3 src/training_plan.py) ou `raw`."""


def _interactive_banner() -> None:
    print("Hermes Coach Agent — orquestrador local determinístico")
    print("Digite 'ajuda' para a lista de comandos; 'sair' encerra.")


def _ns(**kwargs) -> argparse.Namespace:
    kwargs.setdefault("yes", False)
    return argparse.Namespace(**kwargs)


def _dispatch_interactive(name: str, rest: list[str]):
    """Despacha um comando do REPL; devolve exit code ou None se desconhecido."""
    if name in ("status",):
        return cmd_status(_ns())
    if name in ("hoje", "today"):
        apply_flag = any(t in ("aplicar", "apply", "--apply") for t in rest)
        return cmd_today(_ns(apply=apply_flag))
    if name in ("build", "plano"):
        return cmd_build(_ns(days=60, days_plan=14, ftp_test=None,
                             no_power=False, dry_run=False))
    if name in ("reconciliar",):
        return cmd_reconcile(_ns(days=14, show=True))
    if name in ("publicar",):
        return cmd_push(_ns(start=None, dry_run=False))
    if name in ("diario",):
        return cmd_daily(_ns())
    if name in ("ftp",):
        return cmd_ftp_check(_ns(days=120, weeks=8))
    if name in ("ftp-scan",):
        return cmd_ftp_scan(_ns(days=45))
    if name in ("resumo",):
        return cmd_sync_summary(_ns(period="day", date=None, start=None,
                                    end=None, chart=None, export=None, theme=None))
    if name in ("docs",):
        return cmd_vault_check(_ns())
    if name in ("testes",):
        return cmd_tests(_ns(target=None))
    print(f"comando desconhecido: {name} — use 'ajuda'.")
    return None


def interactive() -> int:
    _interactive_banner()
    while True:
        try:
            line = input("hermes> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        words = line.split()
        name = words[0].lower()
        rest = words[1:]
        if name in ("ajuda", "help", "?"):
            print(INTERACTIVE_HELP)
            continue
        if name in ("sair", "exit", "quit", "q"):
            return 0
        try:
            code = _dispatch_interactive(name, rest)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        except Exception as exc:  # noqa: BLE001 — REPL segue a sessão
            print(f"erro: {exc}")
            continue
        if code is not None and code != 0:
            print(f"comando falhou (exit {code})")


# --------------------------------------------------------------------------
# Argparse (não-interativo)
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes_agent.py",
        description="Orquestrador local determinístico do Hermes Coach "
                    "(facade sobre src/training_plan.py).",
        epilog="Sem subcomando: entra no modo interativo (hermes>).")
    parser.add_argument(
        "--yes", action="store_true",
        help="Pula prompts de confirmação. Adequado apenas para workflows "
             "já revisados; não torna operações read-only.")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("status", help="Encadeia info/model/adherence/ftp-check (só leitura)")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("info", help="TSB/CTL/ATL atuais (só leitura)")
    p.add_argument("--days", type=int, default=60)
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("model", help="PMC (Banister) + zonas Friel + projeção (só leitura)")
    p.add_argument("--days", type=int, default=60)
    p.set_defaults(func=cmd_model)

    p = sub.add_parser("adherence", help="Cumprimento semanal do plano (só leitura)")
    p.add_argument("--days", type=int, default=45)
    p.set_defaults(func=cmd_adherence)

    p = sub.add_parser("ftp-check", help="Hora de (re)fazer teste de FTP (só leitura)")
    p.add_argument("--days", type=int, default=120)
    p.add_argument("--weeks", type=int, default=8)
    p.set_defaults(func=cmd_ftp_check)

    p = sub.add_parser("ftp-scan", help="Examina e registra evidencia local (confirma)")
    p.add_argument("--days", type=int, default=45)
    p.set_defaults(func=cmd_ftp_scan)

    p = sub.add_parser("periodization", help="Modelos de periodização (só leitura)")
    p.add_argument("--model", help="polarized|pyramidal|undulating|linear|block")
    p.add_argument("--no-tsb", action="store_true")
    p.add_argument("--days", type=int, default=60)
    p.set_defaults(func=cmd_periodization)

    p = sub.add_parser("summary", help="Resumo dos treinos feitos; --export grava arquivo")
    p.add_argument("--period", default="day")
    p.add_argument("--date", metavar="YYYY-MM-DD")
    p.add_argument("--start", metavar="YYYY-MM-DD")
    p.add_argument("--end", metavar="YYYY-MM-DD")
    p.add_argument("--chart", choices=("auto", "none", "pmc", "load", "all"))
    p.add_argument("--export", metavar="ARQUIVO")
    p.add_argument("--theme", metavar="TEMA")
    p.set_defaults(func=cmd_sync_summary)

    p = sub.add_parser("reconcile", help="Plano x treinos feitos; --show e só leitura")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--show", action="store_true")
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("recovery", help="Retorno à forma: estimativa + rampa (só leitura)")
    p.add_argument("--weeks", type=int, default=12)
    p.add_argument("--ramp-pts", type=int, default=9)
    p.set_defaults(func=cmd_recovery)

    p = sub.add_parser("today", help="Prontidão de hoje; --apply grava em plan.json")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_today)

    p = sub.add_parser("check", help="Prontidão do dia; --apply grava em plan.json")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("build", help="Gera o plano (mutável: grava plan.json)")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--days-plan", type=int, default=14)
    p.add_argument("--ftp-test", metavar="YYYY-MM-DD")
    p.add_argument("--no-power", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("all", help="build + reconcile + push (mutável)")
    p.add_argument("--recovery", action="store_true")
    p.add_argument("--ramp-pts", type=int, default=9)
    p.add_argument("--recovery-weeks", type=int, default=12)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_all)

    p = sub.add_parser("push", help="Publica no calendário do Intervals (mutável)")
    p.add_argument("--start", metavar="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("daily", help="scripts/daily_reconcile.sh (mutável)")
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("vault-check", help="sync_vault_docs.py --check (só leitura)")
    p.set_defaults(func=cmd_vault_check)

    p = sub.add_parser("vault-sync", help="sync_vault_docs.py --sync DOC (mutável)")
    p.add_argument("doc", nargs="+", metavar="DOC")
    p.set_defaults(func=cmd_vault_sync)

    p = sub.add_parser("tests", help="Suíte de testes (só leitura)")
    p.add_argument("target", nargs="?", metavar="TARGET",
                   help="Módulo de teste específico (ex.: tests.test_vault_sync)")
    p.set_defaults(func=cmd_tests)

    p = sub.add_parser("insight", help="Apresentação local do INSIGHT (opt-in)")
    p.add_argument("--subject", default="today", metavar="SUBJECT")
    p.add_argument("--workout-id", metavar="ID")
    p.set_defaults(func=cmd_insight)

    p = sub.add_parser("raw", help="Encaminha ao CLI com confirmacao por efeito")
    p.add_argument("rest", nargs=argparse.REMAINDER,
                   help="Argumentos do CLI (ex.: ftp-check --days 90 --weeks 6)")
    p.set_defaults(func=cmd_raw)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "cmd", None) is None:
        return interactive()
    code = args.func(args)
    return int(code) if isinstance(code, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())

# dev/ — diagnóstico e recuperação

Materiais de desenvolvimento para quando a aplicação **quebrar**: como
investigar, o que coletar e como voltar a operar. Nada aqui roda no fluxo
normal (timer diário).

| Arquivo | Uso |
|---|---|
| `DIAGNOSTICO.md` | Guia passo a passo: de "notificação de falha" a "causa raiz" |
| `diagnose.sh` | Script que coleta o estado da aplicação em um só lugar (rodar ANTES de mexer) |

## Regra de ouro

**Antes de reexecutar qualquer comando, colete o estado** (`./dev/diagnose.sh`).
Não re-execute `reconcile`/`push` às cegas após uma falha — o log pode indicar
uma causa que re-executar vai esconder ou agravar.
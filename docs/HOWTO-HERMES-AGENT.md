# HOWTO — Hermes Agent (orquestrador local)

Este guia mostra como usar o orquestrador local determinístico do Hermes
Coach, do zero, sem precisar ler o código.

## 1. O que é

`scripts/hermes_agent.py` é uma **facade** (camada de orquestração) sobre o CLI
existente:

```
python3 src/training_plan.py <subcomando>
```

Ela não implementa nenhuma lógica de treino. Ela:

- despacha os comandos já existentes do CLI;
- encadeia workflows conhecidos (ex.: `status`);
- **exige confirmação antes de operações mutáveis** (gravar plano, publicar no
  calendário);
- oferece um **modo interativo** simples (`hermes>`);
- oferece **`raw`**, um escape hatch que encaminha argumentos direto ao CLI.

### O que NÃO é

- Não é o motor de treino (o motor continua sendo `src/training_plan.py`).
- Não é fonte de verdade nem armazenamento de estado.
- Não tem LLM/NLP embutido.
- Não é gateway de mensagens (Telegram etc.). Isso é planejamento futuro.

## 2. Pré-requisitos

- Python 3 (stdlib apenas — sem dependências novas).
- O projeto clonado, com `src/training_plan.py` e o `.env` configurado quando os
  comandos lerem o Intervals.icu.
- Para comandos que tocam o calendário ou o wellness, os mesmos requisitos do
  CLI (`.env` com `INTERVALS_ATHLETE_ID`/`INTERVALS_API_KEY` etc.).

## 3. Onde fica

```
scripts/hermes_agent.py
```

## 4. Como executar

Não há instalação via pip/console script ainda. Use:

```bash
python3 scripts/hermes_agent.py <subcomando> [opções]
```

Opcional — dar permissão de execução para usar `./`:

```bash
chmod +x scripts/hermes_agent.py
./scripts/hermes_agent.py <subcomando>
```

Para ver a ajuda:

```bash
python3 scripts/hermes_agent.py --help          # ajuda do orquestrador
python3 scripts/hermes_agent.py raw --help      # ajuda do CLI subjacente
```

## 5. Modo interativo

Sem subcomando, o script abre o REPL:

```bash
python3 scripts/hermes_agent.py
```

Resultado conceitual:

```
Hermes Coach Agent — orquestrador local determinístico
Digite 'ajuda' para a lista de comandos; 'sair' encerra.
hermes> status
hermes> hoje
hermes> build
hermes> ajuda
hermes> sair
```

O REPL entende **aliases determinísticos** (não é linguagem natural). Se um
comando falhar, ele mostra o exit code e a sessão continua. `Ctrl+C`/`EOF`
encerra de forma limpa.

## 6. Comandos

| Comando | O que faz | Mutável? |
|---|---|---|
| `status` | Encadeia `info` + `model` + `adherence` + `ftp-check` | não |
| `info` | TSB/CTL/ATL atuais | não |
| `model` | PMC (Banister) + zonas Friel + projeção | não |
| `adherence` | Cumprimento semanal do plano | não |
| `ftp-check` | Indica se é hora de (re)fazer teste de FTP | não |
| `ftp-scan` | Registra evidência FTP-H2; pode aplicar FTP com segundo prompt | **externo** |
| `periodization` | Modelos de periodização | não |
| `summary` | Resumo dos treinos por período (`--export` grava arquivo) | depende |
| `reconcile --show` | Plano x treinos feitos sem persistir | não |
| `reconcile` | Plano x treinos feitos e grava ajustes locais | **local** |
| `recovery` | Retorno à forma: estimativa + rampa | não |
| `today` | Prontidão de hoje (dry-run) + reconcile | não |
| `today --apply` | Grava a prontidão de hoje em `plan.json` | **sim** |
| `check` | Prontidão do dia (`--dry-run` sem gravar) | — |
| `check --apply` | Grava a proposta de prontidão em `plan.json` | **sim** |
| `build` | Gera o plano e grava `plan.json` | **sim** |
| `all` | build + reconcile + push (calendário) | **sim** |
| `push` | Publica no calendário do Intervals.icu | **sim** |
| `daily` | Roda `scripts/daily_reconcile.sh` | **sim** |
| `vault-check` | `sync_vault_docs.py --check` | não |
| `vault-sync DOC` | Atualiza espelhos do vault | **sim** |
| `tests [TARGET]` | Suíte de testes (focada ou completa) | não |
| `raw ...` | Encaminha argumentos direto ao CLI, com gate pelo efeito | depende |

## 7. Exemplos

```bash
# Status completo (só leitura)
python3 scripts/hermes_agent.py status

# Gerar o plano (grava plan.json — vai pedir confirmação)
python3 scripts/hermes_agent.py build --days 60 --days-plan 14

# Gerar sem gravar nada (revisão)
python3 scripts/hermes_agent.py build --dry-run

# Agenda um teste de FTP e protege as 48h antes
python3 scripts/hermes_agent.py build --ftp-test 2026-11-01 --dry-run

# Prontidão de hoje sem tocar no plano
python3 scripts/hermes_agent.py today

# Publicar sem tocar no calendário (simulação)
python3 scripts/hermes_agent.py push --dry-run
```

Ordem recomendada para publicar: **`build --dry-run` → revisar → `build` →
`reconcile --show` → `push --dry-run` → `push`**.

## 8. Operações mutáveis e confirmações

Operações mutáveis pedem confirmação antes de executar:

```
$ python3 scripts/hermes_agent.py push
push publica no calendário do Intervals? [s/N]
```

Respostas aceitas para **sim**: `y`, `yes`, `s`, `sim`. **Qualquer outra
resposta ou apenas Enter cancela** (default = NÃO).

São mutáveis: `today --apply`, `check --apply`, `build` (sem `--dry-run`),
`reconcile` (sem `--show`), `ftp-scan` (registra evidência), `summary --export`,
`all` (sem `--dry-run`), `push` (sem `--dry-run`), `daily`, `vault-sync` e
`raw` cujo subcomando tenha efeito persistente. `ftp-confirm` é uma alteração de
referência fisiológica e mantém sua confirmação explícita no CLI.

## 9. Uso com `--yes`

`--yes` pula os prompts de confirmação locais do orquestrador:

```bash
python3 scripts/hermes_agent.py --yes daily
```

> **Atenção:** `--yes` só remove os prompts do wrapper. As operações continuam
> **mutáveis** e com efeito real (ex.: `push` publica no Intervals). Use
> `--yes` apenas em workflows já revisados e automatizados.

## 10. Raw passthrough

`raw` é o escape hatch para argumentos que o wrapper ainda não expõe:

```bash
python3 scripts/hermes_agent.py raw ftp-check --days 90 --weeks 6
```

Ele apenas encaminha o restante para `src/training_plan.py` — **não executa
comando shell arbitrário**. Antes do despacho, reaplica a classificação de
efeitos do orquestrador; comando desconhecido é tratado conservadoramente como
escrita local e exige confirmação.

## 11. Testes

```bash
# Suíte completa
python3 scripts/hermes_agent.py tests

# Focada
python3 scripts/hermes_agent.py tests tests.test_vault_sync
```

Equivale a:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest tests.test_vault_sync -v
```

## 12. Vault

Os espelhos do vault são atualizados pelo mecanismo oficial
(`scripts/sync_vault_docs.py`), nunca por cópia manual:

```bash
python3 scripts/hermes_agent.py vault-check
python3 scripts/hermes_agent.py vault-sync docs/ROADMAP.md
```

`vault-sync` pede confirmação. Este HOWTO não faz parte do mirror oficial, então
não é copiado pelo comando.

## 13. Daily automation

`daily` delega para `scripts/daily_reconcile.sh`, que roda três passos
(`check --apply` → `reconcile --show` → `push` do dia):

```bash
python3 scripts/hermes_agent.py daily
```

O **timer do systemd** `cycling-coach-daily.timer` continua separado e continua
chamando o script diretamente — não depende deste orquestrador.

## 14. Uso via OpenCode

Você pode delegar ao agente opencode do projeto:

```bash
opencode run --agent cycling-coach \
  "Execute o status do Hermes Coach usando scripts/hermes_agent.py"
```

Isso só informa o agente a usar o orquestrador; não é uma integração automática
entre o opencode e o script.

## 15. Uso futuro via Hermes Agent / Telegram

A arquitetura futura planejada é:

```
mensagem
→ Hermes Agent (gateway Telegram etc.)
→ scripts/hermes_agent.py
→ src/training_plan.py (Hermes Coach)
```

**Ainda não é um gateway real.** O script atual é apenas a boundary local
determinística; o framework agêntico (AGENT-1 em diante, ver `docs/ROADMAP.md`)
é opção de produto que aguarda aprovação explícita.

## 16. Troubleshooting

| Sintoma | Causa provável | Ação |
|---|---|---|
| `No such file or directory` ao chamar `src/training_plan.py` | Executou de outro diretório | Rode do root do repo (o script usa o caminho do próprio arquivo; rode via `python3 scripts/hermes_agent.py` de qualquer diretório, ou `cd` para o repo) |
| `ModuleNotFoundError: dotenv` / interpretador errado | Ambiente/venv | Use o Python do venv/ambiente atual; o script usa `sys.executable` |
| Comando de treino falha com erro de API | `.env` ausente ou credenciais incorretas | Confira `.env` (`INTERVALS_ATHLETE_ID`/`INTERVALS_API_KEY`) |
| Provider indisponível | Sem rede ou Intervals fora do ar | O CLI já reporta a falha; aguarde e tente de novo |
| `permission denied` ao usar `./scripts/hermes_agent.py` | Sem exec bit | `chmod +x scripts/hermes_agent.py` ou use `python3 scripts/hermes_agent.py` |
| Testes falhando | Ou suíte ou ambiente | Rode `tests <target>` para isolar; a suite completa deve ficar verde |
| `would_update` no vault | Espelho divergente | `vault-check` + revisão + `vault-sync <DOC>` |

Não há fixes destrutivos automáticos: revise antes de publicar.

## 17. Limitações atuais

- Não há NLP/LLM embutido (só aliases determinísticos).
- Não há saída estruturada (`--json`) — o stdout é humano; não interpretar.
- Não há multi-atleta.
- Não há auth/messaging gateway.
- Não substitui a `Application` nem o domínio.
- O script não deve armazenar estado canônico.

## 18. Segurança

- O REPL **não** aceita comandos shell arbitrários.
- Não há `exec`/`eval`/`shell=True` com input do usuário.
- `raw` encaminha **somente** para `src/training_plan.py`.
- Operações mutáveis sempre pedem confirmação (a menos que se use `--yes`,
  que remove o prompt local — mas não torna a operação read-only).

# Roteiro de Testes — Hermes Coach

- **Preparado em:** 2026-09-20 (após a v0.0.12)
- **Execução prevista:** 2026-09-22 (terça-feira)
- **Objetivo:** validar o fluxo completo (CLI, agente, calendário do
  Intervals.icu) e **caçar bugs novos** antes da próxima release.

> Como usar: marque cada item `[x]` após executar. Bugs encontrados → use o
> **template de reporte** na seção 13 e registre em `docs/KNOWN_ISSUES.md` +
> issue no GitHub ao final.

---

## 1. Pré-requisitos e baseline

- [ ] Repo em `<USERHOME>/Work/hermes-coach`, branch `master` em dia com o
      remoto (`git pull`).
- [ ] `.env` configurado (credenciais, `FTP`, `TRAINING_DAYS`, `GOAL`) — **faça
      backup antes de mexer**: `cp .env .env.bak`.
- [ ] Suíte de regressão verde (baseline — hoje: 122 testes, 1 skip em fim de
      semana):
      ```bash
      python3 -m unittest discover -s tests -v
      ```
- [ ] Agente `cycling-coach` linkado no opencode:
      `opencode run --agent cycling-coach --help` não falha.
- [ ] Data/hora do sistema corretas (fuso local) — importante para eventos e
      janelas de 7 dias.

---

## 2. Regressão offline (código)

- [ ] Testes unitários completos (seção 1) sem nenhuma falha.
- [ ] `python3 -c "from src.plan import parse_weekly_hours, parse_long_day"` —
      parsers carregam sem erro.
- [ ] Parsers de disponibilidade (via Python):
  - [ ] `parse_weekly_hours("5")` → `5.0`; `"5h"` → `5.0`; `"300min"` → `5.0`;
        `"0"`/`"abc"` → `None` (sem crash).
  - [ ] `parse_long_day("dom")` → `6`; `"sun"` → `6`; `"xyz"` → `None`.
- [ ] `python3 src/training_plan.py build --days 7 --days-plan 14` com
      `.env` **sem** `WEEKLY_HOURS`/`LONG_DAY` → plano idêntico ao comportamento
      anterior (nenhuma regressão).

---

## 3. Onboarding / primeiro uso (agente)

Simular no chat com o agente (conta **nova fictícia**, sem histórico):

- [ ] O agente **pergunta primeiro** se o usuário já tem conta no Intervals.icu.
- [ ] Com "não tenho conta": orienta criar conta gratuita e conectar plataformas
      via **Settings → Connections** (referencia `docs/SYNC-PLATAFORMAS.md`) e
      **não segue** sem a conta.
- [ ] Com "já tenho": vai direto às credenciais (Athlete ID + API Key →
      **Settings → Developer Settings**) com alerta de segurança.
- [ ] Pergunta **disponibilidade**: quantos dias, quantas horas (`WEEKLY_HOURS`)
      e melhor dia para treino longo (`LONG_DAY`).
- [ ] Resposta **"não tenho tempo para treinos longos no fim de semana"** →
      o agente aceita e propõe encaixar o treino longo no melhor dia informado
      (sem insistir em sábado/domingo).
- [ ] Apresenta o **menu de GOAL (1–7)** com a descrição de cada plano antes de
      pedir a escolha.
- [ ] Conta nova: avisa que o **TSB está zerado** e calibra em ~2 semanas.

**Anotar bugs de UX/flow** (pergunta confusa, ordem estranha, jargão sem
explicação, ausência de validação etc.).

---

## 4. info e wellness

- [ ] `python3 src/training_plan.py info --days 60` → mostra TSB/CTL/ATL.
- [ ] Linha `Wellness:` aparece com RHR, sono, passos e/ou HRV (conforme dados
      do Garmin) — sem crash quando não há dados na janela.
- [ ] `python3 src/training_plan.py model --days 60` → motor local vs API +
      projeção do plano.

---

## 5. build e disponibilidade (é a área com código novo — foco redobrado)

Preparação: `cp .env .env.bak` e edite `.env` entre os cenários.

- [ ] **Horas baixas**: `WEEKLY_HOURS=2` → o `build` reduz as durações;
      nenhum treino fica com esforço (`on_sec`) abaixo de 120s.
- [ ] **Horas altas**: `WEEKLY_HOURS=12` → durações crescem até o teto (1.5x),
      sem estourar o orçamento semanal de TSS.
- [ ] **Formato aceito**: `WEEKLY_HOURS=5h` e `WEEKLY_HOURS=300min` → mesmo
      resultado que `5`.
- [ ] **Valores inválidos**: `WEEKLY_HOURS=muitas` → aviso no `build` e plano
      **sem** ajuste (sem crash).
- [ ] **LONG_DAY dentro da agenda** (ex.: `LONG_DAY=dom` com `TRAINING_DAYS`
      incluindo domingo) → o treino endurance/longo cai no domingo.
- [ ] **LONG_DAY fora da agenda** (ex.: `LONG_DAY=dom`, agenda seg-sex) → o
      treino longo cai no **dia de treino mais próximo** (sem forçar fim de
      semana).
- [ ] **LONG_DAY inválido** → aviso no `build`, sem alteração de posição.
- [ ] **Sem as variáveis** → comportamento atual preservado.
- [ ] **build preserva o treino de hoje** ao regerar o plano.
- [ ] **GOAL=race sem `RACE_DATE`** → o `build` pergunta a data alvo (obrigatória)
      e recusa data passada/inválida.
- [ ] **GOAL=race com prova próxima** → últimos 7 dias viram **Taper (pre-prova)**.
- [ ] `build` imprime `Disponibilidade: ...h/semana | treino longo: ...`.

---

## 6. reconcile

Fixture real (últimos dias): compare `plan.json` x treinos feitos.

- [ ] Treino **perdido** (planejado e não feito em dia passado) → insere
      **Recuperação** no próximo dia de treino.
- [ ] Treino perdido → próximo **Limiar reduzido em 5%** (uma única vez por
      treino).
- [ ] Treino **extra pesado** fora do plano (carga ≥ cap diário nos 7 dias) →
      insere recuperação no próximo dia de treino (sem empilhar com a do
      perdido).
- [ ] Treino extra **leve** → plano não muda (`plan2 == plan`).
- [ ] Extra **fora da janela de 7 dias** → ignorado.
- [ ] `reconcile` **não muda o tamanho do plano** (substitui dias).
- [ ] `python3 src/training_plan.py reconcile --show` imprime agenda + ajustes.

---

## 7. push e calendário

- [ ] **Sempre** `python3 src/training_plan.py push --dry-run` antes do push real.
- [ ] `push --start YYYY-MM-DD` → `POST /events/bulk?upsert=true` ok (HTTP 200).
- [ ] Eventos **órfãos** `hermes-plan*` (não estão no plano atual) são
      removidos automaticamente; outros apps não são tocados.
- [ ] No app do Intervals (Custom Workouts), a descrição renderiza no formato
      nativo: `8m 88% (141w)`, com mensagem explicativa antes de cada passo.
- [ ] Textos em pt (`CUE_LANG=pt`) e en (`CUE_LANG=en`) corretos; `CUE_LANG`
      inválido → fallback para `pt` com aviso.
- [ ] Nenhum cue contém `%` nem duração abreviada (`6m`, `30s`) fora do target.
- [ ] Mensagem de progressão aparece quando há treino anterior do mesmo foco
      ("Isso sao X minutos a mais que o ultimo treino de Limiar FTP").

---

## 8. Troca de objetivo no meio do plano (agente)

- [ ] "quero treinar pra prova de dezembro" → agente mapeia para `race`,
      pergunta `RACE_DATE`, atualiza `.env`, roda `build` **preservando o treino
      de hoje** e explica o que muda na frente.
- [ ] Pede **confirmação antes do `push`** (não publica sozinho).
- [ ] Trocar para objetivo não-`race` → `RACE_DATE` **remove** do `.env`.
- [ ] Mudar só a data de um `race` em curso → atualiza e re-build sem quebrar.

---

## 9. Teste de FTP

- [ ] `python3 src/training_plan.py ftp-check` → mostra último teste, dias desde
      o teste e se o reteste é devido (janela pelo tipo de plano).
- [ ] Quando devido, sugere o **Ramp Test do Zwift** (não agenda sozinho).
- [ ] `python3 src/training_plan.py build --ftp-test 2026-10-22` (data futura):
      protege **D-2 (recuperação)** e **D-1 (spin)**, cria o evento
      `Ramp Test (FTP)` no dia e a recuperação **D+1**.
- [ ] `--ftp-test` com data passada/inválida → erro amigável, sem crash.

---

## 10. Timer diário e falhas

- [ ] `scripts/daily_reconcile.sh` roda manualmente sem erro e escreve em
      `logs/daily_reconcile.log`.
- [ ] Service systemd user `cycling-coach-daily` existe e está ativo
      (`systemctl --user status cycling-coach-daily`).
- [ ] Simulação de falha (ex.: credencial errada temporária): script notifica
      via `notify-send` e **sai com código != 0**; o log registra o erro.
- [ ] Restaurar `.env` correto e reexecutar até passar.

---

## 11. Segurança e boas práticas

- [ ] A API key **nunca** aparece na saída de nenhum comando nem nos logs:
      ```bash
      python3 src/training_plan.py info 2>&1 | grep -ci "$(grep -oP '^INTERVALS_API_KEY=\K.*' .env)" 
      # esperado: 0
      ```
- [ ] `git status` não mostra `.env` (deve estar no `.gitignore`).
- [ ] `cp .env.bak .env` restaura o `.env` original ao final do roteiro.

---

## 12. Caça a bugs — áreas de risco (foco da sessão)

Procurar ativamente (registrar mesmo o que for "menor"):

1. **Datas e janelas**: eventos perto da meia-noite; lendas com fuso;
   `reconcile` rodado no sábado/domingo (agenda seg-sex); extra pesado em dia de
   treino perdido no mesmo dia.
2. **Agendas extremas**: `TRAINING_DAYS` com 1 dia, 7 dias, ou só domingo;
   `LONG_DAY` combinado com agenda de 1 dia; `LONG_DAY` + `race` taper juntos.
3. **Valores-limite**: `WEEKLY_HOURS=0.1` / `168` / `1e9`; `FTP` baixo (120W) e
   alto (400W) nos `estimate_tss`; `days-plan` pequeno (2) e grande (90).
4. **Interações**: `volume_scale` × orçamento de TSS; variedade de formato
   (GOAL) × `LONG_DAY` (rotação do ciclo pode anular a variedade?);
   `weekly_hours` × treino de teste de FTP (o `_protect_ftp_test` não deve ser
   escalado).
5. **Arredondamentos**: progressão "X minutos a mais/menos" com `on_sec`
   escalado (minutos inteiros × segundos exatos no `planned_duration`).
6. **push**: `--start` maior que o fim do plano (nenhum evento/nenhum orphan
   apagado por engano); orfanar atividade **feita** (com `paired_activity_id`)
   — pode apagar histórico? (ver KNOWN_ISSUES #1: fantasma MANUAL).
7. **Wellness**: janela sem dados → `info` sem crash; HRV ausente → linha sem
   quebra.
8. **Onboarding**: agente pras datas no `RACE_DATE` com formatos alternativos
   ("01/12/2026", "dezembro"); decisão de confirmar a agenda sugerida vs.
   aceitar qualquer resposta.

---

## 13. Reporte de bugs (template)

Cada bug encontrado amanhã deve virar um bloco como este:

```markdown
## Bug — <título curto>
- Data/horário:
- Contexto (comandos, valores do .env SEM a chave):
- Passos para reproduzir:
  1. ...
  2. ...
- Esperado:
- Obtido (cole a saída):
- Logs/arquivos relevantes:
- Impacto (crítico / funcional / UX / cosmético):
```

Regras: (a) nunca inclua a API key; (b) se o bug for reprodutível, anexe o
comando exato; (c) classifique o impacto para priorizar correções.

---

## 14. Pós-teste

- [ ] Consolidar bugs em `docs/KNOWN_ISSUES.md` e abrir issues no GitHub
      (uma por bug, com o template da seção 13).
- [ ] Atualizar este roteiro: itens não testados, cenários novos descobertos.
- [ ] Decidir correções e planejar a próxima release.
- [ ] Rodar a suíte completa mais uma vez antes de fechar a sessão.
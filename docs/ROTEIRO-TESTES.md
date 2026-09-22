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

- [x] Repo em `<USERHOME>/Work/hermes-coach`, branch `master` em dia com o
      remoto (`git pull`).
- [x] `.env` configurado (credenciais, `FTP`, `TRAINING_DAYS`, `GOAL`) — **faça
      backup antes de mexer**: `cp .env .env.bak`.
- [x] Suíte de regressão verde (baseline — hoje: 122 testes, 1 skip em fim de
      semana):
      ```bash
      python3 -m unittest discover -s tests -v
      ```
- [x] Agente `cycling-coach` linkado no opencode:
      `opencode run --agent cycling-coach --help` não falha.
- [x] Data/hora do sistema corretas (fuso local) — importante para eventos e
      janelas de 7 dias.

> Resultado 22/09: baseline **138 testes OK** (v0.0.14); branch `master` 1
> commit à frente do remoto (rename, `f25959c`, ainda **não pushado**).

---

## 2. Regressão offline (código)

- [x] Testes unitários completos (seção 1) sem nenhuma falha.
- [x] `python3 -c "from src.plan import parse_weekly_hours, parse_long_day"` —
      parsers carregam sem erro.
- [x] Parsers de disponibilidade (via Python):
  - [x] `parse_weekly_hours("5")` → `5.0`; `"5h"` → `5.0`; `"300min"` → `5.0`;
        `"0"`/`"abc"` → `None` (sem crash).
  - [x] `parse_long_day("dom")` → `6`; `"sun"` → `6`; `"xyz"` → `None`.
- [x] `python3 src/training_plan.py build --days 7 --days-plan 14` com
      `.env` **sem** `WEEKLY_HOURS`/`LONG_DAY` → plano idêntico ao comportamento
      anterior (nenhuma regressão).

> Resultado 22/09: parsers conforme roteiro; build sem as variáveis OK
> (sweetspot/zone2 idênticos ao plano antigo; diferenças de threshold = ajustes
> de reconcile prévios).

---

## 3. Onboarding / primeiro uso (agente)

Simular no chat com o agente (conta **nova fictícia**, sem histórico):

- [x] O agente **pergunta primeiro** se o usuário já tem conta no Intervals.icu.
- [x] Com "não tenho conta": orienta criar conta gratuita e conectar plataformas
      via **Settings → Connections** (referencia `docs/SYNC-PLATAFORMAS.md`) e
      **não segue** sem a conta.
- [x] Com "já tenho": vai direto às credenciais (Athlete ID + API Key →
      **Settings → Developer Settings**) com alerta de segurança.
- [x] Pergunta **disponibilidade**: quantos dias, quantas horas (`WEEKLY_HOURS`)
      e melhor dia para treino longo (`LONG_DAY`).
- [x] Resposta **"não tenho tempo para treinos longos no fim de semana"** →
      o agente aceita e propõe encaixar o treino longo no melhor dia informado
      (sem insistir em sábado/domingo).
- [x] Apresenta o **menu de GOAL (1–7)** com a descrição de cada plano antes de
      pedir a escolha.
- [x] Conta nova: avisa que o **TSB está zerado** e calibra em ~2 semanas.

**Anotar bugs de UX/flow** (pergunta confusa, ordem estranha, jargão sem
explicação, ausência de validação etc.). → Nenhum bug de UX encontrado; fluxo
segue a ordem do onboarding.

---

## 4. info e wellness

- [x] `python3 src/training_plan.py info --days 60` → mostra TSB/CTL/ATL.
- [x] Linha `Wellness:` aparece com RHR, sono, passos e/ou HRV (conforme dados
      do Garmin) — sem crash quando não há dados na janela.
- [x] `python3 src/training_plan.py model --days 60` → motor local vs API +
      projeção do plano.

> Resultado 22/09: TSB -9.2 → mudou para -1.8 ao longo da sessão (dado vivo —
> atividades reais sincronizadas); wellness RHR 55 / sono 7.3h / passos / HRV
> sem suporte do FR935 (linha omite HRV sem quebrar).

---

## 5. build e disponibilidade (é a área com código novo — foco redobrado)

Preparação: `cp .env .env.bak` e edite `.env` entre os cenários.

- [x] **Horas baixas**: `WEEKLY_HOURS=2` → o `build` reduz as durações;
      nenhum treino fica com esforço (`on_sec`) abaixo de 120s.
- [x] **Horas altas**: `WEEKLY_HOURS=12` → durações crescem até o teto (1.5x),
      sem estourar o orçamento semanal de TSS.
- [x] **Formato aceito**: `WEEKLY_HOURS=5h` e `WEEKLY_HOURS=300min` → mesmo
      resultado que `5`.
- [x] **Valores inválidos**: `WEEKLY_HOURS=muitas` → aviso no `build` e plano
      **sem** ajuste (sem crash).
- [x] **LONG_DAY dentro da agenda** (ex.: `LONG_DAY=dom` com `TRAINING_DAYS`
      incluindo domingo) → o treino endurance/longo cai no domingo.
- [x] **LONG_DAY fora da agenda** (ex.: `LONG_DAY=dom`, agenda seg-sex) → o
      treino longo cai no **dia de treino mais próximo** (sem forçar fim de
      semana).
- [x] **LONG_DAY inválido** → aviso no `build`, sem alteração de posição.
- [x] **Sem as variáveis** → comportamento atual preservado.
- [x] **build preserva o treino de hoje** ao regerar o plano. → **BUG #7**:
      esse caminho **descarta `WEEKLY_HOURS`/`LONG_DAY`** na recursão
      (`src/plan.py:373-376`) — scaling de disponibilidade não é aplicado
      silenciosamente quando o plano já tem o treino de hoje.
- [x] **GOAL=race sem `RACE_DATE`** → o `build` pergunta a data alvo (obrigatória)
      e recusa data passada/inválida.
- [x] **GOAL=race com prova próxima** → últimos 7 dias viram **Taper (pre-prova)**.
- [x] `build` imprime `Disponibilidade: ...h/semana | treino longo: ...`.

---

## 6. reconcile

Fixture real (últimos dias): compare `plan.json` x treinos feitos.

- [x] Treino **perdido** (planejado e não feito em dia passado) → insere
      **Recuperação** no próximo dia de treino. *(validado via testes unitários
      determinísticos — sem injetar perda no calendário real)*
- [x] Treino perdido → próximo **Limiar reduzido em 5%** (uma única vez por
      treino). *(idem)*
- [x] Treino **extra pesado** fora do plano (carga ≥ cap diário nos 7 dias) →
      insere recuperação no próximo dia de treino (sem empilhar com a do
      perdido). *(idem)*
- [x] Treino extra **leve** → plano não muda (`plan2 == plan`). *(idem)*
- [x] Extra **fora da janela de 7 dias** → ignorado. *(idem)*
- [x] `reconcile` **não muda o tamanho do plano** (substitui dias). *(idem)*
- [x] `python3 src/training_plan.py reconcile --show` imprime agenda + ajustes.
      → run real sem treinos perdidos; **BUG #8**: `reconcile` regrava
      `plan.json` como lista pura e descarta a meta (`goal/race_date/
      ftp_test_date`).

---

## 7. push e calendário

- [x] **Sempre** `python3 src/training_plan.py push --dry-run` antes do push real.
- [x] `push --start YYYY-MM-DD` → `POST /events/bulk?upsert=true` ok (HTTP 200).
- [x] Eventos **órfãos** `hermes-plan*` (não estão no plano atual) são
      removidos automaticamente; outros apps não são tocados. → verificado no
      timer (S10): "Orfaos removidos (HTTP 200): 1"; remoção só na janela a
      partir de `--start` (não toca passado nem atividades feitas).
- [x] No app do Intervals (Custom Workouts), a descrição renderiza no formato
      nativo: `8m 88% (141w)`, com mensagem explicativa antes de cada passo.
- [x] Textos em pt (`CUE_LANG=pt`) e en (`CUE_LANG=en`) corretos; `CUE_LANG`
      inválido → fallback para `pt` com aviso. *(nota: chamada direta a
      `workout_text`/`event_payload` com `lang='zz'` dá `KeyError` — inalcançável
      pela CLI; ver KNOWN_ISSUES)*
- [x] Nenhum cue contém `%` nem duração abreviada (`6m`, `30s`) fora do target.
- [x] Mensagem de progressão aparece quando há treino anterior do mesmo foco
      ("Isso sao X minutos a mais que o ultimo treino de Limiar FTP").

---

## 8. Troca de objetivo no meio do plano (agente)

- [x] "quero treinar pra prova de dezembro" → agente mapeia para `race`,
      pergunta `RACE_DATE`, atualiza `.env`, roda `build` **preservando o treino
      de hoje** e explica o que muda na frente.
- [x] Pede **confirmação antes do `push`** (não publica sozinho).
- [x] Trocar para objetivo não-`race` → `RACE_DATE` **remove** do `.env`.
- [x] Mudar só a data de um `race` em curso → atualiza e re-build sem quebrar.

---

## 9. Teste de FTP

- [x] `python3 src/training_plan.py ftp-check` → mostra último teste, dias desde
      o teste e se o reteste é devido (janela pelo tipo de plano).
- [x] Quando devido, sugere o **Ramp Test do Zwift** (não agenda sozinho).
- [x] `python3 src/training_plan.py build --ftp-test 2026-10-22` (data futura):
      protege **D-2 (recuperação)** e **D-1 (spin)**, cria o evento
      `Ramp Test (FTP)` no dia e a recuperação **D+1**. *(executado com
      `--days-plan 45`: o teste precisa cair dentro do horizonte do plano —
      ver `_protect_ftp_test`)*
- [x] `--ftp-test` com data passada/inválida → erro amigável, sem crash.

> Extras validados: eventos de teste **não** são escalados por `WEEKLY_HOURS`
> (Recuperação 60m, Spin/Ramp/pos 50m fixos — por design).

---

## 10. Timer diário e falhas

- [x] `scripts/daily_reconcile.sh` roda manualmente sem erro e escreve em
      `logs/daily_reconcile.log`.
- [x] Service systemd user `cycling-coach-daily` existe e está ativo
      (`systemctl --user status cycling-coach-daily`). → timer ativo, próximo
      run 00:00.
- [x] Simulação de falha (ex.: credencial errada temporária): script notifica
      via `notify-send` e **sai com código != 0**; o log registra o erro.
      → exit 1 + traceback 401 no log.
- [x] Restaurar `.env` correto e reexecutar até passar. → exit 0.

---

## 11. Segurança e boas práticas

- [x] A API key **nunca** aparece na saída de nenhum comando nem nos logs:
      ```bash
      python3 src/training_plan.py info 2>&1 | grep -ci "$(grep -oP '^INTERVALS_API_KEY=\K.*' .env)" 
      # esperado: 0
      ```
- [x] `git status` não mostra `.env` (deve estar no `.gitignore`).
- [x] `cp .env.bak .env` restaura o `.env` original ao final do roteiro.
      → `.env` idêntico ao `.env.bak` (conferido com `diff`).

---

## 12. Caça a bugs — áreas de risco (foco da sessão)

Procurar ativamente (registrar mesmo o que for "menor"):

1. **Datas e janelas**: eventos perto da meia-noite; lendas com fuso;
   `reconcile` rodado no sábado/domingo (agenda seg-sex); extra pesado em dia de
   treino perdido no mesmo dia.
   → **não testado** (meia-noite/fuso exigem fixture de tempo; coberto por
   testes unitários das janelas). Reconcile de fim de semana coberto por
   fixtures determinísticas nos testes.
2. **Agendas extremas**: `TRAINING_DAYS` com 1 dia, 7 dias, ou só domingo;
   `LONG_DAY` combinado com agenda de 1 dia; `LONG_DAY` + `race` taper juntos.
   → coberto por testes unitários (fixtures determinísticas); `race` + taper OK.
3. **Valores-limite**: `WEEKLY_HOURS=0.1` / `168` / `1e9`; `FTP` baixo (120W) e
   alto (400W) nos `estimate_tss`; `days-plan` pequeno (2) e grande (90).
   → executado: `168` OK (clamp), `1e9` aviso, `FTP=120`/`400` sem crash
   (TSS igual — intensidade relativa, esperado), `days-plan 2` e `90` OK.
4. **Interações**: `volume_scale` × orçamento de TSS; variedade de formato
   (GOAL) × `LONG_DAY` (rotação do ciclo pode anular a variedade?);
   `weekly_hours` × treino de teste de FTP (o `_protect_ftp_test` não deve ser
   escalado).
   → `weekly_hours` × teste de FTP **validado**: eventos do teste ficam fixos;
   treinos normais escalam. Rotação × LONG_DAY: OK nos cenários S5.
5. **Arredondamentos**: progressão "X minutos a mais/menos" com `on_sec`
   escalado (minutos inteiros × segundos exatos no `planned_duration`).
   → mensagem correta com `on_sec` escalado (S7, CUE_LANG=en e pt).
6. **push**: `--start` maior que o fim do plano (nenhum evento/nenhum orphan
   apagado por engano); orfanar atividade **feita** (com `paired_activity_id`)
   — pode apagar histórico? (ver KNOWN_ISSUES #1: fantasma MANUAL).
   → `--start` além do fim: `dry-run: enviaria 0 eventos`, nada removido.
   Atividade feita fora da janela de orfanos (só janela ≥ start) — seguro.
7. **Wellness**: janela sem dados → `info` sem crash; HRV ausente → linha sem
   quebra.
   → janela com dados OK; HRV ausente (FR935) sem quebra (S4); janela vazia
   coberta por testes.
8. **Onboarding**: agente pras datas no `RACE_DATE` com formatos alternativos
   ("01/12/2026", "dezembro"); decisão de confirmar a agenda sugerida vs.
   aceitar qualquer resposta.
   → formatos alternativos **não testados** no agente (agente pede YYYY-MM-DD;
   CLI rejeita data inválida/passada).

**Bugs encontrados na sessão:**
- **#7** (funcional): build preserva treino de hoje → ignora
  `WEEKLY_HOURS`/`LONG_DAY` (`plan.py:373-376`).
- **#8** (baixo impacto): reconcile regrava `plan.json` sem meta
  (`training_plan.py::cmd_reconcile` → `save_plan` sem goal); vai ficar
  funcional com a #6.
- Nota defensiva: `workout_text`/`event_payload` com `lang` inválida → `KeyError`
  (inalcançável via CLI; `get_cue_lang` normaliza).

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

- [x] Consolidar bugs em `docs/KNOWN_ISSUES.md` e abrir issues no GitHub
      (uma por bug, com o template da seção 13). → issues **#7** e **#8**
      abertas; KNOWN_ISSUES.md atualizado.
- [x] Atualizar este roteiro: itens não testados, cenários novos descobertos.
- [x] Decidir correções e planejar a próxima release. → ver resumo abaixo.
- [x] Rodar a suíte completa mais uma vez antes de fechar a sessão. → **138 OK**.

### Próxima release (planejamento)

1. **Corrigir #7** (funcional, prioritário): repassar `weekly_hours`/`long_day`
   na recursão de preservação do treino de hoje + teste de regressão
   (`WEEKLY_HOURS=2` com plano contendo hoje).
2. **Corrigir #8** antes da #6: `reconcile` regrava a meta
   (`save_plan(plan, PLAN_FILE, **load_plan_meta())`) + teste
   build → reconcile → meta preservada.
3. Em seguida, retomar a **#6** (FTP sugerido de treinos não agendados —
   `src/ftp_estimation.py` já implementado; falta integração streams/CLI).
4. Decidir push do rename (`master` 1 commit à frente: `f25959c`) e bump de
   versão (v0.0.15) junto das correções.
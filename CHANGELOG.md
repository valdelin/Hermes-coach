# Changelog

Todas as mudanças relevantes do **Hermes Coach**. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o versionamento,
[SemVer](https://semver.org/lang/pt-BR/).

As versões aqui correspondem às **tags** do repositório (git tag) e aos
[releases publicados no GitHub](https://github.com/valdelin/Hermes-coach/releases).
As versões intermediárias (v0.0.3–v0.0.6) foram bumpados no `VERSION` sem tag
própria — foram agrupadas na tag/release v0.0.7.

## [0.0.23] - 2026-09-24

### Adicionado

- **Temas no relatório (`--theme TEMA`)** — o export HTML/PDF leva os **22
  temas** do kit de identidade `src/brand.py` (inspirados nos color schemes do
  Omarchy quattro; hex dos `colors.toml` reais). No HTML o leitor troca pelo
  menu **"Temas"** (ou tecla **T**) a qualquer momento; a escolha fica no
  `localStorage` (`hc-theme`); PDF honra o tema passado na CLI. Corrigido bug
  de cascata do CSS: o `:root` (tema padrão) agora é emitido **antes** de todos
  os `[data-theme]` — mesma especificidade, e quem vem depois vence (antes, o
  tokyo-night sobrescrevia os 18 temas listados antes dele no CSS).
- **Forma (TSB) colorida por zona do atleta** — a linha de forma muda de cor
  conforme o estado (como no Intervals/Friel): **risco** (TSB ≤ −10, vermelho),
  **ideal** (−10..+10, verde) e **fresco** (≥ +10, azul). Cores por tema
  (`fresh`/`risk`); segmento Bezier a segmento + ponto final e chip **"Estado"**
  no resumo do PMC. Descrição do PMC reescrita (explicação S2S/Friel + refs:
  *Monitoring your training load* — Science2Sport; *Managing Training Using
  TSB* — Joe Friel).
- **`docs/TEMAS.md`** — kit portátil dos temas: tokens documentados, consumo
  em CSS (com a regra de ouro da ordem do `:root`), switcher JS mínimo e o
  módulo completo copiável para outro projeto.
- Gráficos do `summary` (PMC 90d + carga semanal) e `--export` HTML/PDF
  (gráficos + temas) — seção 0.0.23 (mesma release).

### Testes

- +6 (268 → **274**): zonas da forma (segmentos risco/ideal/fresco + estado de
  risco + refs na descrição) e regressão da ordem do CSS (todos os 22 temas
  com bloco `[data-theme]` e `--fresh`/`--risk`; `:root` antes).
- Validação real no chromium headless: **os 22 temas** resolvem as três cores
  de zona corretamente.

## [Unreleased]

_Próximas mudanças a documentar._

## [0.0.22] - 2026-09-24

### Adicionado

- **`summary` — resumo dos treinos realizados** por período (dia/semana/mês):
  janela terminando no dia-ancla (por padrão ontem), usando só atividades
  pareadas (planejado-não-feito fica fora). Agrega sessões, carga total (TSS),
  tempo, distância, elevação, potência média/NP e FC média (ponderadas pelo
  tempo), e lista o detalhe de cada treino feito. Módulo `src/activity_summary.py`.

### Testes

- +13 (233 → **246**): `tests/test_activity_summary.py` (janela de período,
  filtro de treinos feitos, agregados ponderados, formatação) e CLI `summary`
  no `tests/test_training_plan.py`.

## [0.0.21] - 2026-09-23

### Adicionado

- **`recovery` — retorno a forma**: varre todo o histórico real do Intervals
  (só treinos feitos, com atividade pareada; planejado-nao-feito fica fora),
  reconstrói o PMC (CTL/ATL/TSB, EWMA 42/7, hiatos com zero) do primeiro dia
  até hoje e compara o estado atual com o pico histórico (CTL, melhor mês,
  TSB). Estima o prazo (semanas/meses) de volta a 90%/99% do CTL de pico sob
  rampas conservadora/realista/otimista (deload a cada 4 semanas, teto =
  carga que sustenta o CTL-alvo) e prescreve a rampa semanal de TSS
  (`recovery --weeks N --ramp-pts R`). Módulo `src/recovery.py` (backlog #19).

### Testes

- +17 (216 → **233**): `tests/test_recovery.py` (carga só de treinos feitos,
  série PMC com hiatos, estado/pico, estimativa de retorno, rampa com deload)
  e CLI `recovery` no `tests/test_training_plan.py`.

## [0.0.20] - 2026-09-23

### Adicionado

- **Taper progressivo para `GOAL=race`** (periodização do Joe Friel, case
  study 2010): a última semana antes da prova deixa de ser "Z2 uniforme 20'"
  e vira preparação por fases — **D-6** último estímulo de qualidade
  (Limiar curto ~2×6' "abrir a perna"), **D-5..D-3** recuperação Z2 curta,
  **D-2/D-1** spin muito leve (<60% FTP). Nomes por fase no plano.
- **Evento do dia da prova**: o plano garante `Prova: dia de prova` na data
  (mesmo fora da agenda de treino; TSS 0 = marcador, a carga real entra pela
  API) e **D+1** recuperação pós-prova quando é dia de treino.
- **Projeção de TSB no dia da prova (#16 — semente)**: `build` com
  `GOAL=race` projeta o TSB em `RACE_DATE` via Expected PMC e compara com a
  faixa-alvo `−10..+20` (Friel ~+20; S2S: individual), avisando se o atleta
  chega **cansado** (`< −10`) ou **passou do pico** (`> +20`).

## [0.0.19] - 2026-09-23

### Adicionado

- **Indicadores de zona extrema no Expected PMC (#17 — Friel)**:
  `forecast_pmc()` etiqueta cada dia da projeção com a **zona de TSB** de Joe
  Friel (`high-risk` < −30, `optimal` −30..−10, `grey` −10..+5, `freshness`
  +5..+25, `transition` > +25) via `_tsb_zone()`; retorna listas
  `high_risk`/`transition` e o `model` imprime a zona por linha + avisos de
  R&R (risco alto) e descanso longo (transição).
- **Módulo de corrida a pé (backlog #18)** — esporte #2 registrado no ROADMAP:
  `sport` no domínio, limiar por pace/LTHR, `rftp-scan`, carga via Intervals
  (rTSS), workouts de corrida em FIT, metas 5K/10K/meia/maratona, **PMC único
  multi-esporte**. **Possível — validar c/ treinador.**
- **Issue #3 fechada** — prescrição sem medidor de potência (%FTHR + RPE,
  target `HEART_RATE`, modo FC) validada na suíte (202 testes); ROADMAP nº 3
  refletido como fechado.
- **Docs (acumulado 22–23/09):** glossário de acrônimos (`docs/GLOSSARIO.md`);
  benchmark Tredict + referências de ciência **Joe Friel/Science to Sport** no
  ROADMAP (backlog #13–#17); pitch deck atualizado (Tredict, v0.0.18); portal
  de acesso (desenho v0, `docs/PORTAL-UI-DESIGN.md`); containerização + guia
  de deploy (`dev/DEPLOY.md`); repo privado.

### Testes

- +4 (198 → **202**): zonas de TSB — risco alto, transição, frescor (bordas) e
  plano vazio com `high_risk`/`transition` vazios.

## [0.0.18] - 2026-09-22

### Adicionado

- **Expected PMC (projeção de CTL/ATL/TSB do plano)** — nova
  `forecast_pmc()` em `src/impulse_response.py` mistura o real com o
  planejado: carga dos eventos até hoje (com dias de descanso zerados, sem
  comprimir o decaimento exponencial) + `tss` do `plan.json` de amanhã em
  diante. Retorna a série diária `(data, CTL, ATL, TSB)`, além de **alertas
  quando a projeção cruza TSB ≤ −10** (mesmo gatilho do portal). O `model`
  agora imprime a tabela da projeção e o aviso; com `initial_ctl/atl` da API
  simula só o futuro, e sem elas o histórico real estabelece o ponto de
  partida (fallback).
- **Plan Adherence (relatório de cumprimento)** — nova `adherence_report()`
  em `src/plan.py` reutiliza o critério de conclusão do `reconcile`
  (`_done_and_extra`): cada treino planejado é `feito`/`perdido`/`pendente`,
  agregado por semana ISO com % de cumprimento. Novo subcomando `adherence`
  imprime o relatório (hoje o `build` só listava os `missed` de passagem).
- **Testes**: +16 (181 → 197) — ancoragem de data, decaimento em dia de
  descanso, múltiplos treinos no mesmo dia, horizonte, alerta TSB, agrupamento
  semanal e classificação done/missed/pending.

### Corrigido

- **`adherence` contava o treino de hoje como "perdido"** no meio do dia: só
  o que efetivamente venceu (dia estritamente anterior) deve ser `perdido` —
  o de hoje, ainda não concluído, é `pendente`. Alinhe com o critério do
  `reconcile` (`w["day"] < today`). Sem o alinhamento, um plano com treinos
  pela manhã mostrava % de cumprimento artificialmente baixo (ex.: W39 saía
  `1 feito / 1 perdido` antes do treino do dia acontecer). Teste
  `test_treino_de_hoje_ainda_nao_conta_como_perdido` cobre o caso. (198 testes)

## [0.0.17] - 2026-09-22

### Corrigido

- **CLI quebrava ao carregar qualquer comando** (`info`/`build`/`push`/etc.)
  com `ValueError: badly formed help string`: o help do argparse de
  `--no-power` continha `%FTHR` sem escapar — argparse interpreta `%` como
  formato e abortava a montagem do parser. Escapado para `%%FTHR` nos dois
  subparsers (`build` e `all`). **Derrubaria o timer diário à meia-noite.**
  Encontrado pelo novo `dev/diagnose.sh`.

### Adicionado

- **Diretório `dev/`** — diagnóstico e recuperação para quando a aplicação
  quebrar: `dev/DIAGNOSTICO.md` (fluxo de investigação passo a passo) +
  `dev/diagnose.sh` (snapshot de estado: versão, timer systemd, log, `plan.json`,
  `.env` sanitizado, health check via `info` e suíte de testes).
- **Docs: benchmark de mercado + avaliação comercial** — Xert/Pillar/TriDot/
  RunDot (preços, prescrição, posicionamento) e avaliação de produto
  (ADR-003 como treinador automático por cima do Intervals, não app de tracking).
- **Docs: pitch deck para investidor** — `docs/PITCH-DECK.md` (12 slides,
  texto de tela + notas do apresentador) + `docs/PITCH-DECK-SLIDES.md` (versão
  só-slides para importar no Gamma). Ask proposto: US$ 25k, meta 100 atletas +
  3 treinadores (~US$ 82k ARR). Estratégia de beta testers (treinadores
  conhecidos) embutida nos slides 7/9/12 e no ROTEIRO-TREINADOR.
- **Docs: diagramas UML do sistema** — `docs/DIAGRAMAS.md` com 6 diagramas
  Mermaid (componentes, sequência do timer diário, ciclo manual
  build/reconcile/push, classes, decisão de foco, estados de evento) + PNGs
  renderizados em `docs/diagramas/` para o pitch deck.

## [0.0.16] - 2026-09-22

### Adicionado

- **Issue [#3](https://github.com/valdelin/Hermes-coach/issues/3)** —
  **implementado** (treinos **sem medidor de potência / modo FC**):
  - `FTHR` no `.env` (bpm) e `build --no-power`: o plano passa a prescrever em
    **%FTHR + RPE** (`FOCUS_HR_PCT`/`FOCUS_RPE`/`FOCUS_HR_HINT`, alvo em bpm
    via `hr_target_bpm`), e o `push` envia os eventos com
    `target: HEART_RATE` (o texto do Intervals mantém a regra de cues sem `%`/
    duração abreviada);
  - `reconcile` **preserva o modo FC** ao reescrever treinos (recuperação,
    limiar reduzido);
  - `info`/`reconcile` avisam **"Plano em modo FC — sem medidor de potência;
    carga estimada por FC (icu_training_load)"**;
  - a **carga real** sem watts segue do Intervals (`average_heartrate` →
    `hr_load`/`icu_training_load`), sem TRIMP local.

## [0.0.15] - 2026-09-22

### Adicionado

- **Issue [#6](https://github.com/valdelin/Hermes-coach/issues/6)** — **implementado**
  (comando `ftp-scan`): **FTP sugerido a partir de treinos fora do plano**.
  Detecta eventos pareados não-hermes, aplica filtros baratos no detalhe
  (não-MANUAL, ≥ 45 min, com potência, intensidade ≥ 75% do FTP), estima via
  melhor média móvel de 20 min × 0,95 (`src/ftp_estimation.py`) com gates de
  qualidade, propõe **somente para cima** (+3%..+30%), exige **confirmação
  antes de aplicar** e, no sim, atualiza `.env FTP` (+ `.env.bak`) e o
  `indoor_ftp` via `PUT /athlete/{id}/sport-settings/{ride}`. Candidatos ficam
  na meta do `plan.json` (`ftp_candidates`, com `applied`), preservada por
  `build`/`reconcile`; `info`/`ftp-check` avisam quando há pendência. Detalhes
  em `docs/KNOWN_ISSUES.md`.
- **`src/ftp_estimation.py`** (mecânica pura #6, determinística): `best_effort`
  (melhor média móvel, padrão 20 min), `clean_power` (clipe de spikes
  > 2,5× mediana, suporta anomalias da plataforma — só subestima) e
  `analyze_ride` → `proposed_ftp = round(best20 × 0,95)` com gates
  **CV ≤ 15%**, **min ≥ 80% da média** (anti-apagão) e **diff do atual em
  +3%..+30%** (só propõe para cima; >+30% = anomalia). 16 testes sintéticos;
  validado com dados reais (treinos agendados reprovam/sem novidade, como
  esperado).
- **`README.md`**: nova seção **"O que o cycling coach faz"** — inventário das
  capacidades (plano/cargas, GOAL, FTP, automação, segurança) + contagem de
  testes corrigida.

### Corrigido

- **#7** — `build` preservava o treino de hoje **descartando `WEEKLY_HOURS`/
  `LONG_DAY`**: a chamada recursiva agora repassa as duas opções (o treino de
  hoje preservado não é escalado). Testes `PreserveTodayWithAvailabilityTest`.
- **#8** — `reconcile` regravava `plan.json` **sem a meta**: agora carrega e
  regrava a meta (`goal`/`race_date`/`ftp_test_date`). Testes
  `ReconcileMetaTest`. Pré-requisito da #6 (os `ftp_candidates` vivem na meta).

### Atualizado

- **`docs/KNOWN_ISSUES.md`**: #7 e #8 marcadas **corrigidas** (2026-09-22);
  nota operacional do incidente do timer (evento de hoje apagado e restaurado);
  entrada nova da #6 (implementada).
- **`docs/ROTEIRO-TESTES.md`**: resultados completos da sessão de testes de
  22/09 (S1-S14 + bug hunt + correções).
- **`docs/ROADMAP.md`** sincronizado com o estado real (revisão de 21/09):
  registro dos 5 itens em aberto (#1–#3, #6, #7), dos fechados (#4, #5 —
  resta validação com treinador), da Fase 3 parcialmente iniciada no agente
  (onboarding + disponibilidade, v0.0.10–0.0.11) e do roteiro de testes
  (`docs/ROTEIRO-TESTES.md`, execução em 22/09). Na v0.0.15 o #6 entra nos
  **fechados** (ftp-scan entregue).
- Vault do Obsidian sincronizado: `HISTORICO.md` (entradas 2026-09-20 e
  2026-09-21), `PLANO-NOVAS-IMPLEMENTACOES.md` (status atual 2026-09-21) e
  cópia do `ROTEIRO-TESTES.md`.
- **Prioridade da #1 reduzida** (decisão 2026-09-21): a "fantasma" é
  **cosmética** e é comportamento do **Intervals**, não do agente —
  label `priority: low` criado no repo e aplicado à issue; documentado em
  `docs/KNOWN_ISSUES.md`; #1 saiu do início da sessão de testes de 22/09.

## [0.0.14] - 2026-09-21

## [0.0.13] - 2026-09-21

### Adicionado

- **`docs/ROTEIRO-TESTES.md`** — roteiro de testes manual/semi-automático para a
  sessão de validação: baseline de regressão, onboarding, info/wellness, build e
  disponibilidade (`WEEKLY_HOURS`/`LONG_DAY`), reconcile, push/calendário,
  troca de objetivo, teste de FTP, timer diário, segurança, áreas de risco para
  caça a bugs e template de reporte.

### Corrigido

- **`test_treino_perdido_insere_recuperacao` dependente do dia da semana**:
  com `start=hoje-2` e `days=5`, o plano não tinha nenhum dia passado de
  segunda a sexta (só passava em sáb/dom). Fixture agora usa `start=hoje-7`,
  que garante dias de treino passados em qualquer dia da semana.

## [0.0.12] - 2026-09-20

### Corrigido

- **`test_reconcile_mix_realista_eventos` dependente do dia da semana**: o
  fixture usava `missed=past[1]` + `anchor=today-2`, então os destinos das duas
  recuperações coincidiam (e o reconcile deduplicava "recuperação já
  programada") em seg/ter/qua/dom — o teste só passava em qui/sex/sáb. Novo
  fixture é determinístico (`start=today-6`, perdido = treino passado mais
  antigo, extra ancorado em `today-2`), validado para os 7 dias da semana.

## [0.0.11] - 2026-09-20

### Adicionado

- **Disponibilidade semanal do atleta** (antes de criar/regenerar o plano, o
  agente pergunta): **quantos dias** por semana disponíveis, **quantas horas**
  por semana (`WEEKLY_HOURS` no `.env`) e **melhor dia para treinos longos**
  (`LONG_DAY` no `.env`). Se o atleta não tem tempo para treinos longos no fim
  de semana, o agente aceita e adapta o plano para o melhor dia informado.
  - `build` escala a duração dos treinos (mínimo 120s por esforço) para a semana
    caber nas horas disponíveis — o orçamento de TSS continua mandando
    (`plan.py::_volume_scale`/`_scale_duration`, fator 0.5x–1.5x);
  - `build` rotaciona o ciclo semanal para o treino longo/endurance cair no dia
    preferido (ou no dia de treino mais próximo, quando `LONG_DAY` não é dia de
    treino — `plan.py::_place_long_day`);
  - `parse_weekly_hours` (aceita `5`, `5.5`, `5h`, `300min`) e `parse_long_day`
    (nomes em pt/en) com fallback seguro sem ajuste de volume/posição;
  - 17 testes novos (122 no total).

## [0.0.10] - 2026-09-20

### Adicionado

- **Wellness implementado** (issue
  [#4](https://github.com/valdelin/Hermes-coach/issues/4)): o sync Garmin
  Connect → Intervals.icu já entrega RHR/sono reais; `info` agora exibe
  `Wellness:` — RHR atual + média 7d, sono (h), passos e HRV quando houver
  (`wellness_summary`/`format_wellness`). **Decisão HRV (FR935)**: sem HRV
  Status overnight (requer Elevate Gen 3+); monitorar via Oura/WHOOP ou novo
  relógio fica no backlog. 5 testes novos (105 no total).
- **Onboarding (primeiro uso)** no agente `cycling-coach`: ao montar o primeiro
  plano, o agente conduz a configuração no chat — pergunta se o atleta **já tem
  conta no Intervals.icu** (se não, orienta criar conta gratuita e conectar as
  plataformas via **Settings → Connections**; guia em
  `docs/SYNC-PLATAFORMAS.md`), coleta **Athlete ID + API Key** (Settings →
  Developer Settings, com alerta de segurança), pergunta `TRAINING_DAYS`,
  `CUE_LANG`, `FTP` e o objetivo, e só então gera o plano (conta nova: TSB
  zerado calibra em ~2 semanas).
- **Menu de objetivos (GOAL)** no agente: ao pedir o objetivo, apresenta os 7
  planos com a descrição de cada (`back-to-fitness`, `ftp-builder`,
  `gran-fondo`, `time-trial`, `climbing`, `active-off-season`, `race`).
- **Trocar objetivo no meio do plano**: o agente recebe a intenção em linguagem
  natural, mapeia para o `GOAL` (perguntando `RACE_DATE` quando `race`), atualiza
  o `.env`, roda `build` **preservando o treino de hoje**, explica o que muda e
  pede confirmação antes do `push`; trocar para objetivo não-`race` remove
  `RACE_DATE` do `.env`.
- **Correção Basic Auth** na documentação: o Intervals.icu usa HTTP Basic Auth
  com **username fixo `API_KEY` e senha = a sua API key** (antes constava
  "usuario = senha = API_KEY", impreciso).
- `SKILL.md` do cycling-coach passa a descrever o onboarding e a troca de
  objetivo no meio do plano (versão 2.5.0 → 2.6.0); `README.md`/`README.en.md`
  ganham a seção **Primeiro uso (onboarding)**.

## [0.0.9] - 2026-09-19

### Adicionado

- `docs/KNOWN_ISSUES.md`: rastreio de bugs conhecidos do projeto. Registrada a
  issue [#1](https://github.com/valdelin/Hermes-coach/issues/1) — o Intervals
  materializa o evento `hermes-plan*` como atividade MANUAL "fantasma" ao
  sincronizar o treino (sem endpoint de merge na API; proposta de limpeza
  automática registrada para o futuro).
- **TODO registrado** (issue
  [#2](https://github.com/valdelin/Hermes-coach/issues/2)): enviar resumo do
  treino por **e-mail, WhatsApp ou Telegram** (foco + TSB + TSS previsto/real +
  avisos do reconcile) — adicionado às **Direções futuras** do README.
- **TODO registrado** (issue
  [#3](https://github.com/valdelin/Hermes-coach/issues/3)): suporte a **treinos
  sem medidor de potência** (outdoor/FC) — detectar ausência de potência,
  `FTHR` no `.env`, carga por FC (`hrTSS`) e alvos %FTHR/RPE — adicionado às
  **Direções futuras** do README.
- `docs/ROADMAP.md`: plano consolidado das próximas implementações (fases
  0-4, issues #1-#3 + produto estilo Runna + multi-atleta); README agora
  aponta para o roadmap.
- **TODO registrado** (issue
  [#4](https://github.com/valdelin/Hermes-coach/issues/4)): **ativar sync de
  wellness** (Garmin Connect → Intervals.icu: RHR, sono, Body Battery;
  avaliar HRV para o futuro) — adicionado às **Direções futuras** do README e
  ao roadmap (Fase 0).
- `docs/SYNC-PLATAFORMAS.md`: guia de sincronização de **cada plataforma
  compatível** com o Intervals.icu (Garmin, Zwift, Wahoo, Strava, Polar,
  COROS, Suunto, Amazfit, Huawei, Dropbox, Oura/WHOOP, Apple Health) —
  atividades, wellness, treinos planejados e regras anti-duplicatas; link na
  seção Documentação do README.
- **TODO registrado** (issue
  [#5](https://github.com/valdelin/Hermes-coach/issues/5)): **tipos de plano
  de treino** (`GOAL` no `.env`): `back-to-fitness`, `ftp-builder`,
  `gran-fondo`, `time-trial`, `climbing`, `active-off-season` e `race` (com
  `RACE_DATE` + tapper) — muda a distribuição de focos no `build` conforme o
  tipo; **`race` sempre pergunta a data alvo (dia da prova)** antes de montar
  o plano (sem default/campo vazio); adicionado às **Direções futuras** do
  README e ao roadmap (Fase 2).
- **Tipos de plano implementados** (issue
  [#5](https://github.com/valdelin/Hermes-coach/issues/5), Fase 2):
  - `GOAL` no `.env` — `back-to-fitness`, `ftp-builder`, `gran-fondo`,
    `time-trial`, `climbing`, `active-off-season` e `race`; ausente/inválido
    mantém o comportamento padrão por TSB (fallback seguro);
  - `GOAL_TEMPLATES` (distribuição de focos por TSB e por tipo) e
    `GOAL_BUDGET_SCALE` (calibração de carga: off-season ~60% vs race ~120%);
  - **variedade de formato**: com `GOAL` ativo o `build` alterna estruturas
    do mesmo foco (séries curtas/longas, contínuos) — plano não monótono;
    sem `GOAL`, o template atual é preservado;
  - `race` **sempre pergunta a data alvo** (`RACE_DATE`, futura) antes de
    montar o plano e salva no `.env`; nos últimos 7 dias antes da prova os
    treinos viram **Taper (pre-prova)** (zona 2, TSS baixo);
  - `plan.json` guarda `goal`/`race_date` (formato `{"goal", "race_date",
    "workouts"}`); `load_plan` continua devolvendo a lista (compatível com o
    formato antigo);
  - 24 testes novos (88 no total); docs atualizadas (README, ROADMAP).
- **Janela de reteste do FTP segue o tipo de plano** (`ftp-check`): ao final
  de cada bloco — `ftp-builder`/`gran-fondo` **6 semanas**, `time-trial`/
  `climbing`/`race` **4 semanas**, `back-to-fitness`/`active-off-season`
  **8 semanas**; sem `GOAL` mantém 8 semanas. 5 testes novos (93 no total).
- **Preparação prévia do teste de FTP** (consenso dos treinadores: teste =
  "mini dia de prova", sem fadiga acumulada): `build --ftp-test YYYY-MM-DD`
  (ou `FTP_TEST_DATE` no `.env`) protege as **48h antes** — D-2 vira
  Recuperação, D-1 vira Spin fácil (<65% FTP), D0 recebe o evento
  `Ramp Test (FTP)` (mesmo fora da agenda, como lembrete) e D+1
  Recuperação pós-teste; dias de descanso natural não são tocados.
  `plan.json` guarda `ftp_test_date`. 7 testes novos (100 no total).

### Alterado

- **Intervals.icu (conta do atleta):** `indoor_ftp` **210 → 182W** via API
  (`PUT /sport-settings/{id}`), alinhando o FTP indoor ao ramp test de
  2026-09-10 (`.env` = 182). Motivo: pausa de ~2 anos sem treinar —
  o 210 era o FTP da época; o 182 reflete a condição atual. **Histórico
  preservado**: atividades antigas mantêm `icu_ftp=210` congelado (sem
  recálculo retroativo); o novo valor vale para rides virtuais a partir de
  2026-09-19.

## [0.0.8] - 2026-09-18

### Adicionado

- **Motor de carga fisiológica (Banister Impulse-Response)** — `src/impulse_response.py`,
  implementando o spec da seção 1 do `docs/ARQUITETURA.md`:
  - `ImpulseResponseEngine.calculate_tss(duration, avg_intensity, threshold)` — TSS padrão
    `IF² × horas × 100` (retorna 0 para threshold ≤ 0);
  - `ImpulseResponseEngine.compute_metrics(daily_tss_history, initial_ctl, initial_atl)` —
    suavização exponencial com constantes 42/7 dias (CTL/ATL/TSB);
  - `daily_tss_series(events)` — série diária de TSS dos eventos do Intervals
    (`tss`/`icu_training_load`), mesmo critério de carga do reconcile.
- CLI `python3 src/training_plan.py model`: métricas do motor local vs
  Intervals.icu (com diferença) e **projeção** do TSB ao seguir o `plan.json`.
- 14 testes novos (64 no total); docs atualizadas (README pt/en, `docs/ARQUITETURA.md`).

### Documentação (entrou após v0.0.7)

- `docs/ARQUITETURA.md`: conceito original do agente (motor
  Impulse-Response/Banister, schema de estado do atleta, system prompt de
  corrida) sincronizado com o vault do Obsidian, com a tabela de diferenças
  para a implementação atual e notas de design aproveitáveis (rampagem
  +10%, teto de TSB, periodização por fases).
- README pt/en: seções **Documentação** (link para o spec) e **Direções
  futuras** (multi-atleta, modo solo, IA vs biblioteca, deload, corrida).
- `.gitignore` ignora `.env.bak` / `.env.*.bak`.

## [0.0.7] - 2026-09-18

### Adicionado
- `build` e `reconcile` agora imprimem a agenda de treinos em uso
  (`Agenda: seg,ter,qua,qui,sex`) e avisam quando `TRAINING_DAYS` não está
  definido no `.env` (usa o padrão).

## [0.0.6] - 2026-09-18

### Corrigido
- `scripts/daily_reconcile.sh`: `set -e` era desativado dentro do bloco
  `{ ...; } || { ...; }` (contexto condicional) — uma falha no `reconcile`
  não parava o fluxo nem notificava. Cada passo agora roda via `step()`, que
  loga, emite `notify-send` no desktop e sai com código != 0 na primeira falha.

## [0.0.5] - 2026-09-18

### Corrigido
- `_reduce_next_hard` reduz o mesmo limite (ex.: Limiar) no máximo uma vez por
  `reconcile`: o guard `reduced_ids` é compartilhado entre treinos perdidos e
  treinos extras, evitando dupla-redução quando dois eventos caem na mesma
  janela.

## [0.0.4] - 2026-09-18

### Adicionado
- O `reconcile` detecta **treinos extras fora do plano** (eventos com
  `paired_activity_id` e `external_id` não-hermes) na janela dos últimos 7 dias.
  Se a soma da carga chegar a um treino cheio (`>= cap_diario`, via `tss` ou
  fallback `icu_training_load`), o próximo dia de treino vira recuperação e o
  próximo Limiar é reduzido 5%. Trabalho leve não altera o plano.
- Testes cobrindo a detecção de extras e a recuperação inserida.

## [0.0.3] - 2026-09-18

### Adicionado
- Agenda de treinos **configurável** via `TRAINING_DAYS` no `.env`
  (nomes em pt `seg,ter,...` ou en `mon,tue,...`; padrão seg-sex). O foco do
  dia segue a posição na agenda.
- Testes de agenda parcial e mensagens explicativas em ambos os idiomas.

## [0.0.2] - 2026-09-16

### Adicionado
- Arquivo `VERSION` (passa a gerar versões explícitas).
- **Mensagens explicativas** (`cue text` + intervalos flat) publicadas em cada
  treino no Intervals — o aquecimento explica a zona e cada intervalo recebe
  "Agora voce vai entrar em X minutos a Y por cento do seu FTP".
- `CUE_LANG` no `.env` (`pt`|`en`) controla o idioma das mensagens.

## [0.0.1] - 2026-09-15

### Adicionado
- Baseline do projeto (`zwift-coach` → **hermes-coach**): agente opencode
  `cycling-coach`, skill do Hermes, clientes `intervals_client.py`,
  `coach.py` (TSB → foco → carga) e CLI `training_plan.py`
  (`info`/`build`/`reconcile`/`push`/`all`).
- Plano semanal por TSB, orçamento de carga (TSS 7 dias ≤ `cap_diario × 7`),
  upsert por `external_id` (sem duplicar eventos), publicacao no calendário do
  Intervals.icu e README em pt/en.
- CI: GitHub Actions roda `unittest` (Python 3.12) em todo push e PR — 50
  testes, stdlib-only.

---

## Como manter

Ao criar uma nova versão (bump de `VERSION`):

1. Adicione a seção da versão sob **Unreleased**, ou mova o conteúdo de
   `## [Unreleased]` para a nova tag.
2. Crie a **tag** (`git tag v0.0.X`) e a **release** no GitHub
   (`gh release create v0.0.X`).
3. Linke a nova versão na seção de comparações ao final deste arquivo.

## Comparações (links)

- [v0.0.21…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.21...master)
- [v0.0.20…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.20...master)
- [v0.0.19…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.19...master)
- [v0.0.18…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.18...master)
- [v0.0.17…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.17...master)
- [v0.0.9…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.9...master)
- [v0.0.8…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.8...master)
- [v0.0.7…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.7...master)
- [v0.0.2…v0.0.7](https://github.com/valdelin/Hermes-coach/compare/v0.0.2...v0.0.7)
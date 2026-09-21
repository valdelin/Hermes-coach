# Changelog

Todas as mudanças relevantes do **Hermes Coach**. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o versionamento,
[SemVer](https://semver.org/lang/pt-BR/).

As versões aqui correspondem às **tags** do repositório (git tag) e aos
[releases publicados no GitHub](https://github.com/valdelin/Hermes-coach/releases).
As versões intermediárias (v0.0.3–v0.0.6) foram bumpados no `VERSION` sem tag
própria — foram agrupadas na tag/release v0.0.7.

## [Unreleased]

### Adicionado

- **Issue [#6](https://github.com/valdelin/Hermes-coach/issues/6)** — TODO
  registrado: **FTP sugerido a partir de treinos não agendados** (prova/treino
  livre). Desenho na issue: detectar o pedido "extra" no `reconcile`, estimar
  o FTP via melhor média móvel de 20 min do stream de potência (`0.95 ×
  best20`) com gates de qualidade/contexto, e propor (nunca auto-aplicar) a
  atualização de `.env FTP` + `indoor_ftp` no Intervals com confirmação do
  atleta. Backlog (Fase 2) e ROADMAP atualizados.

### Atualizado

- **`docs/ROADMAP.md`** sincronizado: novo item #6 no backlog (FTP sugerido);
  **renumeração** — a casca Runna virou **#7** e multi-atleta **#8**, para a
  coluna `#` acompanhar os números reais das issues do GitHub.

## [0.0.14] - 2026-09-21

### Atualizado

- **`docs/ROADMAP.md`** sincronizado com o estado real (revisão de 21/09):
  registro dos 5 itens em aberto (#1–#3, #6, #7), dos fechados (#4, #5 —
  resta validação com treinador), da Fase 3 parcialmente iniciada no agente
  (onboarding + disponibilidade, v0.0.10–0.0.11) e do roteiro de testes
  (`docs/ROTEIRO-TESTES.md`, execução em 22/09).
- Vault do Obsidian sincronizado: `HISTORICO.md` (entradas 2026-09-20 e
  2026-09-21), `PLANO-NOVAS-IMPLEMENTACOES.md` (status atual 2026-09-21) e
  cópia do `ROTEIRO-TESTES.md`.

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

- [v0.0.9…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.9...master)
- [v0.0.8…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.8...master)
- [v0.0.7…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.7...master)
- [v0.0.2…v0.0.7](https://github.com/valdelin/Hermes-coach/compare/v0.0.2...v0.0.7)
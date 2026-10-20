# Issues conhecidas — Hermes Coach

Lista de bugs conhecidos e pendências técnicas registradas, com rastreio no
GitHub. Formato: cada issue tem status, impacto, mitigação atual e direção de
solução.

**Status do arquivo:** revisado em 20/10/2026. Os dois defeitos locais de
`summary` — `--date` recebido como `str` e `--export` engolido em período sem
treinos — foram **corrigidos em 07/10/2026** e ficam documentados abaixo como
registro de correção (sintomas reais, causa e cobertura). Em 08/10/2026 a nota
defensiva de `lang` inválida em `workout_text`/`event_payload` também foi
**corrigida** (defesa em profundidade). Em 20/10/2026 foram **corrigidos e
publicados** os dois defeitos do dia de teste de FTP (FTP-H8): o evento D0
publicava workout Z2 estruturado (`Ramp Test (FTP)` com 10m 45-75% / 30m 55% /
10m 70-45%) e o `reconcile` substituía o dia do teste por
`Recuperacao (plano ajustado)` quando havia carga extra. Segue aberto o
item #1 (fantasmas do Intervals, bug da plataforma, prioridade baixa e aceita)
e permanecem abertas as pendências residuais P3 do FTP-H8 explicitadas ao final
da seção FTP-H8/P2 — os dois defeitos críticos estão corrigidos, mas o conjunto
FTP-H8 **não** é declarado encerrado enquanto elas existirem.

Pendências de escopo que não são bug estão em `docs/ROADMAP.md` (#58 integração
dos módulos de P0–P3 ao `build`/`push`, #59 quatro limites de implementação) e
em `docs/EMBASAMENTO-CIENTIFICO.md` §14.

---

## #1 — Intervals cria atividade MANUAL "fantasma" a partir do evento planejado

**GitHub:** [valdelin/Hermes-coach#1](https://github.com/valdelin/Hermes-coach/issues/1)
**Status:** aberto (aceito; não bloqueia o fluxo) · **Severidade:** cosmética/baixa
· **Prioridade:** baixa (`priority: low`, decisão 2026-09-21 — cosmético, comportamento
do Intervals, não do agente)

### Sintoma

Ao sincronizar a atividade real (ex.: Zwift) e pareá-la com um evento
`hermes-plan-YYYY-MM-DD`, o Intervals também materializa **o próprio evento
como uma atividade** no feed:

- `source: MANUAL`, `fit_file: null`, sem `external_id`/`event_id`/`paired_event_id`;
- `start_date_local` = horário agendado do evento (`START_TIME = "07:30:00"` em `src/plan.py`);
- duração e load = valores **planejados** (não os reais).

### Impacto

- Entrada duplicada ("fantasma") no feed de atividades do dia.
- Se a atividade real for **maior** que o planejado (mais TSS/duração), a
  fantasma mantém valores planejados → o dia pode parecer mais carregado que o
  real em painéis de `icu_training_load` (dupla contagem **cosmética**).
- **Não** afeta CTL/ATL/TSB (a fantasma tem `tss: null`) nem o `reconcile`
  (a fantasma não tem `paired_event_id` → invisível para `_done_and_extra`).

### Mitigação atual

1. No app do Intervals, arrastar a entrada do treino sobre a atividade real
   **pareia** atividade ↔ evento (não há merge na API);
2. Apagar a fantasma no app ou via `DELETE /api/v1/activity/{id}` — seguro,
   pois é um registro órfão.

### Não é específico do Hermes — limitação do Intervals

- O gatilho do fantasma é o **pareamento de qualquer evento planejado** com uma
  atividade real — não depende de quem criou o evento (API do Hermes, planner do
  Zwift, biblioteca de treinos, outro app). Prova no fórum do Intervals: coaches
  relatam treino planejado concluído "logging separately and creating a new
  workout", e há feature request aberto (2026-08) para remover o bloco "Workout"
  duplicado em atividades concluídas.
- Observado em 2026-09-25: treinos agendados no **planner do Zwift** (ex.:
  "Tempo 2026-09-29 (rescheduled)", "SweetSpot 2026-09-30", "Endurance
  2026-10-02") chegam ao calendário com `workout_doc` e **sem `external_id`** → 
  ficam fora do escopo do `reconcile`/`push` (não são `hermes-plan` nem órfãos);
  se executados e pareados, espera-se o **mesmo fantasma**.
- **Implicação para a limpeza futura:** detectar fantasmas por **conteúdo**
  (`source: MANUAL`, sem `fit_file`, duração ≈ planejada), não pela origem do
  evento — cobre eventos de qualquer criador.

### Reconhecimento por `external_id` (o que conta como "extra")

O `reconcile` marca "concluído" pelo `external_id` **começando com
`hermes-plan`** (`_done_and_extra`, `orphan_external_ids`); hoje o plano é 1
treino/dia (bike), então basta. A classificação de **"treino extra fora do
plano"** vale para **qualquer evento pareado cujo `external_id` não comece com
`hermes-plan`** — o código não olha esporte nem "mesmo dia":

- corrida planejada num dia de **brick** (bike + run — triatleta);
- corrida **sozinha** num dia só de corrida (#18);
- natação (futuro módulo swim);
- treino do planner do Zwift executado e pareado (§13 do
  `SYNC-PLATAFORMAS.md`).

**O que NÃO conta como extra:** um **ride solto sem evento planejado** (ex.:
pedal outdoor no Garmin sem agenda, ou segundo pedal do dia apenas gravado)
não entra em `_done_and_extra` — a função só itera eventos de calendário com
`paired_activity_id` (nunca lê `activity_id`); atividade não pareada cai no
`if not paired: continue` e é **invisível** ao reconcile. Seu único efeito no
hermes é subir o `avg_load` (via `icu_training_load`), elevando levemente o
cap/budget (×0.95) — **nunca** gera recuperação/Limiar. A natureza do esforço
(com/sem potência, horário, indoor/outdoor) **não é lida**; só a magnitude do
`load` importa para comparar com o cap na janela.

O gatilho **não é por treino individual**, e sim por **acúmulo na janela de 7
dias**: `_adjust_for_extra_workouts` soma a carga dos extras e só age se
`soma >= cap`, com `cap = max(35, min(200, avg_load * 0.95))`. Com `avg_load`
baixo (ex.: 40 → cap ≈ 38 TSS), **uma única corrida de brick de ~45 TSS já
estoura** e injeta recuperação + Limiar −5%; com `avg_load` alto (ex.: 60 →
cap 57), o mesmo treino não muda nada.

Ajuste futuro (#18, multi-esporte): o reconcile precisa conhecer **o que o
hermes planejou** — unificar bike/run/swim no mesmo `plan.json` (cada treino
com seu prefixo ou marcado por `sport`) e fazer `_done_and_extra`/
`orphan_external_ids` reconhecerem o **conjunto de prefixos hermes**; o "extra"
fica restrito a eventos planejados por outras fontes (planner do Zwift,
manuais) executados e pareados — rides soltos continuam invisíveis (não são
eventos).

Conflito de `external_id` no mesmo dia:
- bike + bike: não ocorre hoje (1/dia); se ocorresse, os dois eventos
  **colidiriam** em `hermes-plan-<dia>` no upsert (os prefixos precisariam de
  sufixo).

### Restrição de API

Não existe endpoint de **merge** de atividades na API pública do Intervals
(apenas GET/PUT/DELETE `/activity/{id}`, upload e criação manual).

### Direção de solução (futura)

Etapa de **limpeza de fantasmas** no fluxo `reconcile`/`push` (ou no
`scripts/daily_reconcile.sh`):

1. Detectar atividades `MANUAL` sem `fit_file` e sem vínculo, cujo **nome
   coincide com evento `hermes-plan*`** e **duração = duração planejada**;
2. Confirmar que a atividade real pareada existe;
3. Excluir via `DELETE /api/v1/activity/{id}`;
4. `--dry-run` antes de excluir + testes (regra do projeto:
   `python3 -m unittest discover -s tests -v`).

### Registro

- 2026-09-18: verificado com dados reais — evento `137086170`
  (`hermes-plan-2026-09-18`) pareado com `i188054492` (Zwift, UPLOAD, load 18)
  e fantasma `i188054507` (Ride 07:30, MANUAL, load 23, 2400s).
- 2026-09-18: registrado como issue #1 no GitHub.
- 2026-09-21: **prioridade reduzida** pelo atleta — é cosmético e é bug do
  Intervals, não do agente; label `priority: low`; deixa de ser o primeiro item
  da sessão de testes de 22/09 (segue como melhoria de qualidade de dados,
  podendo entrar junto da Fase 1/notificações ou quando houver folga).

---

## FTP-H8 — o dia do teste de FTP publicava workout Z2 estruturado

**Status:** **corrigido e publicado** (2026-10-20, `58374d8` em `master`) ·
**Severidade:** alta (prescrição errada no dia do teste) · **Escopo:** plano,
payload do Intervals, texto de cue · **Encontrado em:** 2026-10-20, auditoria do
evento real de 22/10/2026

### Sintoma

O dia D0 (`FTP_TEST_DATE`) era publicado no Intervals como
`2026-10-22 - Ramp Test (FTP)`, com a descrição/workout estruturado de uma
sessão Z2 contínua:

- passos `10m 45-75%` (aquecimento), `30m 55%` (bloco) e `10m 70-45%`
  (desaquecimento) — o app (Zwift) executava recovery no dia do teste;
- texto "Mesma carga do ultimo treino de Zona 2";
- `planned_duration` 3000 s e TSS 15.0: carga prescrita que não existe.

### Causa

`_prep_workout(kind="d0")` montava um `PlannedWorkout` com `focus=zone2`,
`on_sec=1800`, `on_power=0.55` e o nome "Ramp Test (FTP)": não havia protocolo
de teste, apenas um rótulo sobre um workout Z2. A descrição vinha do builder
genérico (`_warmup_msg`/`_structure_msg`/`_progress_msg`) e o Intervals deriva o
workout estruturado da própria `description` (linhas `- texto duração %`); o
payload do Hermes não tem campo `steps`.

### Impacto

- Gráfico e passos errados no dia do teste; sessão leve executada como se fosse
  o teste de FTP.
- O título prometia um protocolo (`Ramp Test`) que o Hermes não implementa.

### Correção (implementada)

- D0 passa a ser **evento informativo**: nome `"<dia> - FTP Test"`,
  `planned_duration=0`, `tss=0.0`, `params` zerados e descrição instrucional
  (método/plataforma à escolha do atleta; sem passos, sem `%FTP`, sem Zona 2).
- Marcador estrutural aditivo
  `ftp_test_intent="EXTERNAL_OR_USER_SELECTED_TEST"` persistido no `plan.json`
  e consumido por `event_payload`/`workout_text`/`rebuild_workout`. A decisão é
  **estrutural** — nunca por título. Modo implementado:
  `EXTERNAL_OR_USER_SELECTED_TEST`; não existe protocolo prescritivo do Hermes.
- `FTP_TEST_KEYWORDS` endurecido para expressões específicas (`ftp test`,
  `ftp retest`, `ftp teste`, `teste de ftp`, `teste ftp`, `ramp test`); a
  heurística textual fica restrita a detecção histórica/sugestão de reteste.
- Nenhuma escrita em `ftp_history.json`/`ftp_evidence.json`; FTP canônico e
  `FtpEvidence` intocados; `DEFAULT_FTP` não constrói alvo para o D0.

### Cobertura de regressão

- `tests/test_ftp_test_event.py` (15 testes): payload **final** via
  `FakeProvider` sem passos, persistência do marcador em
  `save_plan`/`load_plan`/`enrich`, ausência de escrita de arquivos de FTP,
  keywords sem falso positivo amplo ("FTP Builder", "Prova", "Pré-FTP").
- Invariância provada na auditoria: plano **sem** `ftp_test_date` idêntico byte
  a byte ao parent; D-2/D-1 inalterados; D+1 continua estruturado.
- Suíte: 1796 testes, 0 falhas, 0 erros, 1 skip (delta +15 vs baseline).

### Operação — evento já publicado não é corrigido pelo código

O código novo **não** corrige um evento já publicado a partir de plano legado
(sem marcador): esse plano continua gerando o Z2 falso. O evento real
`137152273` (`hermes-plan-2026-10-22`) foi corrigido por upsert em 2026-10-20:
nome `FTP Test`, `workout_doc.steps=[]` (sem gráfico), sem duração e sem carga,
descrição instrucional. O `plan.json` local foi ajustado **apenas** nessa
entrada (backup do estado anterior guardado fora do repo).

Observação de contrato: `planned_duration` no payload não é honrado pela API do
Intervals — a duração do evento vem do parsing da descrição. Sem passos, o
evento fica sem duração, que é o comportamento desejado para o D0.

### Registro

- 2026-10-20: causa raiz confirmada por execução do código do parent (nome,
  focus, 3000 s, TSS 15.0, três passos e a frase "Mesma carga do ultimo treino
  de Zona 2"); publicação `58374d8` (CI run `39491323217`, verde); correção
  operacional do evento de 22/10 no mesmo dia.

---

## FTP-H8/P2 — `reconcile` substituía o dia do teste de FTP por recuperação

**Status:** **corrigido e publicado** (2026-10-20, `9a82c99` em `master`) ·
**Severidade:** alta (o teste desaparecia do calendário sem aviso) ·
**Escopo:** `reconcile`/`push` · **Encontrado em:** 2026-10-20, auditoria do
FTP-H8 (P2 promovido no gate de publicação)

### Sintoma

Com carga extra fora do plano ≥ cap diário na janela de 7 dias,
`_adjust_for_extra_workouts` inseria `Recuperacao (plano ajustado)` no **próximo
dia de treino**. Quando esse dia era o teste de FTP, o evento de teste era
substituído, o marcador `ftp_test_intent` era perdido e o fluxo `all`
(build → reconcile → push) publicava a recuperação no lugar do teste. O CLI não
listava a mudança (só imprime o plano com `--show`) e podia terminar com
`Nenhum treino perdido; plano mantido.`

### Causa

`_insert_recovery` fazia `[w for w in plan if w["day"] != next_day] +
[recovery]` sem olhar o que havia no dia; `_adjust_for_extra_workouts` escolhia
o alvo apenas por dia de treino, sem considerar a intenção de teste.

### Impacto

- Teste de FTP cancelado silenciosamente: o atleta via
  "Recuperacao (plano ajustado)" no dia e nenhum aviso do teste perdido.
- Defeito **pré-existente** ao FTP-H8 (o parent também substituía o
  `Ramp Test (FTP)`), mas incompatível com o contrato do D0.

### Correção (implementada)

- `_adjust_for_extra_workouts` desvia a recuperação para o próximo dia de
  treino **livre** quando o alvo carrega `ftp_test_intent`; o teste permanece
  intacto.
- `_insert_recovery` ganhou guarda defensiva: nunca sobrescreve um dia marcado.
- O desvio é **anunciado**: `info["ftp_test_preserved"]` e
  `info["recovery_day"]` alimentam `_ftp_test_reconcile_hint()` em
  `cmd_reconcile`.
- Sem marcador, o comportamento é idêntico ao anterior (autoridade estrutural,
  não o título).
- A absorção de treino perdido já não injeta volume no D0 (`on_sec<=0`).

### Cobertura de regressão

- `tests/test_ftp_test_event.py` → `FtpTestReconcileProtectionTest` (5 testes):
  carga extra não substitui o dia do teste; recuperação vai para o próximo dia
  livre; guarda de `_insert_recovery`; sem marcador reage como antes;
  `reconcile` preserva o marcador e anuncia o desvio.
- `tests/test_training_plan.py` → `FtpTestReconcileHintTest` (2 testes).
- Suíte: 1803 testes, 0 falhas, 0 erros, 1 skip (delta +7).

### P3 corrigida — comparação de volume do mesmo foco

**Corrigido** (2026-10-20, commit local `8c2c15f`, aguardando publicação).
`_prev_same_focus` escolhia o treino anterior apenas por `focus` e `day`. O D0
tem `focus=zone2` (dia fácil de propósito) com `params` zerados, então o D+1
publicava "30 minutos a mais que o ultimo treino de Zona 2" — uma comparação de
volume contra um teste que não prescreve bloco nenhum.

Correção: a função ignora sessões com `ftp_test_intent` (autoridade
estrutural — nunca por título ou descrição) e também entradas sem volume
prescrito (`on_sec<=0`), o que cobre plano legado construído antes do marcador
existir. A comparação entre dois Z2 legítimos permanece idêntica.

Cobertura: `FtpTestPreviousFocusTest` (5 testes) e um teste de integração via
`push_workouts` com o filtro real, verificando que o marcador chega intacto ao
ponto de filtragem; suíte com 1809 testes. Os cinco testes novos falham no
código anterior e passam com a correção.

### Pendências residuais (P3, abertas — não bloqueiam)

- `ftp_watts` snapshot permanece no D0 — inerte (nenhum caminho gera steps).
- Keywords ainda casam por substring "Preparacao para FTP Test"/"Pos FTP Test"
  (afeta só a sugestão de reteste); e
  `test_nenhum_protocolo_e_inferido_do_texto` é asserção fraca.
- `structure_read_only`/`workout_doc` de eventos antigos: ao trocar a descrição
  por upsert, `moving_time`/`icu_training_load` herdados precisam ser zerados
  explicitamente no payload; sem isso o evento informativo mantém a carga
  antiga (27/10 → 0 no evento real).

### Registro

- 2026-10-20: reproduzido com o código real (teste em 21/10 + 200 TSS em 20/10
  → o dia virava `Recuperacao (plano ajustado)`, marcador `None`); correção
  publicada em `9a82c99` (CI run `39495983667`, verde).

---

## `summary --date` recebia a âncora como `str` e quebrava o cálculo da janela

**Status:** **corrigido** (2026-10-07) · **Severidade:** baixa · **Escopo:** CLI local.

### Sintoma

`python3 src/training_plan.py summary --date YYYY-MM-DD` entregava a âncora
como `str` para um core que espera `date`. O ponto de falha dependia do
`--period`, e os três caminhos vêm da mesma causa:

| `--period` | Exceção | Origem |
|---|---|---|
| `day` | `AttributeError: 'str' object has no attribute 'isoformat'` | `activity_summary.done_activities()` (`start.isoformat()`) |
| `week`, `month`, `quarter`, `semester`, `year` | `TypeError: unsupported operand type(s) for -: 'str' and 'datetime.timedelta'` | `activity_summary.period_range()` (`anchor - timedelta`) |
| `45d`, `6m`, `1y` (duração livre) | `TypeError` de mesmo tipo | `activity_summary.resolve_period()` (`anchor - timedelta`) |

A versão anterior deste registro apontava apenas o terceiro caminho e atribuía a
falha a `period_range()` — descrição imprecisa, corrigida aqui.

### Causa

`args.date` era o único parâmetro do `summary` aceito como `str` **ou** `date`:
sem `--date`, `cmd_summary()` montava o default `date.today() - timedelta(days=1)`
(já `date`); com `--date`, o argparse entregava a string crua. A **mistura de
tipos** é o defeito — não o parsing em si. `--start`/`--end` não têm esse
problema: são `str` do fim ao fim e viram `date` uma única vez, dentro de
`resolve_period()`.

### Correção (implementada)

- `--date` ganhou `type=_iso_date` no parser. `_iso_date()` converte com
  `date.fromisoformat` **na borda do argparse** e devolve
  `argparse.ArgumentTypeError` (`use YYYY-MM-DD`) quando a entrada é inválida,
  para o argparse reportar erro de uso com exit 2 em vez de o core estourar
  `AttributeError`/`TypeError`. O core só vê `datetime.date`.
- Não houve mudança de semântica de período, nem de default D-1, nem de
  `resolve_period()`.

### Cobertura de regressão

`tests/test_training_plan.py` → `SummaryVazioEDateTest`: `--date` para `day`,
`week` (âncora −6d), `month` (−29d) e `45d` (−44d); default D-1 sem `--date`;
`--date 2026-13-99` → exit 2 com mensagem de uso. Verificado red→green por
mutação de cada um dos dois defeitos desta issue.

### Registro

- 2026-10-07: sintomas reais levantados por execução da CLI (três caminhos da
  tabela acima); correção na borda do argparse; suíte verde.

---

## `summary --export` não gerava arquivo num período sem treinos

**Status:** **corrigido** (2026-10-07) · **Severidade:** média · **Escopo:** CLI local.

### Sintoma

`summary --period ... --export relatorio.html` num período com **zero**
atividades pareadas encerrava com exit 0, **sem criar o arquivo** e **sem
aviso algum**. Um relatório de um dia sem treino simplesmente não aparecia —
falha silenciosa no comando cujo propósito é produzir aquele arquivo.

### Causa

`cmd_summary()` imprimia `Nenhum treino feito no periodo.` e executava
`return agg` **antes** de `_summary_charts()`/`_summary_export()`. O renderer,
em si, já trata a lista vazia: `_hero_title()` vira "Nenhum treino no periodo",
`_stats_cards()` degrada potência/FC/elevação para "—",
`charts.weekly_load([])` devolve `[]` e `summarize([])` não emite
`avg_power`/`np`/`avg_hr`. Nada impedia a geração — só o retorno antecipado.

### Correção (implementada)

- O `return agg` cedo saiu de `cmd_summary()`: o console mantém a mesma linha
  `Nenhum treino feito no periodo.` (comportamento humano inalterado) e
  `_summary_export()` passa a rodar **sempre** que `--export` for pedido.
  Gráficos do terminal no caso vazio seguem fora, como antes.
- `render_summary_html()` ganhou estado vazio explícito em "Treinos feitos":
  `Nenhum treino foi realizado neste período.` no lugar de `<tbody></tbody>`.

### Cobertura de regressão

`tests/test_training_plan.py` → `SummaryVazioEDateTest`: (1) arquivo criado em
período vazio com a nota de estado vazio e sem `<tbody></tbody>`; (2) relatório
vazio contendo a sessão **planejada** e a leitura de **prontidão**; (3)
relatório vazio sem plano e sem readiness, HTML válido.

### Registro

- 2026-10-07: reproduzido por execução da CLI; correção + três regressões;
  suíte verde.

---

## `IntegracaoCliTest::test_saida_avisa_quando_a_leitura_nao_foi_aplicada` era date-fragile

**Backlog:** `TEST-1` (P3) · **Status:** **corrigido** (2026-10-05) — dívida de
teste, nunca bug de produção · **Severidade:** nenhuma em produção — o código
estava correto

### Sintoma

O teste criava registros de wellness de ontem até **amanhã** e esperava que o
CLI rejeitasse a leitura ("leitura de ontem, nada é adaptado"). Na prática a
decisão aplicava-se ao primeiro dia do plano (amanhã) e a saída saía
`efeito: aplicada em <amanhã>`, quebrando a asserção.

### Causa

Premissa do fixture contradita pelos próprios dados: com wellness até D+1, o
`reference_day` da avaliação (`ReadinessTrace.reference_day` = último registro)
era D+1, que coincide com o primeiro dia do plano. Não era regressão — o teste
já falhava no commit `931fe16`, antes de UI-1.

### Correção (implementada)

Somente o fixture do teste: a janela de wellness agora **termina em D-1**
(`ontem - timedelta(days=2 - i)`, três registros para a avaliação ter janela),
casando a premissa com os dados. `_readiness_applies_on` e
`_readiness_situacao` já tratavam o caso corretamente — `dia_alvo_fora_do_plano`
produz `nao aplicada — leitura e de um dia fora do plano; nao foi transferida
para outra sessao`, exatamente o que o teste afirma. Nenhum arquivo de `src/`
mudou: sem seam novo, sem `--today`, sem clock abstrato, sem alteração de
thresholds, ação, policy ou saída de CLI.

A correção é estrutural, não dependente do dia: D-1 nunca pertence ao plano,
que começa em D+1 com a sessão de hoje preservada verbatim. Verificado freezing
`date.today()` em 75 dias consecutivos (cobre virada de mês, fim de semana e
segunda-feira como D+1): `nao aplicada` e `nao foi transferida` presentes,
`aplicada em` ausente em todos.

### Registro

- 2026-10-04 — registrado durante PMC-1; falha pré-existente mantida
  deliberadamente (não corrigida incidentalmente).
- 2026-10-05 — TEST-1 corrigido (fixture), suíte verde.

---

## Build — preservar o treino de hoje descarta WEEKLY_HOURS/LONG_DAY

**GitHub:** valdelin/Hermes-coach#7
**Status:** **corrigido e publicado** (implementado 2026-09-22, entregue em
v0.0.15) · **Severidade:** funcional (configuração ignorada silenciosamente)
· **Encontrado em:** 2026-09-22 (roteiro de testes, S5)

### Sintoma

Quando o `plan.json` já contém um treino para **hoje** (caso normal: o `build`
é regerado em dia de treino), o scaling de disponibilidade **não é aplicado**:
com `WEEKLY_HOURS=2` a linha `Disponibilidade: 2h/semana` é impressa, mas as
durações ficam idênticas ao plano sem `WEEKLY_HOURS`. O mesmo vale para
`LONG_DAY` (o ciclo não é rotacionado). Com `plan.json` sem treino de hoje, o
scaling funciona normalmente (validado: durações reduzidas, mínimo 150s).

### Causa

`src/plan.py::build_plan` (linhas 368-376): o caminho que **preserva o treino
de hoje** chama `build_plan` recursivamente **sem repassar `weekly_hours` e
`long_day`**:

```python
return plan + build_plan(events, tsb, ftp=ftp, days=days,
                         start=start, training_days=training_days,
                         goal=goal, race_date=race_date,
                         ftp_test_date=ftp_test_date)
                         # faltam: weekly_hours=..., long_day=...
```

### Impacto

- Usuário configura `WEEKLY_HOURS`/`LONG_DAY` no onboarding e o `build` diário
  (sempre com treino de hoje existente) **ignora** a configuração sem aviso —
  a linha `Disponibilidade` dá a falsa impressão de que o ajuste foi aplicado.
- Funcional (não crasha), mas anula o valor da feature de disponibilidade
  (v0.0.11) no fluxo real de uso.

### Direção de solução

Repassar `weekly_hours=weekly_hours, long_day=long_day` na chamada recursiva
(e manter o treino de hoje fora do scaling — ele já existe e não deve ser
mudado). Testes: cenário `WEEKLY_HOURS=2` **com** plano contendo hoje (regressão).

### Correção (implementada)

`build_plan` repassa `weekly_hours=weekly_hours, long_day=long_day` na chamada
recursiva do caminho de preservação do treino de hoje. O treino de hoje
preservado **não** é escalado (fica exatamente como estava). Testes de
regressão: `PreserveTodayWithAvailabilityTest` em `tests/test_availability.py`
(WEEKLY_HOURS e LONG_DAY com plano contendo hoje). Validado também no fluxo
real: com `plan.json` contendo 22/09, `WEEKLY_HOURS=2` → futuros escalados
(241 vs 373 TSS) e hoje preservado (on_sec 360).

### Nota operacional (2026-09-22)

Durante a sessão de testes, `rm -f plan.json` + `build` (que começa em
**amanhã**, `start = today + 1`) gerou planos **sem o treino de hoje**; a
execução do `scripts/daily_reconcile.sh` (S10) fez `push --start $(date +%F)`
= `--start 2026-09-22` e a limpeza de órfãos **apagou o evento de hoje** do
calendário (`Orfaos removidos (HTTP 200): 1`). Restaurado manualmente via
upsert do payload original (`id 138109180`, `hermes-plan-2026-09-22`) e o
`plan.json` re-inseriu o dia.

Prevenção (relacionada ao bug acima): o caminho de **preservar o treino de
hoje** no `build` é o que protege o evento — nunca regenerar o plano a partir
do zero em produção sem incluir hoje antes do `push`; o `push --start hoje`
trata qualquer dia ausente do plano como órfão por design.

### Registro

- 2026-09-22: encontrado na S5 do `docs/ROTEIRO-TESTES.md`; causa raiz
  identificada; issue aberta no GitHub (#7).

---

## `reconcile` grava `plan.json` sem a meta (goal/race_date/ftp_test_date)

**GitHub:** valdelin/Hermes-coach#8
**Status:** **corrigido e publicado** (implementado 2026-09-22, entregue em
v0.0.15) · **Severidade:** baixa hoje (auditável; baixo impacto) —
**vai ficar funcional com a #6** (`ftp_candidates` vive na meta) · **Encontrado em:** 2026-09-22 (roteiro de testes, S2/S6)

### Sintoma

O `build` salva `plan.json` no formato novo `{'goal', 'race_date',
'ftp_test_date', 'workouts'}`. O `reconcile` em seguida regrava o mesmo arquivo
**como lista pura** e a meta é perdida (`load_plan_meta` → todos `None`).

### Causa

`src/training_plan.py::cmd_reconcile` (linha 317) chama
`save_plan(plan, PLAN_FILE)` **sem os argumentos de meta** — `save_plan` só
gera o formato dict quando `goal is not None`.

### Impacto

- Hoje: baixo — `load_plan_meta` só é importado, não consumido (GOAL/RACE_DATE
  vêm do `.env` em cada comando).
- **Com a #6:** os `ftp_candidates` serão gravados na meta e o `reconcile`
  (rodado todo dia no timer) os apagaria todo dia. Tratar antes do #6.

### Direção de solução

`cmd_reconcile` carrega a meta (`load_plan_meta`) e a regrava junto
(`save_plan(plan, PLAN_FILE, **meta)`). Teste: build → reconcile → meta igual.

### Correção (implementada)

`cmd_reconcile` carrega a meta (`load_plan_meta(PLAN_FILE)`) e a regrava junto
(`save_plan(plan, PLAN_FILE, goal=..., race_date=..., ftp_test_date=...)`).
Sem GOAL (formato antigo), continua lista pura — compatível. Testes:
`ReconcileMetaTest` em `tests/test_training_plan.py` (build → reconcile → meta
preservada; formato antigo continua lista). Validado no fluxo real: build →
reconcile → meta `{'goal': 'ftp-builder', 'race_date': None,
'ftp_test_date': '2026-10-22'}` intacta.

### Registro

- 2026-09-22: encontrado na S2/S6 do `docs/ROTEIRO-TESTES.md`; issue aberta no
  GitHub (#8).

---

## #6 — FTP sugerido a partir de treinos fora do plano

**GitHub:** [valdelin/Hermes-coach#6](https://github.com/valdelin/Hermes-coach/issues/6)
**Status:** **implementado e publicado** (2026-09-22, entregue em v0.0.15) ·
**Severidade:** feature (estimativa assistida de FTP)

### Descrição

Quando o atleta pedala **fora do plano** (ex.: um Zwift race, um pedal solto ou
um treino que ele mesmo montou), o pedal carrega informação de fitness que o
Ramp Test obrigaria a parar a semana para obter. O `ftp-scan` examina esses
treinos e propõe um novo FTP, seguindo regras conservadoras:

- **Candidatos**: eventos pareados (`paired_activity_id`) com `external_id`
  não-hermes; filtros baratos no detalhe (não-MANUAL, duração ≥ 45 min, com
  potência, intensidade média ≥ 75% do FTP) antes de baixar o stream;
- **Estimativa** (`src/ftp_estimation.py`): melhor média móvel de 20 min × 0.95
  (= `proposed_ftp`), com gates de qualidade (CV ≤ 15%, mínimo da janela ≥ 80%
  da média, limpeza de picos espúrios);
- **Somente para cima**: `proposed_ftp` precisa estar entre **+3% e +30%** do
  FTP atual (`MIN_NEW_FTP_RATIO`/`MAX_NEW_FTP_RATIO`) — esforço fraco não vira
  "FTP menor" (fadiga derruba potência) e salto > 30% é tratado como anomalia;
- **Confirmação obrigatória**: o `ftp-scan` lista os candidatos validados e
  pergunta antes de aplicar (nunca altera `.env`/Intervals sozinho);
- **Aplicação**: `.env FTP` + backup `.env.bak` + `PUT /athlete/{id}/
  sport-settings/{ride_id}` com `indoor_ftp` novo (mesmo padrão do alinhamento
  210 → 182W em 19/09/2026: payload sem `created`/`updated`);
- **Registro na meta**: candidatos ficam em `plan.json` → `ftp_candidates`
  (chave = `activity_id`, com `applied`); `build`/`reconcile` **preservam** a
  meta (o #8 garantiu isso); `info`/`ftp-check` avisam quando há pendência.

### Uso

```
python3 src/training_plan.py ftp-scan [--days 45]
```

### Validação

- Suíte: 165 testes OK (novos em `tests/test_ftp_scan.py` +
  `tests/test_training_plan.py` — E2E com client fake, sem rede).
- Dados reais (2026-09-22, janela 45d): 8 treinos fora do plano detectados,
  **todos filtrados** no gate de intensidade (pedais leves de agosto/setembro:
  101–131W < 75% do FTP 182W) — nenhum candidato a aplicar; `plan.json`
  inalterado.

### Registro

- 2026-09-22: implementação da integração (client: activity/streams/
  sport-settings + detecção + CLI + meta); sondagem da API real confirmou o
  formato dos streams (`GET /activity/{id}/streams.json?types=watts,time` →
  lista `{type, data}`) e da entrada Ride das sport-settings (id 31898,
  `indoor_ftp`).

---

## Nota defensiva: `workout_text`/`event_payload` com `lang` inválida

**Status:** **corrigido** (2026-10-08) · **Severidade:** defensiva — **não
alcançável pela CLI** · **Encontrado em:** 2026-09-22 (S7)

`event_payload(..., lang="zz")`/`workout_text(..., lang="zz")` levantava
`KeyError: 'zz'` em `FOCUS_ZONE_HINT[focus][lang]`. Na CLI isso não acontecia:
`cmd_push` usa `get_cue_lang()`, que normaliza para `pt` com aviso. Risco
apenas se um futuro código chamasse as funções de texto com `CUE_LANG` cru.

### Correção (implementada)

Defesa em profundidade dentro de `src/plan.py`: `_normalize_lang()` devolve
`lang` quando ela pertence a `CUE_LANGS`, senão `"pt"`; `event_payload` e
`workout_text` normalizam **na entrada** (antes do branch `hr_mode`) — nenhum
chamador externo consegue mais acertar `FOCUS_ZONE_HINT`/`FOCUS_HR_HINT` com
idioma fora da lista. Comportamento da CLI inalterado.

### Cobertura de regressão

`tests/test_plan.py` → `WorkoutTextLangDefenseTest`: `lang="zz"` na descrição
POWER (cai para `pt`), no modo FC (`hr_mode` + `fthr`) e `lang="en"` continua
sendo usada.

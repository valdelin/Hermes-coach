# Roadmap — próximas implementações

Plano consolidado das próximas implementações do Hermes Coach. Cada item tem
rastreio no GitHub (issue) e estágio. Fonte canônica: vault do Obsidian
(`01-Projetos/hermes-coach/PLANO-NOVAS-IMPLEMENTACOES.md`); este arquivo é o
espelho público.

Referências: [ADR-003](https://github.com/valdelin/Hermes-coach/issues) (visão
de produto: "Runna do ciclismo indoor" — ver `docs/ARQUITETURA.md` e vault).

## Backlog

| # | Tipo | Item | Issue | Fase |
|---|---|---|---|---|
| 1 | bug | Limpeza de "fantasmas" (atividades MANUAL criadas pelo Intervals ao parear treino) — **prioridade baixa** (cosmético, bug do Intervals, não do agente) | [#1](https://github.com/valdelin/Hermes-coach/issues/1) | 0 |
| 2 | feature | Notificações de treino (Telegram → e-mail/WhatsApp) | [#2](https://github.com/valdelin/Hermes-coach/issues/2) | 1 |
| 3 | feature | Treinos sem medidor de potência (outdoor/FC: FTHR, hrTSS, %FTHR/RPE) | [#3](https://github.com/valdelin/Hermes-coach/issues/3) | 2 |
| 4 | feature | ~~Ativar sync de wellness~~ **implementado e issue fechada** (RHR/sono no `info`; HRV sem suporte no FR935) | [#4](https://github.com/valdelin/Hermes-coach/issues/4) | 0 ✅ |
| 5 | feature | ~~Tipos de plano de treino (`GOAL`)~~ **implementado e issue fechada** (v0.0.9) — 7 tipos + `RACE_DATE`/tapper + variedade | [#5](https://github.com/valdelin/Hermes-coach/issues/5) | 2 ✅ |
| 6 | feature | ~~FTP sugerido a partir de treinos não agendados~~ (prova/treino livre) **implementado e issue fechada** (v0.0.15, `ftp-scan`: best-20min × 0,95 com gates + confirmação) | [#6](https://github.com/valdelin/Hermes-coach/issues/6) | 2 ✅ |
| 7 | produto | Casca estilo Runna: PWA + onboarding por objetivo + assinatura | — | 3 |
| 8 | produto | Multi-atleta / modo treinador (dashboard por atleta) | — | 4 |

## Fases

### Fase 0 — Higiene de dados (issues #1 e #4)
- Limpeza de fantasmas no fluxo `reconcile`/`push` (ou `daily_reconcile.sh`):
  detectar atividade `MANUAL` órfã com nome de evento `hermes-plan*` e duração
  = planejada; confirmar atividade real pareada; excluir via
  `DELETE /api/v1/activity/{id}`.
- Regras: `--dry-run` antes de excluir; testes obrigatórios.
- **Wellness (issue #4) — ✅ implementado**: o Garmin Connect → Intervals já
  entrega RHR/sono reais (dados confirmados na conta, 2026-09-19); o `info`
  exibe `Wellness:` (RHR atual/média 7d, sono, passos, HRV quando existir);
  HRV Status overnight não suportado pelo FR935 (Elevate Gen 3+) — decisão
  documentada; Oura/WHOOP/novo relógio fica no backlog.

### Fase 1 — Comunicação (issue #2)
- Resumo do treino (foco + TSB + TSS previsto/real + avisos do reconcile) via
  **Telegram** primeiro; interface `Notifier` extensível (e-mail/WhatsApp);
  config `NOTIFY_CHANNEL`/token/chat id no `.env`.
- Regra: envio **assíncrono e não-bloqueante** (não derruba o timer diário).

### Fase 2 — Dados incompletos (issue #3) + tipos de plano (#5) + FTP sugerido (#6)
- ✅ **Sem medidor de potência (issue #3) — implementado (próxima release)**:
  `FTHR` no `.env` (`parse_fthr`/`get_fthr`); `build --no-power` carimba
  `hr_mode` nos workouts e o `push` envia `target: HEART_RATE` com texto em
  **%FTHR + RPE** (`FOCUS_HR_PCT`/`FOCUS_RPE`/`FOCUS_HR_HINT`); reconcile
  preserva o modo FC ao reescrever treinos (recuperação/limiar); `info`/
  `reconcile` avisam "sem potência — carga por FC (icu_training_load)".
  Carga real da atividade continua via `average_heartrate`/`has_heartrate` →
  `hr_load`/`icu_training_load` do Intervals (lthr 182 já configurado).
  Futuro: `fthr-scan` análogo ao `ftp-scan`.
- 📊 **Benchmark (2026-09-22) — Pillar, Xert, TriDot, RunDot**: referências
  de treinos sem potência/outdoor/FC registradas como comentários na issue #3.
  Consenso: (1) **carga por FC sem watts é padrão de mercado** (Pillar
  "indoor ou outdoor"; Xert HRDM — FC+cadência → XSS; TriDot "power meter
  great, but not required") ⇒ nosso plano FTHR + `hrTSS`/`icu_training_load`
  está alinhado; (2) **execução medida contra a prescrição** (Xert smart
  intervals, TriDot TrainX 1-100, Pillar "interval detection") ⇒ com `FTHR`
  dá para verificar zona de FC alcançada em vez de só "não verificado";
  (3) **ambiente importa no outdoor** (TriDot EnviroNorm: calor/altitude
  elevam FC) ⇒ cue outdoor com RPE como âncora; (4) **threshold sem teste
  protocolado** (Xert "What's My FTP", TriDot auto-threshold) ⇒ valida o
  `ftp-scan` (#6) e sugere futuro **`fthr-scan`** análogo.
- **FTP sugerido (issue #6) — ✅ implementado (v0.0.15)**: `ftp-scan` examina
  treinos fora do plano (eventos pareados não-hermes), filtra (não-MANUAL,
  ≥ 45 min, com potência, intensidade ≥ 75% do FTP), estima via
  `src/ftp_estimation.py` (best-20min × 0,95, gates CV≤15%/min≥80%) e propõe
  **somente para cima** (+3%..+30%) com **confirmação obrigatória** — aplica
  `.env FTP` + `indoor_ftp` do Intervals e registra `ftp_candidates` na meta do
  `plan.json` (preservada por build/reconcile).
- **Tipos de plano (issue #5) — ✅ implementado** (reste: validação da
  prescrição com treinador). `GOAL` no `.env` seleciona o tipo —
  `back-to-fitness` (pós-pausa: base z2, carga ~60%), `ftp-builder`
  (Limiar/Sweet Spot + VO2 curto), `gran-fondo` (endurance longo + volume),
  `time-trial` (esforços limiar/super-limiar), `climbing` (repetições
  3-15min), `active-off-season` (z1-2 leve, ~60%), `race` (exige `RACE_DATE`;
  **últimos 7 dias = Taper pre-prova**). ⚠️ **`race` sempre pergunta a data
  alvo (dia da prova) antes de montar o plano** — sem default/campo vazio.
  📊 **Benchmark (whatsonzwift.com)**: valores do Zwift usados **só como
  calibração de volume/carga** (TSS/sem por tipo — sujeito a TSB + cap
  diário); prescrição **própria** do hermes (periodização clássica,
  validação com treinador pendente); coleção de workouts inspira apenas
  **variedade de formato** (o `build` alterna estruturas - sem replicar
  workouts do Zwift). `plan.json` guarda `goal`/`race_date`; complementa o
  onboarding por objetivo da Fase 3.

### Fase 3 — Produto (casca estilo Runna, ADR-003)
- PWA + onboarding por objetivo → `build` → calendário → Zwift (`.zwo`) +
  assinatura mensal; login com API key do Intervals.
- **Parcialmente iniciado no agente (v0.0.10–0.0.11):** onboarding por objetivo
  (menu GOAL de 7 tipos) + troca de objetivo no meio do plano + disponibilidade
  (`WEEKLY_HOURS`/`LONG_DAY`). Falta a casca (PWA, tela de seleção, assinatura).

### Fase 4 — Multi-atleta / modo treinador
- Dashboard por atleta, parâmetros por atleta, aprovação antes de publicar,
  alertas e relatório semanal. Depende da validação com treinador.

## Regras transversais

- Toda implementação exige **testes** e docs (README/CHANGELOG/vault) no mesmo
  commit.
- Mudanças que afetam carga/plano passam por **`--dry-run`** ou validação com
  dados reais antes de tocar o fluxo do timer diário.

## Status atual (2026-09-22)

Revisão dos itens (release v0.0.15, sessão de 22/09):

- **Abertos (3):** #1 fantasmas (Fase 0 — bug especificado em
  `docs/KNOWN_ISSUES.md`, **prioridade baixa**: cosmético, bug do Intervals,
  não do agente), #2 notificações (Fase 1), #3 treinos sem potência
  (Fase 2 — complementa o `ftp-scan`/FTHR).
- **Fechados:** #4 wellness ✅, #5 tipos de plano ✅ (resta validar a prescrição
  com treinador), **#6 FTP sugerido ✅ (v0.0.15)** — `ftp-scan` implementado e
  validado com dados reais (janela 45d: 8 treinos fora do plano, todos
  filtrados no gate de intensidade); issues #7/#8 (bugs da sessão 22/09)
  corrigidos na v0.0.15.
- **Renumeração (21/09):** a coluna `#` acompanha os números das issues do
  GitHub — FTP é **#6**; a casca Runna (antes #6) é **#7** e multi-atleta
  (antes #7) é **#8**.
- Suíte: **165 testes OK** (v0.0.15).
- Roteiro de validação: **`docs/ROTEIRO-TESTES.md`** (execução em 22/09).
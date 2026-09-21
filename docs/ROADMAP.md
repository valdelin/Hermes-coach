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
| 6 | feature | **FTP sugerido a partir de treinos não agendados** (prova/treino livre): estimar novo FTP do stream de potência (best-20min × 0,95) com gates de qualidade/contexto e confirmação do atleta | [#6](https://github.com/valdelin/Hermes-coach/issues/6) | 2 |
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
- Detectar ausência de potência; configurar `FTHR` no `.env`;
  `hrTSS = seg × IF_hr² × 100 / 3600`; prescrever %FTHR (ou RPE) em dias
  outdoor; sinalizar "sem potência — carga por FC" no resumo.
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

## Status atual (2026-09-21)

Revisão dos itens em aberto (sessão de 21/09, com o #6 novo):

- **Abertos (6):** #1 fantasmas (Fase 0 — bug especificado em
  `docs/KNOWN_ISSUES.md`, **prioridade baixa**: cosmético, bug do Intervals,
  não do agente — saiu do início da sessão de testes 22/09),
  #2 notificações (Fase 1), #3 treinos sem potência (Fase 2),
  #6 **FTP sugerido de treinos não agendados** (Fase 2 — issue registrada
  21/09; complementa o `ftp-check` da #5. **Piloto de implementação em 21/09**:
  investigada a API real — o eFTP não está no perfil, a fonte primária é o
  `icu_pm_ftp` do detalhe da atividade e o stream de potência vem em
  `/streams` (`type == "watts"`); **mecânica pura pronta** em
  `src/ftp_estimation.py` (best-20min × 0,95, gates CV≤15%/min≥80%/diff
  +3%..+30%, clipe de spikes) com 16 testes (suite 138 OK). Faltam: client
  streams/filtro de candidatos, CLI `ftp-scan`, `plan.json` e #2), #7 casca
  Runna (Fase 3 — onboarding por objetivo já existe no agente,
  v0.0.10–0.0.11), #8 multi-atleta (Fase 4 —
  aguarda ROTEIRO-TREINADOR).
- **Fechados:** #4 wellness ✅, #5 tipos de plano ✅ (resta validar a prescrição
  com treinador).
- **Renumeração (21/09):** a coluna `#` acompanha os números das issues do
  GitHub — FTP é **#6**; a casca Runna (antes #6) é **#7** e multi-atleta
  (antes #7) é **#8**.
- Suíte: **138 testes OK** (v0.0.13 + 16 novos de `ftp_estimation`,
  fixtures de reconcile determinísticas).
- Roteiro de validação: **`docs/ROTEIRO-TESTES.md`** (execução em 22/09).
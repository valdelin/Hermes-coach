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
| 1 | bug | Limpeza de "fantasmas" (atividades MANUAL criadas pelo Intervals ao parear treino) | [#1](https://github.com/valdelin/Hermes-coach/issues/1) | 0 |
| 2 | feature | Notificações de treino (Telegram → e-mail/WhatsApp) | [#2](https://github.com/valdelin/Hermes-coach/issues/2) | 1 |
| 3 | feature | Treinos sem medidor de potência (outdoor/FC: FTHR, hrTSS, %FTHR/RPE) | [#3](https://github.com/valdelin/Hermes-coach/issues/3) | 2 |
| 4 | produto | Casca estilo Runna: PWA + onboarding por objetivo + assinatura | — | 3 |
| 5 | produto | Multi-atleta / modo treinador (dashboard por atleta) | — | 4 |

## Fases

### Fase 0 — Higiene de dados (issue #1)
- Limpeza de fantasmas no fluxo `reconcile`/`push` (ou `daily_reconcile.sh`):
  detectar atividade `MANUAL` órfã com nome de evento `hermes-plan*` e duração
  = planejada; confirmar atividade real pareada; excluir via
  `DELETE /api/v1/activity/{id}`.
- Regras: `--dry-run` antes de excluir; testes obrigatórios.

### Fase 1 — Comunicação (issue #2)
- Resumo do treino (foco + TSB + TSS previsto/real + avisos do reconcile) via
  **Telegram** primeiro; interface `Notifier` extensível (e-mail/WhatsApp);
  config `NOTIFY_CHANNEL`/token/chat id no `.env`.
- Regra: envio **assíncrono e não-bloqueante** (não derruba o timer diário).

### Fase 2 — Dados incompletos (issue #3)
- Detectar ausência de potência; configurar `FTHR` no `.env`;
  `hrTSS = seg × IF_hr² × 100 / 3600`; prescrever %FTHR (ou RPE) em dias
  outdoor; sinalizar "sem potência — carga por FC" no resumo.

### Fase 3 — Produto (casca estilo Runna, ADR-003)
- PWA + onboarding por objetivo → `build` → calendário → Zwift (`.zwo`) +
  assinatura mensal; login com API key do Intervals.

### Fase 4 — Multi-atleta / modo treinador
- Dashboard por atleta, parâmetros por atleta, aprovação antes de publicar,
  alertas e relatório semanal. Depende da validação com treinador.

## Regras transversais

- Toda implementação exige **testes** e docs (README/CHANGELOG/vault) no mesmo
  commit.
- Mudanças que afetam carga/plano passam por **`--dry-run`** ou validação com
  dados reais antes de tocar o fluxo do timer diário.
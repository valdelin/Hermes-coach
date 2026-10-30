# Ações operacionais na TUI Context

**Gathered:** 2026-10-29
**Spec:** `.specs/features/ui-operational-actions/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Conectar as ações `build`, `check`, `reconcile` e `push` da TUI à facade
`scripts/hermes_agent.py`, mantendo prévia, confirmação e observabilidade.

---

## Implementation Decisions

### Alterações locais

- `build`, `check` e `reconcile` começam em modo consultivo.
- A TUI mostra o resultado da prévia antes de disponibilizar aplicação.
- A aplicação só ocorre após confirmação explícita do atleta.

### Publicação

- `push --dry-run` é obrigatório antes de qualquer publicação.
- Publicar requer confirmação de continuidade e depois o texto literal
  `PUBLICAR`.

### Fronteira de execução

- A TUI chama apenas `scripts/hermes_agent.py`.
- O `--yes` da facade só é enviado após a confirmação da TUI.

### Agent's Discretion

- Componentes Textual, apresentação de stdout/stderr, limite visual de logs e
  mecanismo de execução assíncrona seguem os padrões da base existente.

### Declined / Undiscussed Gray Areas → Assumptions

- A TUI não terá persistência de logs nesta entrega; a última operação é
  suficiente para a sessão local.

---

## Specific References

- `scripts/hermes_agent.py`: facade e classificação de efeitos.
- `docs/MANUAL-TUI.md`: fronteira local-first e somente leitura atual.

## Deferred Ideas

- Workflows `daily`/`all`, FTP scan, raw CLI e configuração editável.

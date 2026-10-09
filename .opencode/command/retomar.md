---
description: Recupera o contexto operacional do Hermes Coach sem alterar o repositório.
agent: build
---

Recupere o contexto somente por evidências atuais. Não edite arquivos nem
execute comandos mutáveis.

1. Leia `AGENTS.md`, `docs/ROADMAP.md` e, como contexto histórico não autoritativo,
   `docs/OPENCODE-SETUP-STATE.md`.
2. Consulte `git branch --show-current`, `git log -1 --oneline` e `git status --short`.
   Diferencie alterações staged, unstaged e untracked a partir desse estado real.
3. Relate o último commit, o trabalho concluído e as pendências documentadas no
   roadmap. Não invente histórico nem afirme que testes passaram sem evidência
   disponível no repositório ou nesta sessão.
4. Sugira a próxima etapa, mas não a execute. Se ela puder modificar código,
   documentação, `.env`, vault ou calendário, peça autorização explícita antes.

Nunca execute `git add`, `git commit`, `git push`, merge, rebase, reset, limpeza
destrutiva, sync do vault, alterações em `.env` ou ações no Intervals.icu. Não
use caminhos alternativos para contornar as confirmações do Hermes Agent.

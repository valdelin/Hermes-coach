---
name: cycling-coach
description: "Gera/monitora o treino de ciclismo do dia e o plano semanal (seg-sex) no Intervals.icu — consulta TSB, respeita a carga semanal e publica no calendario (o .zwo e baixado no app). Delega ao agente opencode 'cycling-coach'."
version: 2.2.0
author: Hermes Agent -> opencode
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Coding-Agent, Cycling, Zwift, Intervals.icu, Automation]
    related_skills: [opencode]
---

# Cycling Coach (delegacao via opencode)

Skill de delegacao: **o Hermes nao executa o fluxo de treinamento diretamente** —
ele orquestra e delega o trabalho pesado ao CLI do opencode usando o agente
`cycling-coach` (tier gratuito do opencode). Assim os turnos do Hermes ficam
curtos e a consulta/geracao de treinos nao consome credito de modelo.

## Pre-requisitos

- opencode instalado e autenticado no CLI (o tier gratuito basta).
- Agente `cycling-coach` instalado em `.opencode/agent/` do projeto
  `/home/valdelin/Work/hermes-coach` e linkado em `~/.config/opencode/agent/`.
- `.env` do projeto configurado com `INTERVALS_ATHLETE_ID`, `INTERVALS_API_KEY`,
  `FTP` e (opcional) `CUE_LANG` (`pt` padrao | `en`) para o idioma das mensagens.

## Regras de agendamento (passadas ao agente)

- Semana-base = **segunda a sexta**: todos os dias uteis tem treino; sabado e
  domingo sao descanso (treino de fim de semana so por pedido explicito).
- Carga semanal respeitada via orcamento rolante de 7 dias (TSS): se estourar,
  reduz o `on_sec`/`on_power` do dia e a folga passa aos dias subsequentes.
- Treino de hoje a tarde, quando solicitado: gera respeitando o ciclo do dia e a
  carga da semana, adiciona ao `plan.json` e publica com `push --start <hoje>`.
- Nome do evento no Intervals: `YYYY-MM-DD - Treino de <Foco>`.

## Procedimento

1. Confirme que o projeto existe e o `.env` tem credenciais (sem exibir valores).
2. Delega ao CLI com `run` (saida JSON, sem TTY):
   - `opencode run --agent cycling-coach --format json "Gere o treino de hoje do Intervals.icu e publique no calendario"`
   - workdir: `/home/valdelin/Work/hermes-coach`
   - Se a tarefa for longa/multiturno, prefira `background=true, pty=true`
     (monitore com `process(poll/log)`; saia com `process(action="write", data="\\x03")`).
3. Recapitule o essencial para o usuario: TSB atual, foco do treino e TSS estimado.
4. Nunca copie a API key do Intervals.icu nem a imprima. Fica so no `.env`.

## Plano de treinos (fluxo completo)

Quando o usuario pedir "monte/a ajuste o plano de treinos":

1. Delegue ao agente no CLI do opencode (workdir `/home/valdelin/Work/hermes-coach`):
   ```
   opencode run --agent cycling-coach --format json "Monte o plano das proximas 2 semanas respeitando seg-sex e a carga semanal e publique no calendario do Intervals.icu"
   ```
2. O agente executa: `info` (TSB atual) → `build` (historico -> plano seg-sex +
   orcamento de carga) → `reconcile` (treinos feitos/perdidos, recuperacao no
   proximo dia util) → `push` (calendario; remove automaticamente orfaos
   `hermes-plan*`).
3. Volte ao usuario um resumo: semana planejada (com TSS de cada dia) e TSB atual.
   Lembre que os `.zwo` sao baixados no app do Intervals (Custom Workouts).
4. Diariamente (ou a pedido), rode o fluxo novamente para o plano se adaptar.
   A meia-noite um timer do systemd (`cycling-coach-daily`) ja roda
   `reconcile + push` automaticamente (script `scripts/daily_reconcile.sh`,
   log em `logs/daily_reconcile.log`); nao foi preciso pedir manualmente.
5. **Teste de FTP:** periodicamente (ou a cada sessao de plano), o agente roda
   `ftp-check` e, se o reteste for devido (janela padrao de 8 semanas), sugere ao
   usuario refazer o **Ramp Test do app Zwift** em dia descansado para avaliar o
   progresso. O pedido partiu do usuario: "quando o hermes achar necessario,
   sugerir teste de FTP, de preferencia ramp test". Nao agenda o teste sozinho:
   apenas sugere e, se aceito, ajusta o plano.

## Descricao no Intervals (formato nativo)

Os treinos publicados usam a notacao nativa do workout builder no campo
`description` (os passos aparecem no app como `8m 88% (141w)`). Desde a v2.2,
cada passo ganha uma mensagem explicativa (cue text -> textevent no .zwo):
aquecimento com o roteiro da zona + estrutura do dia (e progressao vs. o treino
anterior do mesmo foco) e "Agora voce vai entrar em X minutos a Y por cento do
seu FTP" antes de cada intervalo. Repeticoes sao achatadas em passos
individuais (o parser do Intervals descarta o grupo `Nx` com texto interno) e o
idioma e controlado por `CUE_LANG`. Nao altere esse formato ao ajustar um
treino; mantenha o padrao do agente.

## Pitfalls

- Nao rode o Hermes executando a CLI diretamente se ele puder delegar ao opencode:
  a orquestracao dele custa turnos, a do opencode no CLI e gratis.
- O `push` padrao comeca amanha. Para incluir o treino de hoje (criado a tarde),
  use `push --start <data-de-hoje>`.
- Nao gere `.zwo` local: os arquivos sao baixados no app do Intervals.icu.
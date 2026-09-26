# Portal do cycling coach — desenho de interface (v0)

> Status: **rascunho aprovado em 22/09/2026** (Trilha B — mapa de telas);
> **decisões de UX (aprovação, reconcile, sem chat, dashboard essencial) em
> 26/09/2026** — ver "Decisões fixadas" e "Decisões pendentes (roadmap)".
> Sem código implementado ainda; `docs/PORTAL-UI-DESIGN.md` é a fonte do
> desenho; o vault espelha. Nada aqui altera o fluxo atual (CLI + timer +
> container) — o portal entra como camada nova (`web/`), motor via
> `AthleteContext` (Fase 0 do plano).

## Objetivo

Portal de acesso ao cycling coach, **multi-usuário desde o início**, com os
papéis `admin` / `coach` / `atleta`. Um login = um papel. Coach liga-se a
atletas via `roster`. Interface **web responsiva** (SPA React); PWA na Fase 3;
app nativo **fora do roadmap**.

## Decisões fixadas

| # | Decisão |
|---|---|
| Aprovação | **Sempre com aprovação antes de publicar.** Solo: o atleta decide. Com treinador: o treinador decide. Nada novo vai ao calendário sem OK (vale para `build` **e** `reconcile`) |
| Publicação | **Proposta na meia-noite → aprovação → publicação** + botão manual "publicar agora" (que também passa por aprovação) |
| Reconcile | **Ajustes por treino perdido/extra também vão para a fila de aprovação** — não entram sozinhos no calendário |
| Interação | **Sem chat.** A interface oferece **ações/opções pré-definidas** (ex.: "trocar objetivo", "mudar dia longo", "aprovar", "rejeitar") e o usuário decide clicando — nada de caixa de texto livre/LLM na primeira versão |
| Design | **Seguir o visual dos relatórios HTML atuais** (`src/report.py` + `src/brand.py`): 22 temas do Omarchy quattro (default tokyo-night), cards, barra de TSS da semana, linha de forma (TSB) colorida por zona (risco ≤ −10 / ideal / fresco ≥ +10) e tooltip temático — o portal herda o kit de `docs/TEMAS.md` |
| Dashboard | **Só o essencial**: resumo do dia (prontidão + treino de hoje) e da semana (TSS planejado × feito) + alertas. Detalhes (passos, zonas, %FTHR/RPE) ficam no **Calendário** (menu) |
| Dados | **Ao vivo** a cada abertura do portal, com fallback para cache (SQLite) se o Intervals cair |
| Idioma | Interface em português (i18n depois) |
| Alerta | TSB ≤ **−10** (régua inicial, ajustável depois) |
| Stack | API FastAPI + React (Vite + TypeScript + Tailwind) — SPA |
| Multi-tenant | Motor via `AthleteContext`; roles admin/coach/athlete; um user = um atleta; coach via roster; "conta de time" fica para o futuro |
| Intervals | Conexão via **OAuth 2.0** (Bearer + refresh), app registrado; HTTPS via hostname grátis (`<ip>.sslip.io` ou DuckDNS) no início |

## Navegação por papel

```
Configuração inicial: LOGIN · CONECTAR INTERVALS (OAuth) · ONBOARDING (objetivo + dias + horas)

ATLETA   Dashboard · Calendário · Aprovações · Plano/Objetivo · Histórico · Ajustes
COACH    Atletas · Atleta :id · Aprovações · (Resumos semanais — Fase 2)
ADMIN    (tudo do coach) + Jobs · Config · Usuários/convites
```

## Telas (informação e fonte)

| Tela | Conteúdo | Fonte |
|---|---|---|
| **Dashboard‑atleta** | **só o essencial**: prontidão do dia (RHR/TSB/alertas) · **treino de hoje** (foco, TSS alvo × feito, duração, status, link `.zwo`) · **resumo da semana** (barras de TSS planejado × feito) · chips de alerta (aprovação pendente · treino perdido · TSB ≤ −10 · reteste FTP devido · taper) · contagem p/ RACE_DATE · **ações rápidas** (ex.: "publicar agora", "marcar feito", "ver semana") | motor + Intervals (ao vivo) + cache SQLite |
| **Aprovações (atleta)** | **fila de diffs propostos** (`build` e `reconcile`): o que muda, por quê, impacto na carga → **aprovar/rejeitar (com comentário opcional)** → publica; história das aprovações | motor (`build`/`reconcile`) + SQLite |
| **Calendário** | semana com foco/duração/TSS/status · detalhe do treino com **passos** (notação builder, %FTHR/RPE) | SQLite (plano) + Intervals (pareamento) |
| **Plano/Objetivo** | GOAL atual, RACE_DATE, FTP_TEST_DATE, perfil (dias, horas, long day) · troca com **preview do diff** → confirmar | motor (`build`) |
| **Histórico** | TSS/CTL/ATL 4 semanas · execução planejado × feito · evolução de FTP | SQLite (plans/jobs) + Intervals |
| **Atletas (coach)** | cards por atleta: status resumido + alertas + acesso ao dashboard do atleta (leitura) | SQLite/Intervals agregado |
| **Aprovações (coach)** | fila de diffs propostos → **aprovar/rejeitar (com comentário)** → publica; atleta lê o resultado | motor (`build`/`reconcile`) |
| **Jobs (admin)** | execuções por atleta: ação, status, resumo, erro | SQLite (`jobs`) |
| **Sistema (admin)** | usuários, convites de coach, config do app OAuth, limites (tiers futuros) | SQLite |

## Fluxos

- **Auth/OAuth:** email+senha → "Connect with Intervals" (OAuth 2.0, redirect
  HTTPS) → token protegido com refresh.
- **Publicação (sempre com aprovação):** meia-noite → scheduler roda
  `build`/`reconcile` para cada atleta ativo e **gera a proposta** (diff), não
  publica → atleta (solo) ou coach vê a fila em **Aprovações** → aprova →
  `push`. Botão **"publicar agora"** força a geração fora do horário, mas a
  proposta também passa pela fila de aprovação.
- **Aprovação:**
  - *Solo:* sistema propõe → **atleta** vê o diff → aprova → publica.
  - *Com coach:* sistema propõe → **coach** aprova/rejeita (comentário) →
    publica → atleta vê o resultado.
  - **Reconcile idem:** ajuste por treino perdido/extra entra na mesma fila
    com o porquê (recuperação + limiar −5%) e só publica com OK.
- **Onboarding:** objetivo → dias de treino → horas semanais → long day →
  connect Intervals → primeira semana montada.
- **Dados ao vivo:** abertura do portal → fetch Intervals → cache (fallback se API fora).
- **Interação por ações (sem chat):** menus e botões pré-definidos ("trocar
  objetivo", "mudar dia longo", "aprovar", "rejeitar", "publicar agora"); o
  usuário escolhe a ação e confirma. Caixa de texto livre/chat fica para o
  futuro (exigiria LLM/Coach+ — fora da primeira versão).

## Em aberto (não bloqueia; evolui)

Visual/PWA, i18n, tiers/preço/assinatura, "conta de time" (equipe), detalhes
de notificação (Fase 2), comentários na aprovação, catálogo de eventos (#11),
integração fina com relatórios do treinador.

## Decisões pendentes (roadmap)

Registradas para decisão antes/durante a Fase 1 (ver ROADMAP):

| # | Decisão | Por quê importa |
|---|---|---|
| P1 | **O que acontece se não houver aprovação até o treino** (meia-noite passou e ninguém aprovou a proposta de amanhã)? Opções: (a) publica mesmo assim com aviso; (b) fica pendente e o dia fica sem treino publicado; (c) expira e repete na próxima janela | Define se o calendário do atleta pode "ficar vazio" de um dia pro outro |
| P2 | **Onde o atleta aprova: na fila de Aprovações ou inline no Calendário/Dashboard?** (fila dedicada vs aprovar direto no treino afetado) | Muda a navegação e o esforço de implementação |
| P3 | **Notificação de pendência**: como o atleta sabe que há proposta aguardando (badge, Telegram/e-mail — issue #2, push)? | Aprovação só funciona se o atleta souber que precisa agir |
| P4 | **Profundidade do Dashboard vs Calendário**: confirmar na primeira versão se passos/zonas ficam só no Calendário, ou se o Dashboard ganha um "detalhe do treino de hoje" expansível | Avaliar com protótipo; troca depois se o atleta quiser |
| P5 | **Catálogo de ações pré-definidas** (v1): quais entram (trocar objetivo, dias, horas, long day, aprovar/rejeitar, publicar agora, marcar feito) e quais ficam para depois | Escopo da primeira versão sem chat |
| P6 | **Chat/Coach+ futuro**: quando entrar (LLM por treino tem custo) e se entra como menu de perguntas com respostas pré-formatadas antes de virar conversa livre | Escopo SaaS #29 |
| P7 | **Protótipo navegável do Dashboard** (HTML com o visual de verdade + dados reais/de exemplo) para validar na tela: hierarquia P4, onde aprovar (P2), menu de ações (P5) e o tom visual. **Direção já definida: herdar o kit dos relatórios** (22 temas do Omarchy, default tokyo-night, cards, linha de forma por zona) | Fazer em outra sessão; não bloqueia a Fase 0 |

## Fases (rastreáveis no repo)

| Fase | Escopo | Issue |
|---|---|---|
| 0 | Fundação multi-tenant: `AthleteContext` (file + SQLite), OAuth no `IntervalsClient`, schema (users/roster/athletes/oauth_tokens/plans/jobs), testes | issue — Portal Fase 0 |
| 1 | API FastAPI + auth/RBAC + OAuth + scheduler por atleta + SPA React (telas acima) + deploy (web+caddy, HTTPS `sslip.io`) — somente o fundador usa | issue — Portal Fase 1 |
| 2 | Onboarding de treinadores (convite, roster, aprovação) + notificações por usuário (Telegram/e-mail, issue #2) + resumos semanais | issue — Portal Fase 2 |
| 3 | PWA, domínio próprio, tiers solo/coach, retenção | (adiar) |
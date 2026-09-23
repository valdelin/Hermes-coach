# Portal do cycling coach — desenho de interface (v0)

> Status: **rascunho aprovado em 22/09/2026** (Trilha B — mapa de telas).
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
| Aprovação | **Solo: o atleta decide.** Com treinador: **o treinador decide** antes de publicar |
| Publicação | **Automática (meia-noite, como hoje) + botão manual** "publicar agora" |
| Dados | **Ao vivo** a cada abertura do portal, com fallback para cache (SQLite) se o Intervals cair |
| Idioma | Interface em português (i18n depois) |
| Alerta | TSB ≤ **−10** (régua inicial, ajustável depois) |
| Stack | API FastAPI + React (Vite + TypeScript + Tailwind) — SPA |
| Multi-tenant | Motor via `AthleteContext`; roles admin/coach/athlete; um user = um atleta; coach via roster; "conta de time" fica para o futuro |
| Intervals | Conexão via **OAuth 2.0** (Bearer + refresh), app registrado; HTTPS via hostname grátis (`<ip>.sslip.io` ou DuckDNS) no início |

## Navegação por papel

```
Configuração inicial: LOGIN · CONECTAR INTERVALS (OAuth) · ONBOARDING (objetivo + dias + horas)

ATLETA   Dashboard · Calendário · Plano/Objetivo · Histórico · Ajustes
COACH    Atletas · Atleta :id · Aprovações · (Resumos semanais — Fase 2)
ADMIN    (tudo do coach) + Jobs · Config · Usuários/convites
```

## Telas (informação e fonte)

| Tela | Conteúdo | Fonte |
|---|---|---|
| **Dashboard‑atleta** | TSB/CTL/ATL hoje · **treino de hoje** (foco, TSS alvo × feito, duração, zona, status, link `.zwo`) · barras de TSS da semana (planejado × feito) · chips de alerta (treino perdido · TSB ≤ −10 · reteste FTP devido · taper) · contagem p/ RACE_DATE | motor + Intervals (ao vivo) + cache SQLite |
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
- **Publicação:** meia-noite → scheduler roda `reconcile + push` para cada
  atleta ativo (automático, como o timer atual); botão **"publicar agora"**
  permite forçar fora do horário. Diffs de `build` seguem a regra de aprovação.
- **Aprovação:**
  - *Solo:* sistema propõe → **atleta** vê o diff → aprova → publica.
  - *Com coach:* sistema propõe → **coach** aprova/rejeita (comentário) →
    publica → atleta vê o resultado.
- **Onboarding:** objetivo → dias de treino → horas semanais → long day →
  connect Intervals → primeira semana montada.
- **Dados ao vivo:** abertura do portal → fetch Intervals → cache (fallback se API fora).

## Em aberto (não bloqueia; evolui)

Visual/PWA, i18n, tiers/preço/assinatura, "conta de time" (equipe), detalhes
de notificação (Fase 2), comentários na aprovação, catálogo de eventos (#11),
integração fina com relatórios do treinador.

## Fases (rastreáveis no repo)

| Fase | Escopo | Issue |
|---|---|---|
| 0 | Fundação multi-tenant: `AthleteContext` (file + SQLite), OAuth no `IntervalsClient`, schema (users/roster/athletes/oauth_tokens/plans/jobs), testes | issue — Portal Fase 0 |
| 1 | API FastAPI + auth/RBAC + OAuth + scheduler por atleta + SPA React (telas acima) + deploy (web+caddy, HTTPS `sslip.io`) — somente o fundador usa | issue — Portal Fase 1 |
| 2 | Onboarding de treinadores (convite, roster, aprovação) + notificações por usuário (Telegram/e-mail, issue #2) + resumos semanais | issue — Portal Fase 2 |
| 3 | PWA, domínio próprio, tiers solo/coach, retenção | (adiar) |
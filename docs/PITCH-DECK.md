# Pitch Deck — Hermes Coach

**Rascunho para apresentação a investidor** (anjo/seed). Conteúdo baseado nos
docs reais do repo: `docs/ROADMAP.md`, `docs/ARQUITETURA.md`, ADR-003 (vault),
benchmarks de mercado (22/09–23/09) e avaliação comercial #12.

> Formato: 12 slides. Cada seção tem (a) o texto da tela — curto, pronto para
> colar no Gamma/Slidebean — e (b) nota do apresentador (não vai no slide).
> Idioma: PT-BR por padrão; versão EN fácil (traduzir títulos + textos).

---

## Slide 1 — Capa

**Hermes Coach**
*O treinador automático de ciclismo indoor*

Plano adaptativo que decide por você, agenda no seu calendário e se ajusta
sozinho após cada treino — integrado ao ecossistema que você já usa
(Zwift, Garmin, Wahoo).

> **Nota:** logo + tagline. Se tiver, 1 demo curta (app no celular) aqui.
> Fechar com: "automação ponta-a-ponta — do plano ao calendário, sem app pra
> abrir todo dia".

---

## Slide 2 — Problema

**Treinar com ciência é difícil e dá trabalho**

- Apps de treino exigem **abrir todo dia**, escolher o workout, decidir pelo atleta.
- Planos comprados são **estáticos**: não reagem se você perde um treino, viaja
  ou faz um pedal extra.
- Ferramentas de dados (Intervals.icu, TrainingPeaks) mostram **métricas**, mas
  **não decidem por você**.
- O resultado: amadores seguem planilha cega, erram na carga e não evoluem — ou
  desistem.

> **Nota:** dar um exemplo concreto do atleta: perdeu 1 treino na semana → o
> plano do concorrente não muda nada; o Hermes insere recuperação e reduz o
> próximo limiar automaticamente.

---

## Slide 3 — Solução

**Um treinador que decide, agenda e se corrige sozinho**

- **Decide:** foco do dia pelo TSB (forma × fadiga), não por calendário fixo.
- **Agenda:** o treino cai no calendário do Intervals.icu → `.zwo` no Zwift.
- **Corrige:** `reconcile` detecta treino perdido ou extra fora do plano e
  ajusta recuperação + intensidade — sozinho.
- **Respeita a sua vida:** dias de treino, horas disponíveis, dia preferido para
  o longo (`TRAINING_DAYS`, `WEEKLY_HOURS`, `LONG_DAY`).
- **Funciona sem medidor de potência:** prescrição em %FTHR + RPE (outdoor/FC).

> **Nota:** 3 verbos (decide/agenda/corrige) é o takeaway. Se der, 1 gif do
> calendário recebendo treino + reconcile ajustando.

---

## Slide 4 — Mercado

**Ciclismo indoor/outdoor amador é grande e paga por assinatura**

- Referências de preço verificadas (2026):
  - Xert US$8,33–14,99/mês · Pillar App ~US$7,99/mês · RunDot ~US$9,99/mês
  - TriDot US$14,99–39/mês (solo) · **US$99–249/mês (multi-atleta/coach)**
- **Solo amador:** US$8–15/mês (~R$ 45–80) — faixa comprovada de aceitação.
- **B2B treinador:** US$99–249/mês por atleta — ARPU 10–30× maior.

> **Nota:** posicionar Hermes entre "app de dados gratuito" (Intervals) e
> "assessoria cara" (coach 1:1) — assinatura acessível com valor de coaching.

---

## Slide 5 — Produto (como funciona)

**O motor já roda hoje** (v0.0.20, 216 testes OK)

- Motor Banister local: **CTL/ATL/TSB** → foco do dia por faixa (`<-15` → Z2;
  `-15..0` → Sweet Spot; `0..5` → Limiar; `>=+5` → VO2).
- **Expected PMC:** projeta forma/fadiga com treinos reais **+** planejados
  (TSB hoje → próxima semana; alertas de sobrecarga).
- **Plan adherence:** execução medida — feito × perdido × pendente por semana.
- Orçamento semanal de carga (TSS 7d ≤ cap diário × 7) — nunca estoura.
- **7 tipos de plano** (`GOAL`): base, FTP builder, gran-fondo, time-trial,
  climbing, off-season, **race** (com `RACE_DATE` e taper automático na semana
  da prova).
- **`ftp-scan`:** sugere novo FTP sem teste protocolado (best-20min × 0,95).
- **Modo FC:** sem medalha de potência → %FTHR + RPE.
- Integração: API do Intervals.icu (Garmin/Zwift/Wahoo/Polar/COROS...) + Zwift.

> **Nota:** é o slide de maior densidade técnica — mantenha só o essencial e
> mostre 1 print do calendário/`info` se possível. "216 testes OK" é sinal de
> engenharia séria; guarde detalhe para o Q&A.

---

## Slide 6 — Diferenciais (moat)

**Automação ponta-a-ponta que nenhum concorrente tem**

| Capacidade | Hermes | Xert | Pillar | TriDot |
|---|---|---|---|---|
| Plano por objetivo + taper | ✅ | ✅ | ✅ | ✅ |
| Sem medidor de potência | ✅ | ✅ | ✅ | ✅ |
| Threshold sem teste | ✅ | ✅ | ✅ | ✅ |
| Execução medida vs prescrição | ✅ | ✅ | ✅ | ✅ |
| **Decide + agenda + corrige sozinho** | ✅ | ❌ | ❌ | ❌ |

- Concorrentes exigem **app/ação manual todo dia**; o Hermes roda sozinho
  (`systemd` timer diário + reconcile noturno).
- **Custo de operação ~R$ 0:** a orquestração é determinística (sem LLM por
  treino) — rodar o serviço é barato, margem alta.
- **Tredict** (benchmark 23/09) é o concorrente conceitual mais próximo —
  plataforma completa (análise + IA + sync de devices, MCP server). **Valida o
  conceito** (previsão de forma, detecção de FTP/LTHR) **e o contraste:** eles
  são a plataforma de dados; o Hermes é o cérebro determinístico/auditável
  sobre o ecossistema que o atleta já usa.

> **Nota:** a linha do meio (automação) é o argumento central de investimento.
> Reforçar: "não é mais um app de treino — é o backend de coaching".

---

## Slide 7 — Validação (o que já está provado)

- Motor **rodando em produção pessoal** há ~1 semana (timer diário +
  calendário real no Intervals.icu).
- Benchmarks de mercado concluídos (22/09–23/09): Xert, Pillar, TriDot,
  RunDot, Zwift, **Tredict** — prescrição, precificação e posicionamento
  validados contra o padrão do mercado.
- **Roteiro de validação com treinador** pronto (`ROTEIRO-TREINADOR.md`):
  ciência do treino + produto multi-atleta + pricing (perguntas 9–12 adicionadas).
- **Acesso a treinadores via rede do fundador:** treinadores conhecidos entram
  como **beta testers** — primeiro piloto com custo de aquisição ~zero.
- 216 testes automatizados; CI no GitHub.

> **Nota reta:** ainda não é tração comercial (zero pagantes) — seja honesto.
> A validação até agora é de **motor + mercado + método**; o próximo marco é o
> piloto com treinadores conhecidos como beta testers (ver Slide 9).

---

## Slide 8 — Modelo de negócio

**Assinatura em 2 tiers (a validar com treinador)**

| Tier | Público | Preço-alvo | Análogo de mercado |
|---|---|---|---|
| **Solo** | Ciclista amador | **US$8–15/mês** (~R$ 45–80) | Xert/Pillar/RunDot |
| **Coach/Multi-atleta** | Treinador gerenciando atletas | **US$99–249/mês** | TriDot Complete/Coached |

- Custo marginal de cada atleta: mínimo (sem LLM por treino, API do Intervals).
- Caminho: **PWA + onboarding por objetivo + assinatura** (Fase 3 do roadmap)
  → validar disposição a pagar → tiers.

> **Nota:** 1 treinador com 20 atletas a US$99 = US$2k/mês — o B2B é o motor
> de receita; o solo é o funil de aquisição.

---

## Slide 9 — Roadmap

**Já implementado → próximas 3 fases**

| Fase | Entrega | Status |
|---|---|---|
| Motor (0–2) | Plano, GOAL×7, race/taper + TSB no dia da prova, FTP scan, modo FC, wellness, Expected PMC com zonas Friel, adherence | ✅ feito (v0.0.20) |
| Comunicação (1) | Notificações Telegram → e-mail/WhatsApp | 🔜 issue #2 |
| Casca/produto (3) | PWA + onboarding + assinatura + catálogo de eventos | 📋 Fase 3 (#7/#11/#12) |
| Multi-atleta (4) | Dashboard por atleta, aprovação, alertas | 📋 Fase 4 (#8) |

- Validar com treinador antes do B2B (ROTEIRO-TREINADOR).
- **Piloto:** treinadores conhecidos do fundador como **beta testers** (1–2, com
  seus atletas lendo/escrevendo no Intervals) — aquisição inicial com custo ~zero.

> **Nota:** mostrar que o caminho está desenhado e priorizado, não é roadmap
> de slide bonito. O próximo investimento vai 100% para Fase 1 + 3.

---

## Slide 10 — Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Dependência da API do Intervals.icu | Camada fina por design; a decisão é local (motor próprio); API aberta/OAuth |
| "Camada fina" = difícil cobrar | Diferencial de automação + motor próprio (não é só integração) |
| Ciência do treino questionada | Validação com treinador (ROTEIRO) + benchmarks de mercado |
| Mercado indoor depende de Zwift/equipamento | Modo FC já cobre outdoor sem medidor de potência |

> **Nota:** 2º risco é o mais provável de aparecer no Q&A — resposta: "o
> concorrente vende plano; nós vendemos **decisão automática + ajuste**; o
> Intervals é backend, não coach".

---

## Slide 11 — Time

**1 fundador (full-stack: produto + engenharia + ciência do treino)**

- Construiu o motor completo: TSB, plano, reconcile, FTP scan, Expected PMC,
  adherence, integração Intervals/Zwift — 216 testes, rodando em produção.
- Fez benchmarks de mercado e rascunhou o roteiro de validação com treinador.
- [Se aplicar] Validando com treinador de ciclismo real (parceria de
  validação/consultoria).

> **Nota:** se houver co-fundador/advisor em esportes ou app, citar aqui. Time
> pequeno é OK em pré-seed se a execução estiver provada — mostre commits/demo.

---

## Slide 12 — Ask

**Estamos levantando US$ 25k** 🔧 *(proposta — confirmar)* **para validar o
produto e chegar aos primeiros pagantes**

> 🔧 = valor proposto por mim com base nos benchmarks; **só o fundador decide**
> o número final. Troque antes de apresentar.

Uso do capital (12 meses):
1. **Notificações (issue #2)** — primeiro valor visível para o atleta;
2. **Casca PWA + onboarding + assinatura (Fase 3)** — mínimo produto assinável;
3. **Piloto com 1–2 treinadores (modo multi-atleta)** — treinadores conhecidos
   do fundador como beta testers: validação B2B + pricing;
4. Aquisição inicial: **rede de treinadores (beta testers)** + comunidade
   Zwift/Intervals + conteúdo de treino.

Meta de 12 meses 🔧 *(proposta)*: **100 atletas solo + 3 treinadores** → ARR
~**US$ 70–90k**

Cálculo da proposta:
- Solo: 100 × US$ 9/mês ≈ US$ 10,8k/ano
- Coach: 3 treinadores × 20 atletas × US$ 99/mês ≈ US$ 71,3k/ano
- Total ≈ US$ 82k ARR (margem alta: operação sem custo de LLM)

> **Nota:** o número de 12 meses deve ser um milestone crível, não otimista —
> investidor anjo quer ver marco de saída ("mínimo produto pago até [mês]"),
> não narrativa. Se preferir meta menor, ajuste o slide.

---

## Apêndice — fatos usados (para Q&A)

- Versão atual: **v0.0.20** · 216 testes OK · CI verde · timer systemd rodando.
- Pricing concorrentes verificado em 22/09/2026 (fontes oficiais).
- Repo **privado** (`github.com/valdelin/Hermes-coach`) — código sob demanda
  (demonstração/NDA para investidores); docs públicos resumidos no pitch.
- Non-goals (ADR-003): **não** reimplementar tracking/sync de dispositivos —
  usamos Intervals.icu como backend de dados.
- Posicionamento vs Tredict: eles são a **plataforma de dados/IA**; o Hermes é
  o **cérebro de coaching determinístico** sobre o ecossistema (ADR-003).
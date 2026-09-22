# Hermes Coach

O treinador automático de ciclismo indoor

Plano adaptativo que decide por você, agenda no seu calendário e se ajusta sozinho após cada treino — integrado ao ecossistema que você já usa (Zwift, Garmin, Wahoo).

---

# O problema

Treinar com ciência é difícil e dá trabalho

- Apps de treino exigem abrir todo dia, escolher o workout, decidir pelo atleta
- Planos comprados são estáticos: não reagem se você perde um treino, viaja ou faz um pedal extra
- Ferramentas de dados (Intervals.icu, TrainingPeaks) mostram métricas, mas não decidem por você
- Resultado: amadores seguem planilha cega, erram na carga e não evoluem — ou desistem

---

# A solução

Um treinador que decide, agenda e se corrige sozinho

- Decide: foco do dia pelo TSB (forma × fadiga), não por calendário fixo
- Agenda: o treino cai no calendário do Intervals.icu → .zwo no Zwift
- Corrige: detecção de treino perdido ou extra ajusta recuperação e intensidade automaticamente
- Respeita a sua vida: dias de treino, horas disponíveis, dia preferido para o longo
- Funciona sem medidor de potência: prescrição em %FTHR (outdoor/FC)

---

# Mercado

Ciclismo amador é grande e paga por assinatura

- Preços de referência verificados (2026): Xert US$ 8,33–14,99/mês · Pillar ~US$ 7,99/mês · RunDot ~US$ 9,99/mês
- TriDot: US$ 14,99–39/mês solo · US$ 99–249/mês multi-atleta/coach
- Solo amador: US$ 8–15/mês — faixa comprovada de aceitação
- B2B treinador: US$ 99–249/mês por atleta — ARPU 10–30× maior

---

# Produto

O motor já roda hoje (v0.0.16, 181 testes OK)

- Motor Banister local: CTL/ATL/TSB → foco do dia por faixa (Z2, Sweet Spot, Limiar, VO2)
- Orçamento semanal de carga (TSS) — nunca estoura
- 7 tipos de plano: base, FTP builder, gran-fondo, time-trial, climbing, off-season, race (com taper automático)
- Novo FTP sem teste: best-20min × 0,95
- Modo FC: sem medidor de potência → %FTHR
- Integração: API do Intervals.icu (Garmin, Zwift, Wahoo, Polar, COROS...) + Zwift

---

# Diferenciais

Automação ponta-a-ponta que nenhum concorrente tem

- Concorrentes (Xert, Pillar, TriDot) exigem app e ação manual todo dia
- Hermes roda sozinho: timer diário + reconciliação noturna
- Custo de operação ~R$ 0: orquestração determinística, sem LLM por treino
- Não é mais um app de treino — é o backend de coaching

---

# Validação

O que já está provado

- Motor rodando em produção (timer diário + calendário real no Intervals.icu)
- Benchmarks de mercado concluídos: Xert, Pillar, TriDot, RunDot, Zwift
- Roteiro de validação com treinador pronto: ciência + multi-atleta + pricing
- Acesso a treinadores via rede do fundador: treinadores conhecidos entram como beta testers (primeiro piloto, custo ~zero)
- 181 testes automatizados, CI no GitHub

---

# Modelo de negócio

Assinatura em 2 tiers (a validar com treinador)

- Solo: ciclista amador · US$ 8–15/mês · análogo Xert/Pillar/RunDot
- Coach/Multi-atleta: treinador gerenciando atletas · US$ 99–249/mês · análogo TriDot
- Custo marginal por atleta mínimo (sem LLM, API do Intervals)
- Caminho: PWA + onboarding por objetivo + assinatura → validar disposição a pagar

---

# Roadmap

Já implementado → próximas 3 fases

- Motor (Fases 0–2): plano, 7 objetivos, race/taper, FTP scan, modo FC, wellness — feito (v0.0.16)
- Comunicação (Fase 1): notificações Telegram → e-mail/WhatsApp — em andamento
- Casca/produto (Fase 3): PWA + onboarding + assinatura + catálogo de eventos
- Multi-atleta (Fase 4): dashboard por atleta, aprovação, alertas
- Piloto: treinadores conhecidos do fundador como beta testers (1–2, com seus atletas no Intervals) — aquisição inicial com custo ~zero

---

# Riscos e mitigação

- Dependência da API do Intervals.icu → camada fina por design; decisão local (motor próprio)
- "Camada fina" = difícil cobrar → diferencial de automação + motor próprio
- Ciência do treino questionada → validação com treinador + benchmarks
- Mercado indoor depende de Zwift → modo FC cobre outdoor sem medidor de potência

---

# Time

- 1 fundador full-stack: produto + engenharia + ciência do treino
- Motor completo construído: TSB, plano, reconcile, FTP scan, integração Intervals/Zwift — 181 testes em produção
- Benchmarks de mercado e roteiro de validação com treinador prontos

---

# Ask

Estamos levantando US$ 25k para validar o produto e chegar aos primeiros pagantes

Uso do capital (12 meses):
1. Notificações (issue #2) — primeiro valor visível para o atleta
2. Casca PWA + onboarding + assinatura (Fase 3) — mínimo produto assinável
3. Piloto com 1–2 treinadores (modo multi-atleta) — treinadores conhecidos como beta testers: validação B2B + pricing
4. Aquisição inicial: rede de treinadores (beta testers) + comunidade Zwift/Intervals + conteúdo de treino

Meta de 12 meses: 100 atletas solo + 3 treinadores → ARR ~US$ 70–90k
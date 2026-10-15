# Roadmap — próximas implementações

> [!info] Dono deste documento
> Fonte canônica: `docs/ROADMAP.md` **no repo** (o mesmo arquivo do vault é
> cópia). Quando divergirem, o repo vence. Editar no repo e copiar.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/PLANO-NOVAS-IMPLEMENTACOES.md`.

Plano consolidado das próximas implementações do Hermes Coach. Cada item tem
rastreio no GitHub (issue) e estágio.

Referências: [ADR-003](https://github.com/valdelin/Hermes-coach/issues) (visão
de produto: "Runna do ciclismo indoor" — ver `docs/ARQUITETURA.md` e vault);
**fundamentação científica** do algoritmo em `docs/EMBASAMENTO-CIENTIFICO.md`
(o **contrato algorítmico** canônico no repo; o vault é somente espelho de
leitura). `ZoneIntegrityTest` compara `src/coach.py:ZONE_BANDS` com um literal
no próprio teste; não lê Markdown nem estabelece uma fonte científica;
**visão SaaS** (arquitetura alvo multi-tenant) em
`docs/ROADMAP-2-CRIACAO-DE-SAAS.md` (itens #24-#27, Fases 1B/3B); **parecer da
revisão técnica** (propostas aplicadas/não aplicadas) em
`docs/proposta-de-melhorias-do-sistema.md`.

## Backlog

| # | Tipo | Item | Issue | Status | Fase |
|---|---|---|---|---|---|
| 1 | bug | Limpeza de "fantasmas" (atividades MANUAL criadas pelo Intervals ao parear treino) — **prioridade baixa** (cosmético, bug do Intervals, não do agente) | [#1](https://github.com/valdelin/Hermes-coach/issues/1) | **aberto** | 0 |
| 2 | feature | Notificações de treino (Telegram → e-mail/WhatsApp) | [#2](https://github.com/valdelin/Hermes-coach/issues/2) | **aberto** | 1 |
| 3 | feature | ~~Treinos sem medidor de potência (outdoor/FC: FTHR, hrTSS, %FTHR/RPE)~~ **implementado e issue fechada** (v0.0.16, modo FC %FTHR+RPE; validado 23/09 — 202 testes e 25/09 contra a API real — target HR) | [#3](https://github.com/valdelin/Hermes-coach/issues/3) | **implementado e issue fechada** | 2 ✅ |
| 4 | feature | ~~Ativar sync de wellness~~ **implementado e issue fechada** (RHR/sono no `info`; HRV sem suporte no FR935) | [#4](https://github.com/valdelin/Hermes-coach/issues/4) | **implementado e issue fechada** | 0 ✅ |
| 5 | feature | ~~Tipos de plano de treino (`GOAL`)~~ **implementado e issue fechada** (v0.0.9) — 7 tipos + `RACE_DATE`/tapper + variedade | [#5](https://github.com/valdelin/Hermes-coach/issues/5) | **implementado e issue fechada** | 2 ✅ |
| 6 | feature | ~~FTP sugerido a partir de treinos não agendados~~ (prova/treino livre) **implementado e issue fechada** (v0.0.15, `ftp-scan`: best-20min × 0,95 com gates + confirmação) | [#6](https://github.com/valdelin/Hermes-coach/issues/6) | **implementado e issue fechada** | 2 ✅ |
| 7 | produto | Casca estilo Runna: PWA + onboarding por objetivo + assinatura | — | **aberto** | 3 |
| 8 | produto | Multi-atleta / modo treinador (dashboard por atleta) | — | **aberto** | 4 |
| 9 | feature | **Perfil de esforço-alvo no `GOAL=race`** (estilo "Athlete Type" do Xert: Rouleur/TT/escalador) — ajusta a distribuição de focos dentro do mesmo objetivo | — (benchmark 22/09) | **possível — validar c/ treinador** | 2 |
| 10 | feature | **Nível do atleta** (iniciante/intermediário/avançado) como ajuste fino de volume/intensidade — hoje o TSB já calibra | — (benchmark 22/09) | **possível — validar c/ treinador** | 2 |
| 11 | produto | **Catálogo de eventos estilo Pillar** (200+ provas) — onboarding por prova-alvo (distância/perfil) | — (benchmark 22/09) | **possível — validar c/ treinador** | 3 |
| 12 | produto | **App comercial de ciclismo indoor** (posicionamento + preços — benchmark 22/09): consolidar #7/#8/#11 em produto com assinatura (tiers solo/coach), notificações (#2), catálogo de eventos e retenção | — (benchmark 22/09; ADR-003) | **possível — validar c/ treinador** (ROTEIRO-TREINADOR seções 3-4) | 3 |
| 13 | produto | **Assistentes de IA no padrão Tredict** — análise do histórico e criação de planos via LLM (MCP server / apps ChatGPT/Claude) como interface do motor; o nosso é determinístico/auditável (diferencial de confiança), o deles é LLM aberto | — (benchmark Tredict 23/09) | **possível — validar c/ treinador** | 3 |
| 14 | decisão | **W′/CP — referência analítica opcional.** A análise Tredict (mai/2026) reforça a baixa acionabilidade de W′-balance para endurance. CP/W′ permanecem disponíveis para estudo e contexto, sem roadmap de integração prescritiva. | — (benchmark 23/09; reposicionamento 03/10) | **sem roadmap ativo** | — |
| 15 | feature | **Wellness objetivo no alerta de sobrecarga** — dados coletados das plataformas via Intervals (Google Fit: peso, RC em repouso, sono, SpO2, tensão arterial, hidratação, kCal, gordura corporal; Garmin: + pontuação/qualidade do sono, VO2max, HRV rMSSD, passos) complementando o alerta `TSB ≤ −10` do Expected PMC. **Não é RPE/"como se sentiu"** (RPE continua âncora do modo FC — ver `docs/GLOSSARIO.md`); S2S (23/09): métricas de recuperação detectam overreaching | — (Science to Sport 23/09) | **possível — validar c/ treinador** | 1 |
| 16 | feature | **TSB-alvo pessoal de prova** — aprender o TSB ótimo de corrida correlacionando os melhores dias de forma com o TSB do dia (S2S: ótimo varia, `−5..+5` a `+10..+20` por atleta); usar para ajustar o taper do `GOAL=race`. **Semente implementada (v0.0.20)** no `GOAL=race`: o `build` projeta o TSB no dia da prova (Expected PMC) e compara com a faixa `−10..+20` (`_tsb_race_verdict`: cansado/ok/acima); falta o aprendizado pessoal | — (Science to Sport 23/09; Friel case study 2010) | **semente implementada — aprendizado pessoal: validar c/ treinador** | 2 |
| 17 | feature | ~~**Indicadores de zona extrema no Expected PMC**~~ **implementado (v0.0.19)**: Friel — `TSB < −30` = risco alto (R&R), `> +25` = transição (descanso longo); `forecast_pmc()` etiqueta a zona por dia (`_tsb_zone`) e o `model` avisa | — (Joe Friel 23/09) | **implementado** | 2 ✅ |
| 18 | feature | **Módulo de corrida a pé (esporte #2)** — `sport` no domínio (plan.json/workouts/eventos), limiar por pace/LTHR, `rftp-scan`, carga via Intervals (rTSS/gCTB), workouts de corrida em FIT, metas 5K/10K/meia/maratona (estilo RunDot), **PMC único multi-esporte** (TSS de todos os esportes no mesmo CTL/ATL — abordagem tri). Fora de escopo: passada/forma, Stryd/RunPower. **Prescrição SEM power meter** (protótipo `src/plan_run.py`): variável de controle é **p/ template**, não global — contínua/longa = `hr` (%LTHR; estado estável), tempo/limiar/VO2 = `pace` (ritmo-alvo do rFTP, FC como âncora), **fartlek = `rpe`** (surto < 2' nunca alcança a zona de FC; prescreve esforço "ritmo 5-10K"); sem `RFTP_PACE`, alvo `pace` cai p/ `hr`. Atleta escolhe no build; **decisão final: validação c/ treinador** (quando usar cada controle) | — (análise 23/09) | **possível — validar c/ treinador** | 2 |
| 19 | feature | **`recovery` — retorno a forma** (prazo realista + prescrição segura de rampa): varre **todo** o histórico real do Intervals (paginação com hiatos), reconstrói o PMC por dia (EWMA 42/7; zero nos hiatos para o decaimento não comprimir o tempo) e compara o hoje com o pico histórico (CTL, melhor mês, TSB). Estima semanas/meses para voltar a 90%/99% do CTL de pico sob rampas conservador/realista/otimista e entrega a rampa semanal de TSS com deload a cada 4 sem e teto = carga que sustenta o CTL-alvo (`src/recovery.py`; CLI `recovery`). **`build --recovery` (conexão ao build, 24/09)**: o plano dos próximos dias é orçado pelos tetos semanais da rampa (`--ramp-pts`, `--recovery-weeks`; também no `all`)~~ + **PMC real do Intervals + rampa calibrada (27/09)**: série ancorada nos `icu_ctl`/`icu_atl` reais (fallback reconstrução) e teto em TSS do plano via `calibrated_state` (teto = vol atual × pico/atual, ex.: 130 TSS/sem) | — (análise 23/09 — seu histórico real; 27/09 — alinhado) | **implementado (v0.0.21) + build conectado (24/09) + alinhado ao Intervals (27/09)** — validar a rampa c/ treinador | 2 |
| 20 | feature | ~~**`summary` — resumo dos treinos feitos por período**~~ (dia/semana/mês, janela terminando no dia-ancla, default ontem): sessões, carga total (TSS), tempo, distância, elevação, potência média/NP e FC média ponderadas pelo tempo + detalhe de cada treino; usa só atividades pareadas (`src/activity_summary.py`; CLI `summary --period --date`). **+ Períodos flexíveis (25/09):** `quarter`/`semester`/`year` (90/180/365d), duração livre `45d`/`6m`/`1y`, `plan` (primeiro→último dia do plano salvo = relatório final do ciclo) e `custom` (`--start`/`--end`); PMC acompanha a janela do período (piso 90d) | — (pedido 24/09 — "resumo do dia, semana, mes"; 25/09 — 6 meses/ano/fim do plano/custom) | **implementado (v0.0.22 + 25/09)** | 2 ✅ |
| 21 | feature | ~~**Gráficos no `summary`** (estilo Pillar "Advanced Progress Tracking"/Analog 90-day dashboards): **PMC CTL/ATL/TSB trailing 90d** em sparklines unicode (escala global compartilhada) + **barras de carga semanal** (TSS/semana ISO); `--chart auto\|none\|pmc\|load\|all` (default `auto` = PMC sempre + carga p/ semana/mês; `src/charts.py`); **`--export` para HTML/PDF** (SVG inline via `src/report.py`; PDF = mesmo HTML no chromium headless `--print-to-pdf`)~~ + **tema no relatório** (`src/brand.py`: 22 temas inspirados no Omarchy quattro; menu "Temas"/tecla T no HTML, `--theme` na CLI) e **linha de forma (TSB) por zona** (risco ≤ −10 / ideal / fresco ≥ +10, cores por tema)~~ + **alinhado ao Intervals (27/09, v0.0.29)** — PMC do gráfico parte dos valores REAIS `icu_ctl`/`icu_atl` de cada treino (`coach.real_pmc_by_day`) com decaimento EWMA entre os dias (`recovery.pmc_series_anchored`): mesmo número que o Intervals plota (CTL 25.3 vs ~15.8); reconstrução local de zero vira fallback | — (benchmark Pillar/Analog 24/09; alinhamento 27/09) | **implementado (v0.0.23 + alinhado 27/09)** | 2 ✅ |
| 22 | feature | **"Próximo passo" pós-treino** — post-ride insight → ação clara única (estilo Analog Sports "clear next action"; ex.: "amanhã: recuperação — cargas caíram, TSB vira +"...): ainda sob análise se vira `summary`/`reconcile` enrichment | — (benchmark Analog Sports 24/09) | **possível — validar c/ treinador** | 2 |
| 23 | produto | **Portal do sistema + teste real de inscrição de outros atletas** — casca do produto (login/OAuth Intervals + onboarding por objetivo) pronta para receber um **2º atleta de verdade**: criar conta, conectar o Intervals, gerar plano e ver publicar no calendário dele; validar o fluxo ponta-a-ponta (não só o motor) num futuro não muito distante | — (decisão 24/09) | **aberto — futuro próximo** | 3 |
| 24 | infra | **Modelagem de Banco de Dados Multi-tenant (PostgreSQL)** — Substituição do estado local (`plan.json`) por banco de dados relacional para gerir usuários, credenciais criptografadas (*AES-256*), estado dos treinos e assinaturas | — (arquitetura SaaS 25/09) | **planejado (SaaS)** | 1B |
| 25 | backend | **Encapsulamento em API REST (FastAPI)** — Transformação dos comandos da CLI e do motor determinístico em endpoints assíncronos REST | — (arquitetura SaaS 25/09) | **planejado (SaaS)** | 1B |
| 26 | backend | **Fila de Execução Assíncrona (Redis + Celery)** — Substituição da execução diária via Cron local por workers distribuídos que processam a autorregulação isolada de cada atleta cadastrado | — (arquitetura SaaS 25/09) | **planejado (SaaS)** | 1B |
| 27 | produto | **Gateway de Pagamento & Subscrições (Stripe / Paddle)** — Suporte a planos recorrentes (B2C Pro Athlete / B2B Coach), Trial de 14 dias e gestão automatizada de cobrança | — (arquitetura SaaS 25/09) | **planejado (SaaS)** | 3B |
| 28 | feature | **Race Recon — leitura do percurso da prova** (GPX/FIT ou rota do Intervals.icu): mede cada subida sustentada, estima o tempo nelas no ritmo de prova, favorece intervalos com esse tamanho nas semanas finais e planeja o dia da prova segmento a segmento (alvo de potência/pace + estoque de carboidrato/água) | — (benchmark IntervalCoach 26/09) | **possível — validar c/ treinador** | 2 |
| 29 | produto | **Coach+ — chat com o treinador de IA** (explicar decisões, mover/reescrever sessões no calendário; foto/screenshot na versão Max) — o nosso agente CLI já conversa e reescreve; falta a casca de produto | — (benchmark IntervalCoach 26/09) | **possível — menor prioridade** | 3 |
| 30 | feature | **Multi-esporte com carga compartilhada** (ciclo + corrida + natação + tri + força + HYROX num plano só, PMC único) — expandir o módulo de corrida (#18) para os demais esportes | — (benchmark IntervalCoach 26/09) | **possível — sem urgência** | 2 |
| 31 | feature | ~~**`check` — prontidão do dia**~~ (wellness + sinais de recuperação): RHR acima da média +3 bpm, HRV < 80%, sono < 6h ou 2h abaixo, readiness < 60 → **sugere** (nunca impõe) troca por recuperação Z2 curta (`--apply`); alerta de início de doença (RHR 2+ noites subindo + HRV caindo) + aviso ao treinador via `COACH_WEBHOOK` | — (benchmark IntervalCoach 26/09) | **implementado (v0.0.27)** | 0 ✅ |
| 32 | feature | ~~**Periodização selecionável (`PERIODIZATION`)**~~ — 5 modelos (polarized, pyramidal, undulating, linear, block) com templates por TSB; **decisão do usuário (26/09): TSB governa** (sem `PERIODIZATION` no `.env`); comando `periodization` (v0.0.28) explica os modelos/sugere por GOAL/TSB | — (benchmark IntervalCoach 26/09) | **implementado (v0.0.27/28)** | 2 ✅ |
| 33 | feature | ~~**Motor local do `model` alinhado ao Intervals**~~ — investigado em 27/09 e **resolvido via bootstrap presente**: a pipeline interna do Intervals não é reproduzível por EWMA simples sobre o `icu_training_load` (carga efetiva ~2×, campos `icu_*` da API); reconstruir a trajetória do passado diverge (CTL −10.9/ATL −29.7). O `cmd_model` agora parte do estado atual do Intervals (`latest_metrics`) — diferença ±0.0, confirmando 1:1 o TSB que o `build`/`reconcile`/`push` usam. Recriar a pipeline fica no **#34** | — (sessão 27/09 — divergência Motor local vs Intervals) | **implementado (v0.0.29, bootstrap presente)** | 0 ✅ |
| 34 | feature | **Recriar a pipeline de carga do Intervals no motor local** — como o `icu_ctl`/`icu_atl` da API é calculado internamente pelo Intervals (carga efetiva ~2× o `icu_training_load`; `strain_score`, NP, constantes `ctl_days`/`atl_days` configuráveis do atleta), bater sem bootstrap exigiria baixar streams de potência de todos os treinos e replicar a matemática deles (frágil a mudanças e a configurações da conta). **Decisão 27/09: não fazer agora** — o bootstrap presente já dá o diagnóstico 1:1; reabrir se quisermos TSB independente do Intervals ou diagnósticos sem a API | — (sessão 27/09 — análise do ~2×) | **decisão: adiado — SUPERSEDED** (bootstrap #33 vigente; reabrir somente para TSB independente do Intervals) | 2 |
| 35 | validação | **Consistência com dados de outros atletas** — a divergência Motor local vs Intervals (carga ~2×) e a solução de bootstrap/ancorar nos `icu_ctl`/`icu_atl` (#33/#21 v0.0.29) foram validadas na conta do próprio usuário (1 atleta, ~5 semanas de retorno). Para confiar que o modelo Carrega/Decai igual para qualquer perfil (outdoor/NP, sem power meter/FTHR, atleta treinando há anos com CTL alto, periodização por blocos), inscrever **ao menos um 2º atleta de verdade** no fluxo real do portal (#23) e conferir: (a) gráfico local ancorado ≈ Intervals, (b) decisões de foco/TSB coerentes, (c) bootstrap presente sem divergência ao longo do tempo | — (27/09 — "precisamos de dados de outros atletas") | **aberto — depende do portal (#23) testar com 2º atleta** | 3 |
| 36 | bug | **Orçamento semanal inflado em ~1,4× (`cap × 7`)** — o teto da janela rolante de 7 dias era `cap diário × 7`, mas `avg_load` é a média **por dia de treino**; multiplicar por 7 concedia 7 sessões numa semana de 5 dias. Corrigido para `cap × len(training_days)` (287 → 220 TSS); `weekly_budget()` virou a única fonte (o `cap * 7` hardcoded no `build_plan` foi removido). Em paralelo, `avg_load` passou a contar só sessões **realizadas** (`paired_activity_id` presente): carga prescrita nunca executada não é evidência de tolerância (média 44,1 → 47,1). Achado adicional: mesmo com o teto fiel, o template `ftp-builder` produz ~217 no pico (folga de 1,4% do teto), ou seja **é o template que limita a prescrição, não o teto** | — (sessão 01/10 — "recalibração deveria respeitar o volume semanal") | **implementado (v0.0.30)** | 0 ✅ |
| 37 | bug | **Treino perdido por substituição binária em vez de absorção pelo orçamento** — o `reconcile` inseria "recuperação" e reduzia −5% no próximo Limiar para **qualquer** falta, sem distinguir a natureza do treino perdido (inclusive quando o perdido era o próprio active recovery). Corrigido: a carga não feita é **redistribuída** nos treinos Z2/SweetSpot posteriores com folga no teto (`_absorb_missed_into_budget`), limitada pelo teto e não por fator arbitrário. **O que não se compensa:** active recovery (o propósito é *não* gerar carga) e Limiar/VO2máx (a adaptação vem da intensidade acima do LT1, não de volume — fica como "débito" para o `build` repriorizar pelo TSB real). Detalhado em `docs/EMBASAMENTO-CIENTIFICO.md` §5 (Seiler, Friel) | — (sessão 01/10 — "1 treino perdido pode virar recuperação?") | **implementado (v0.0.30)** | 0 ✅ |
| 38 | bug | **`push` nunca varria órfãos além do horizonte do plano** — `newest` era derivado do **último dia do plano**, então eventos `hermes-plan-*` de um plano anterior **mais longo** nunca entravam na busca de órfãos e sobreviviam indefinidamente (o `--dry-run` reportava "0 órfãos" em silêncio). Caso real: 16 eventos de 16/10 a 06/11 (incluindo o **Ramp Test de 22/10**, `ftp_test_date`) sobraram de um plano de 20 dias quando o atual tinha 14. Corrigido com varredura em **duas camadas**: a busca é ampla (`start + 120d`) só para **enxergar** o que existe, mas só se **apaga** o que está **dentro** do horizonte do plano; além do horizonte é reportado como mantido. Sem essa distinção, um plano mais curto apagaria o plano mais longo legítimo | — (sessão 01/10 — duplicatas no calendário após `push`) | **implementado (v0.0.30)** | 1 ✅ |
| 39 | bug | **Duplicatas manuais no calendário não eram removíveis** — eventos criados direto no app do Intervals têm `external_id = None`, e `orphan_external_ids` filtra por `EXTERNAL_ID_PREFIX` **e** o `bulk-delete` só aceita `external_id`; logo, um treino manual que repetia um dia do plano (ex.: `VO2max 2026-10-14` vs `Treino de Sweet Spot`) coexistia para sempre sem caminho de limpeza. Adicionado `IntervalsClient.delete_event(id)` (`DELETE /events/{id}`) e `plan.manual_duplicate_ids()` (detecta manual sem `external_id` cujo dia existe no plano), ligado ao `push` com relatório no `--dry-run`. **Precedência:** evento do Hermes vence sobre o manual do mesmo dia; evento manual em dia **sem** treino no plano **não** é duplicata e é preservado | — (sessão 01/10 — "trate das duplicatas manuais") | **implementado (v0.0.30)** | 1 ✅ |
| 40 | refactor | **Idempotência do `reconcile`** — `absorbed_ids` é **reconstruído a cada execução** dentro de `_absorb_missed_into_budget()` e não é persistido em `plan.json`. Efeito: o mesmo treino perdido pode ser absorvido repetidamente em execuções sucessivas do timer (`daily_reconcile.sh`), elevando `on_sec` a cada run até bater no teto — a absorção não é convergente. Correção: persistir os `external_id` já absorvidos na meta do plano e pulá-los, tornando `reconcile` idempotente | — (sessão 01/10 — revisão pós-release; **implementado 07/10 — auditoria**, commit `3fe9ec9`, publicado em v0.0.36) | **implementado (v0.0.36)** | 1 ✅ |
| 41 | limpeza | **`by_id` não utilizado em `_absorb_missed_into_budget()`** — mapa `by_id` é montado e populado mas nunca consultado na função (dead code). Remover junto da #40, ambos tocam a mesma função | — (sessão 01/10 — revisão pós-release; **implementado 07/10 — auditoria**, `by_id` removido no mesmo `3fe9ec9`) | **implementado (v0.0.36)** | 0 ✅ |
| 42 | docs | **Fonte única do embasamento científico** — a tabela Z1–Z7 e as ressalvas por zona passam a viver **só no vault** (documento canônico); `docs/EMBASAMENTO-CIENTIFICO.md` no repo vira o **contrato algorítmico** (o que o código faz e por quê, em seção/fórmula) e passa a apontar para o vault. Elimina uma divergência real: o arquivo do repo **prometia** uma "Tabela Científica Z1–Z7" que não continha, enquanto `ZoneIntegrityTest` e comentários em `src/` o citavam como origem da tabela. Seções 1–3 do repo reescritas (descreviam o algoritmo antigo: Ter/Qui/Sáb fixo, redução 5–25%, corte de 10% por IF alto); §6 antiga (blocos SweetSpot/VO₂máx) removida por redundante e por usar "vVO₂max", terminologia que o documento canônico **rejeita** explicitamente para ciclismo; nova §6 espelha a do vault (invariante `ZONE_BANDS`) | — (sessão 01/10 — "o repo e o vaultdevem ser a mesma fonte") | **implementado (v0.0.31)** | 0 ✅ |
| 43 | arquitetura | **Contrato de carga de treino** — separar TSS executado por potência (`NP`/`FTP`), TSS estimado do treino planejado, carga externa e interna. `power_training_load()` só calcula TSS após execução com NP/FTP válidos; sem essas medidas, inclusive em segmento ≤30 s, retorna desconhecido em vez de inferir NP. `icu_training_load` permanece autoritativo para CTL/ATL/TSB. | — (sessão 01/10 — P0-01) | **implementado (v0.0.32)** | 0 ✅ |
| 44 | arquitetura | **Separar periodização de TSB** — `TrainingPlanState` explicita goal, fase, semana/ciclo, cargas, TSB e readiness. `GOAL`/prova definem fase e alvo semanal; TSB < −15 ou readiness desfavorável adaptam só a primeira sessão de qualidade para Z2. Galán-Rioja et al. (2023) contextualiza a periodização; os limites são heurística do sistema. | — (sessão 01/10 — P0-02) | **implementado (v0.0.33)** | 0 ✅ |
| 45 | arquitetura | **Fases de treino explícitas** — `TrainingPhaseEngine` com `BASE`/`BUILD`/`SPECIFIC`/`PEAK`/`RECOVERY`/`TEST`, duração e critérios configuráveis por fase. Transições são regras de plano, não sequência fisiológica universal. | — (sessão 01/10 — P0-03) | **implementado (v0.0.34)** | 0 ✅ |
| 46 | decisão | **Progressão de estímulos** — `ProgressionEngine` só avança a sequência após `CompletionScore` bem-sucedido; `PARTIAL` repete, `FAILED` reduz. Heurística de plano. | — (sessão 01/10 — P0-04) | **implementado (v0.0.34)** | 0 ✅ |
| 47 | analise | **Distribuição de intensidade por tempo efetivo** — `IntensityDistributionEngine` reporta minutos LOW/MOD/HIGH por semana; modelos `POLARIZED`/`PYRAMIDAL`/`THRESHOLD_HEAVY`/`CUSTOM` são rótulos, sem 80/20 presumido. | — (sessão 01/10 — P1-01) | **implementado (v0.0.34)** | 0 ✅ |
| 48 | dominio | **Perfil fisiológico** — `AthletePhysiologicalProfile` com marcadores opcionais e `FtpSource`/`FtpConfidence`; FTP-only é válido e nada é inferido a partir dele. | — (sessão 01/10 — P1-02) | **implementado (v0.0.34)** | 0 ✅ |
| 49 | dominio | **Estado de adaptação** — `AdaptationState` com seis domínios, contribuição por estímulo, decaimento e saturação. Heurística computacional. | — (sessão 01/10 — P1-03) | **implementado (v0.0.34)** | 0 ✅ |
| 50 | decisão | **TrainingDecisionEngine** — compõe objetivo, fase, adaptação, carga, readiness, progressão, dose e segurança em decisão com `rationale` e `confidence`. | — (sessão 01/10 — P1-04) | **implementado (v0.0.34)** | 0 ✅ |
| 51 | decisão | **ReadinessAssessment multimodal** — HRV vs baseline, RHR tendencial, sono, fadiga, carga, performance e consistência; cor = adequação ao treino; sinal isolado não cancela sessão. | — (sessão 01/10 — P1-05) | **implementado (v0.0.34)** | 0 ✅ |
| 52 | dominio | **Critical Power / W′** — `CriticalPowerProfile` + ajuste `P = CP + W′/t` apenas com dados suficientes; CP/W′ complementam o FTP e não o substituem. **Fase 2 concluída:** `source`, `model`, n/min/max/span de duração, `fit_r2`/`fit_rmse` e confidences informativas separadas para CP/W′. Perfil inválido fica sem confidence; todo perfil válido fica `LOW` nesta fase, sem thresholds arbitrários para `MEDIUM`/`HIGH`. Não há consumidor prescritivo, fallback FTP nem ativação em VO2, zonas, TSS, INTENSITY, work_sec, repeats ou recovery. | — (01/10 P2-01; Fase 2 02/10, `509487e`) | **implementado — Fase 2 concluída** | 0 ✅ |
| 53 | feature | **Gerador estruturado VO2max** — `VO2Workout` com `interval_duration`, `repetitions`, `work_power_range`, `recovery_duration`, `recovery_power`, `total_work_time`, `progression_step` e `lever`, em três famílias; escadas por dimensão via `progression_ledger()`; `Z5_CEILING` impede o degrau de intensidade de atravessar para Z6. **Nenhuma estrutura de protocolo é superior** (NMA de 19 publicações, 240 atletas, todas as comparações não significativas) — os templates são formatos configuráveis, não recomendações de eficácia. | — (sessão 02/10 — P2-02) | **implementado (v0.0.35)** | 0 ✅ |
| 54 | feature | **Intenção e dose por família** (`src/zone_intent.py`) — `FamilyProfile` para `ENDURANCE`/`SWEET_SPOT`/`THRESHOLD` com `intent`, `dose`, `dose_shape`, `levers`, `not_claim` e `criterion`. **Sobreposição explícita**: `sweetspot` (84–97%) e `threshold` (91–105%) se cruzam em 91–97% FTP; `classify()` levanta `AmbiguousIntensity` nessa faixa em vez de escolher pelo número. Bandas vêm de `ZONE_BANDS` e não são redefinidas. | — (sessão 02/10 — P2-03) | **implementado (v0.0.35)** | 0 ✅ |
| 55 | docs | **Embasamento científico reestruturado** — 15 seções classificadas (`EMBASAMENTO CIENTÍFICA` / `HEURÍSTICA DO SISTEMA` / `MODELO COMPUTACIONAL`), índice, sem superlativo sem base comparativa; 5 autores e 2 PMIDs conferidos contra o abstract no NCBI (Düking corrigido: **34489178**, não 34469178); seção 14 de limitações; contrato testado por 19 testes documentais. | — (sessão 02/10 — P2-04) | **implementado (v0.0.35)** | 0 ✅ |
| 56 | teste | **Suíte de regressão científica** (`tests/scientific/`) — 228 testes em nove módulos, um por contrato algorítmico: training load (22), periodização (20), progressão (24), readiness (19), adaptação (20), FTP (34), CP/W′ (39), VO2max (24) e distribuição de intensidade (26). Cada docstring declara se a asserção é evidência, heurística ou modelo. Expôs quatro divergências doc↔código, registradas em #57. | — (sessão 02/10 — P3-01; Fase 2 CP/W′) | **implementado** | 0 ✅ |
| 57 | docs | **Correção de quatro divergências doc↔código** expostas por #56 — §11 (as quatro transições de `SEQUENCES` que quebram a regra de dimensão única, e a escada não ser caminho para subir potência), §12 (`MIXED_TEMPLATES` não muda duas dimensões em todo degrau; lever `INTENSITY` inerte na faixa padrão), §10 (`decay()` sem teto superior), §3 (OLS enviesado no `estimate_cp`). Nenhuma mudança de comportamento: em todos os casos o código é coerente com a intenção e era o texto que superdeclava. Quatro entradas novas em §14 + trava de teste date-dependent em `test_plan.ReconcileTest`. | — (sessão 02/10 — P3-02) | **implementado (v0.0.35)** | 0 ✅ |
| 58 | decisão | **Integração de módulos isolados no fluxo publicado.** Fase 1 concluída: `zone_intent` é guardrail semântico derivado de `focus` em `build_plan`, sem schema, migration ou alteração prescritiva (`364bb03`). `readiness_assessment` também chega ao fluxo diário por `check --apply`. Os oito módulos restantes seguem sem consumidor em `build`/`push`; a integração deles continua decisão de escopo, pois `plan.json` e os valores de `focus` são contratos publicados. | — (02/10 decisão de escopo; 03/10 Fase 1 zone_intent) | **parcial — primeiro guardrail integrado** | 0 |
| 59 | decisão | **Quatro limites de implementação** — todos documentados em §14 com trava de teste. **Resolvidos em 02/10:** (a) `SEQUENCES` × regra de dimensão única (§11) — a aritmética da §11 estava errada (afirmava volume total constante; real −16,7%/+6,7%/+50%) e foi corrigida; `SEQUENCES` **não** foi alterado, por decisão de escopo, e o trabalho absoluto por degrau agora é trava de teste (`test_delta_de_trabalho_total_das_excecoes`). (b) lever `INTENSITY` inerte na faixa padrão (§12) — `generate()` agora levanta `ValueError` quando a faixa não tem folga abaixo de `Z5_CEILING`, em vez de devolver degrau mudo; a faixa padrão **não** foi abaixada, porque subir acima do teto geraria Z6 rotulada como VO2max. **Pendentes: (c) e (d) foram extraídos para o item 60.** | — (sessão 02/10 — rastreio de §14 lim. 9–12); (a) e (b) resolvidos 02/10 (`b0e7368`, `b4f1695`); (c)/(d) → item 60 | **parcial — (a) documentado, (b) resolvido** | 0 |
| 60 | decisão | **Auditoria científica e arquitetural concluída.** Os três módulos continuam isolados, sem consumidores produtivos em `plan.py`/`training_plan.py`: não alteram workout publicado, TSS, intensidade, duração, zonas, calendário ou payload. (a) `decay()`: **corrigir futuramente** como invariantes de entrada/normalização de engenharia; implementação pendente. (b) CP/W′ OLS: **pesquisar mais** para qualidade da referência analítica, mantendo Fase 2 informativa e sem uso prescritivo; quality gates não criam roadmap de Fase 3. (c) `intensity=0.90`: **manter placeholder isolado**; decisão por família e reconciliação com `ZONE_BANDS` antes de integração. | — (03/10 — auditoria #60; 811 testes, 0 falhas, 3 skips; **localizado em 07/10 — auditoria**, linha deslocada para a tabela) | **auditoria concluída — follow-ups pendentes** | 0 |
| 61 | revisão | **Revisão do orquestrador local (`scripts/hermes_agent.py`, AGENT-0)** — code review do script entregue no PROMPT 66 (08/10) antes de virar interface oficial consumida pelo OpenCode/Hermes Agent: (a) segurança — ausência de `shell=True`/`exec`/`eval`, `raw` limitado ao `training_plan.py`, cwd fixado no root; (b) paridade das flags com o argparse real de `src/training_plan.py` (incl. divergência registrada: `recovery` expõe só `--weeks`/`--ramp-pts`); (c) cobertura de confirmação dos mutáveis (`today --apply`, `build`, `all`, `push`, `daily`, `vault-sync`) e semântica de `--yes`; (d) comportamento do modo interativo (aliases, falha sem derrubar a sessão, Ctrl+C/EOF); (e) robustez dos testes (`tests/test_hermes_agent.py` — 32 testes com mock de `subprocess.run`). HOWTO em `docs/HOWTO-HERMES-AGENT.md`; suíte 1451 testes OK | — (08/10 — PROMPT 66) | **aberto — aguardando revisão** | — |

## Prioridade operacional atual (2026-10-02)

**[ENGENHARIA] CP/W′ Fase 2 — CONCLUÍDA.** Estimativa, proveniência, metadados, métricas de fit e confidence informativa estão completos como capacidade analítica. FTP continua o baseline operacional universal; CP/W′ não têm consumidor prescritivo. Fase 3 não tem roadmap ativo e integração prescritiva não é planejada no momento.

**[ENGENHARIA] #40 + #41 — CONCLUÍDOS EM CÓDIGO (auditoria 07/10 → status atualizado).** A recomendação "próximo trabalho" desta linha ficou superada: `absorbed_ids` agora **persiste** na meta do `plan.json` e o `reconcile` é idempotente (commit `3fe9ec9`, publicado em v0.0.36); o `by_id` morto foi removido no mesmo commit. O próximo trabalho de código volta a ficar em aberto para decisão separada.

**[ENGENHARIA/PRODUTO] #58 — FASE 1 CONCLUÍDA.** `zone_intent` é guardrail semântico derivado de `focus` no build, sem alterar schema ou prescrição. Os demais módulos isolados continuam exigindo contrato e decisão explícita antes de publicação.

**[EVIDÊNCIA + ENGENHARIA] #60 — AUDITORIA CONCLUÍDA.** `decay()` terá correção futura apenas como invariante de engenharia; CP/W′ OLS permanece informativo e requer pesquisa de protocolo/quality gates antes de qualquer uso prescritivo; `intensity=0.90` permanece placeholder isolado até haver contrato por família. Nenhuma implementação prescritiva foi autorizada.

**[ENGENHARIA/PRODUTO] Rationale.** Priorizar bugs que afetam plano publicado antes de ativar módulos científicos isolados; #58 requer contrato antes de código; #60 requer revisão científica. CP/W′ só será reconsiderado para integração produtiva diante de caso de uso concreto em que FTP seja insuficiente ou CP/W′ demonstre benefício claro, exigindo nova avaliação científica, arquitetural e de produto.

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
- **Duas decisões abertas da linha algorítmica (itens #58 e #59).** Ambas
  acontecem aqui porque não são features: são escolhas de escopo sobre
  trabalho já feito.
  - **#58 — integrar os 10 módulos de P0–P3 ao `build`/`push`?** Eles são
    contratos testados e não afetam a publicação. Enquanto a resposta for não,
    o ganho de P0–P3 para o atleta é zero, e isso deve estar explícito.
    Integrar um de cada vez, começando pelo de maior efeito sobre o plano
    (`training_phase` ou `zone_intent`), porque `plan.json` é contrato
    persistido e os valores de `focus` são publicados no Intervals.
    - **Passo A implementado e conectado ao fluxo diário: `readiness`.**
      Corrigidos na revisão 2: a redução não devolvia orçamento aos dias
      seguintes, e uma leitura podia degradar a mesma sessão em builds
      sucessivos — agora ela vale só para o dia que descreve.
      **Revisão 3 (§15):** a leitura de hoje nunca era acionada, porque `build`
      começa o plano amanhã e a sessão de hoje é preservada. Agora o
      `check` roda no script do timer systemd (`check --apply` antes de
      `reconcile` e `push`), usa o mesmo motor do `build`, só toca a sessão se
      ela ainda não começou (concluída → preservada; estado desconhecido →
      propõe e não aplica), e separa proposta / aplicação local / publicação.
      Evidência: `tests/test_readiness_today.py`, 21 casos pelo dispatcher real.
      O timer do sistema saiu de 00:00 para **05:30**, depois da sincronização
      do wellness e antes da sessão das 07:30 — a 00:00 a etapa rodava sem dado
      do dia.
      **Limitação:** sem fuso horário; a chegada do wellness é variável.
      Detalhes, política, evidência e lacunas em
      `docs/SPEC-passo-A-readiness.md`. **A #58 continua aberta:**
      `training_phase`, `zone_intent` e os demais módulos seguem isolados, e
       `readiness_assessment` tem capacidade de 3/7 eixos; a cobertura diária
       varia conforme HRV/RHR/sono estejam válidos no registro de wellness.
  - **#59 — corrigir os quatro limites de implementação de §14?** Todos mudam
    comportamento de prescrição, então nenhum deve entrar como efeito colateral.
    Recomenda-se decidir por ordem de impacto no plano: (a) regra de dimensão
    única e (b) lever de intensidade inerte afetam prescrição de verdade;
    (c) teto de `decay()` e (d) estimador de CP são robustez de modelo.

### Fase 1 — Comunicação (issue #2) & Arquitetura SaaS Core
- Resumo do treino (foco + TSB + TSS previsto/real + avisos do reconcile) via
  **Telegram** primeiro; interface `Notifier` extensível (e-mail/WhatsApp);
  config `NOTIFY_CHANNEL`/token/chat id no `.env`.
- Regra: envio **assíncrono e não-bloqueante** (não derruba o timer diário).
- **Fase 1B (Evolução Multi-tenant):**
  - Migração de estado (`plan.json`) para **PostgreSQL** (tabelas `Users`, `Credentials`, `Workouts`).
  - Criptografia simétrica (*AES-256*) para armazenar as API Keys do Intervals.icu de múltiplos atletas.
  - Exposição do motor via **FastAPI** e fila de workers com **Redis + Celery** para processar o `reconcile` diário em escala.

### Fase 2 — Dados incompletos (issue #3) + tipos de plano (#5) + FTP sugerido (#6)
- ✅ **Sem medidor de potência (issue #3) — implementado (v0.0.25, validado
  contra a API real)**:
  `FTHR` no `.env` (`parse_fthr`/`get_fthr`); `build --no-power` carimba
  `hr_mode` nos workouts e o `push` envia `target: HR` com texto em
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
- 📊 **Benchmark (2026-09-22) — tipos de training plan (Xert, Pillar, TriDot,
  RunDot)** — verificar se o mercado tem "tipos de plano" a copiar. **Achado:
  nenhuma usa catálogo estático tipo Zwift; todas são adaptativas por
  objetivo/evento:**
  - **Xert**: XATA (recomendação diária adaptativa) e XFAI (plano orientado a
    evento/objetivo); "Athlete Type" (Rouleur/TT) como perfil de esforço-alvo;
    sem planos pré-definidos ("the smartest plan is the emptiest").
  - **Pillar**: filosofia anti-plano-genérico; plano **personalizado por
    objetivo/agenda**, **200+ eventos** (Event Goals) + taper automático;
    multi-sport.
  - **TriDot**: por **distância de prova** (sprint → Olympic → 70.3 → full) +
    camadas (Lifestyle 1 prova / Essentials 3 / Complete ilimitado).
  - **RunDot** (running, FitLogic/TriDot): por **distância de corrida** (5K,
    10K, meia, maratona) + base building; via número único (VDOT).
  - **Conclusão:** as escolhas do hermes já refletem o padrão de mercado
    (`GOAL` por perfil de prova + `race` com `RACE_DATE`/taper = "plano por
    evento"; `ftp-scan` = threshold sem teste protocolado). **Não adicionar
    novos `GOAL` agora.** Evoluções candidatas (backlog #9-#11), **validadas
    com o treinador** no ROTEIRO-TREINADOR (seção 1, perguntas 9-12): perfil de
    esforço-alvo no `race`; catálogo de eventos (Fase 3); nível do atleta como
    calibração fina (TSB já cobre).
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

### Fase 3 — Produto (casca estilo Runna, ADR-003) & Monetização
- PWA + onboarding por objetivo → `build` → calendário → Zwift (`.zwo`) +
  assinatura mensal; login com API key do Intervals.
- **Parcialmente iniciado no agente (v0.0.10–0.0.11):** onboarding por objetivo
  (menu GOAL de 7 tipos) + troca de objetivo no meio do plano + disponibilidade
  (`WEEKLY_HOURS`/`LONG_DAY`). Falta a casca (PWA, tela de seleção, assinatura).
- **Fase 3B (SaaS & Monetização - itens #23, #27):**
  - Portal do sistema (Next.js/React) para onboarding de atletas sem tocar em CLI.
  - Conexão de gateway de pagamento (Stripe/Paddle) com tiers **Pro Athlete (B2C)** e **Coach/Studio (B2B)**.
- 📊 **Benchmark comercial (22/09) — o agente pode virar app pago?** **Sim** — o
  núcleo já entrega o que o mercado vende: planos adaptativos por objetivo
  (GOAL + `race`/taper = Pillar/TriDot), treino sem medidor de potência
  (FTHR/%FTHR/RPE = Xert HRDM, TriDot "power meter not required"), threshold
  sem teste protocolado (`ftp-scan` = Xert "What's My FTP", TriDot
  auto-threshold), execução medida no reconcile (≈ TrainX/Pillar "interval
  detection"). **Vantagem competitiva: automação ponta-a-ponta** (plano →
  calendário → reconcile + timer diário) que nenhum deles tem — os concorrentes
  exigem app/ação manual. **Preços de referência (2026):** Xert US$8,33/mês
  (anual) ou US$14,99 mensal; Pillar App ~US$7,99/mês (trial 30d); TriDot
  Lifestyle US$14,99 (1 prova curta), Essentials US$39 (3 provas), Complete
  US$99 (ilimitado), **Premium-Coached US$249/mês** (treinador dedicado);
  RunDot ~US$9,99/mês. ⇒ **solo amador cabe em US$8–15/mês (~R$ 45–80)**;
  **multi-atleta/treinador é onde o valor sobe** (valida a Fase 4).
  **Gap para virar produto:** casca UI/PWA (#7), cobrança/assinatura,
  notificações (#2), multi-atleta (#8), catálogo de eventos (#11), app nativo,
  comunidade; **decisão:** caminho já traçado (#7→#8→#11) — adicionar à Fase 3 a
  **camada de preços** (tiers solo/coach validados com o treinador,
  ROTEIRO-TREINADOR 3.6) e métricas de retenção.

### Fase 4 — Multi-atleta / modo treinador
- Dashboard por atleta, parâmetros por atleta, aprovação antes de publicar,
  alertas e relatório semanal. Depende da validação com treinador.

- 📊 **Benchmark (2026-09-23) — Tredict** — concorrente conceitual mais
  próximo. Plataforma de planejamento + análise (corrida/ciclismo/natação/
  triathlon) com **previsão de forma** ("redundant effort calculation" ≈ nosso
  Expected PMC), **detecção automática de FTP/LTHR** (≈ `ftp-scan`/#6),
  **conexão coach↔atleta** (≈ Fase 4/#8), venda de planos e **integrações de
  device** (Garmin Training API, Coros, Wahoo, Suunto, Zwift, Hammerhead,
  Watchletic, Withings). **Desde 2026 adota IA no mesmo sentido da Fase 3**:
  MCP server + apps ChatGPT/Claude que analisam histórico, estimam FTP e
  **escrevem treinos que sincronizam no relógio** (backlog #13). **Lições:**
  (1) **Expected PMC/TSB validado** — previsão de forma é o core deles
  (múltiplas fontes de carga ⇒ não simplificar o nosso p/ métrica única);
  (2) **independência de fornecedor = posicionamento deles** — capitalizam a
  aquisição **Garmin→TrainingPeaks (jul/2026)** como "end of vendor
  independence" ⇒ reforça o seam `AthleteContext` (Fase 0) e o OAuth: o nosso
  produto sobrevive à troca de provedor, o deles É o provedor;
  (3) **W′/CP** — post "Why Tredict does not calculate W-Prime" (mai/2026)
  recusa W′-balance por instabilidade/baixa acionabilidade para endurance ⇒
  CP/W′ ficam como referência analítica opcional, sem consumidor prescritivo e
  sem roadmap ativo de integração (item #14);
  (4) **preço p/ coaches**: "prepaid credits for write access" (créditos por
  escrita) — opção de monetização a validar na Fase 3;
  (5) **posicionamento**: Tredict resolve "onde guardo/analiso/sincronizo"; o
  Hermes resolve "quem pensa/planeja" ⇒ caminho (cérebro sobre o Intervals)
  segue defensável; Tredict vira **benchmark vivo** das Fases 2-3.

- 📊 **Benchmark (2026-09-23) — Joe Friel + Science to Sport (TSB/CTL/ATL)** —
  duas referências de ciência do treino que **justificam decisões e mudanças**
  no sistema:
  - **Joe Friel — "Managing Training Using TSB"**
    (https://joefrieltraining.com/managing-training-using-tsb/): define 5 zonas
    de TSB para **gerenciar** treino — risco alto `< −30` (overreaching; ficar
    poucos dias, R&R depois), ótimo `−30..−10` (maior estímulo de treino),
    cinza `−10..+5` (planalto: recuperação/taper/volta), frescor `+5..+25`
    (pronto p/ prova / qualidade), transição `> +25` (fim de temporada).
    **O que justifica:** (a) o mapa de "foco do dia" por TSB é a mesma lógica
    dele — sem mudança; (b) nossas bordas são simplificação (4 faixas vs 5):
    **backlog #17** adiciona indicadores de zona extrema (`< −30`/`> +25`) ao
    Expected PMC; (c) a ressalva "zonas variam por atleta" reforça a
    parametrização existente (FTP/FTHR/GOAL/horas) e o **#16** (TSB-alvo
    pessoal).
  - **Joe Friel — "Case Study: Periodization for First A Race of Season"**
    (https://joefrieltraining.com/case-study-periodization-for-first-a-race-of-season/):
    caso real (WKO+) de periodização até a 1ª prova A — macrociclo
    Transition→Prep→Base→Build→Peak→Race; **ATL é bem mais sensível que CTL**
    (fitness só sobe se a carga gera fatigue); **Build** empurra TSB bem
    negativo com CTL/ATL subindo, fechando com semana de R&R; **Peak** = treino
    tipo-prova a cada 72h + 2 dias fáceis (TSB oscila em torno de 0 por 2
    semanas); **Race week** = leve com intensidade alta **decrescente**,
    limitando a **perda de fitness a ≤10%** enquanto descarrega fatigue.
    **Alvo de forma no dia da prova ~+20 TSB** (acertou +19,7 e venceu a
    categoria). Ressalva: **forma alta sem prova à vista = ruim** (descarrega
    fitness à toa; converse com a nossa zona `transition > +25` #17 — lá o
    recado é "descanso longo", no dele é "volte a construir"). **O que
    justifica:** **#16** (TSB-alvo pessoal — dá um alvo concreto de prova) e um
    reforço do **`GOAL=race`/taper** (o `_taper_focus` atual é simplificação —
    só 3 dias Z2; o dele é R&R + race week com intensidade decrescente e teto
    de perda de fitness).
  - **Mike Posthumus — "Monitoring Cyclist Training Load Part 1"** (Science to
    Sport/UCT, https://www.sciencetosport.com/monitoring-training-load/):
    **valida o modelo EWMA 42/7** já usado pelo engine
    (`impulse_response.py`); defende monitorar **aderência** ao plano
    (implementado na v0.0.18, `adherence`); mostra que input **subjetivo**
    (RPE/"how do you feel") pode detectar overreaching mais cedo que métricas
    de potência; CTL/TSB ótimos são **individuais** (CTL 70→140; TSB de prova
    `−5..+5` a `+10..+20`). **O que justifica:** **#15** (wellness objetivo —
    métricas das plataformas — no alerta de sobrecarga) e **#16** (TSB-alvo de
    prova aprendido por correlação).

- 📊 **Benchmark (2026-09-24) — Pillar + Analog Sports (Ana)** — dois
  concorrentes de coaching com perfil oposto n/as reviews:
  - **Pillar** (_trainwithpillar.com_): 4,9★ App Store; **Adaptive
    Performance** com **200+ eventos** (Event Goals), taper na temporada de
    provas, freshness **multi-esporte**, interval detection, conexões
    Zwift/Garmin/Wahoo/TrainingPeaks e tema constante nas reviews (fórum
    TrainerRoad): "pular/remodelar sessões sem ficar para trás" (plano
    adaptativo). **Lições:** (a) o `summary` com gráficos (#21) espelha o
    "Advanced Progress Tracking" deles; (b) catálogo de eventos já é o
    backlog #11; (c) **progressão adaptativa ao perder treino** é o nosso
    `reconcile` (recuperação/limiar reduzido) — validar c/ treinador.
  - **Analog Sports (Ana)** — dev **Analog AI** (Abu Dhabi; time que usa:
    UAE Team Emirates XRG/ADQ), `io.analog.sports.ana` no Play Store. App
    Store **2,6★/5 (7 avaliações, todas negativas)**: "doesn't really sync
    data", "AI interface weird and slow", "Unresponsive UI... annoying
    voice", "slow, unresponsive, repetitive"; reviews citam ainda **privacy
    policy ampla / entidade nos Emirados** como dealbreaker. **Produto, se
    funcionasse:** dashboard de **90 dias** de form/fitness/fatigue (PMC),
    HRV/RHR/CTL/ATL/TSB, post-ride insights → "clear next action", chat IA
    em 32 idiomas, conexões Garmin/Wahoo/WHOOP/Oura/Ultrahuman/TrainingPeaks/
    Zwift, wellness score (sono+stress+humor). **Lições:** (a) **falha de UX/
    performance e sync derrubam o app mesmo com IA boa** — reforça o nosso
    motor **determinístico/auditável** como diferencial (backlog #13:
    LLM como interface, nunca como núcleo); (b) **os gráficos PMC de 90 dias
    são valor percebido** — que é exatamente o #21; (c) "clear next action"
    pós-treino vira backlog #22; (d) wellness score mapeia o #15; (e)
    **privacidade/terminais é posicionamento**: self-host/Intervals/CLI é
    vantagem de confiança.
  - **Contraste útil p/ validação com o treinador:** UI/IA rica com reviews
    ruins (Analog 2,6★) vs UX simples com reviews ótimas (Pillar 4,9★) ⇒ o
    caminho do hermes (CLI determinístico, robusto, audável) está alinhado
    com para onde o mercado apontaria, e a casca (#7) deve priorizar
    **robustez/valor percebido** (gráficos, aderência, automação) sobre
    enfeites de IA.

## Regras transversais

- Toda implementação exige **testes** e docs (README/CHANGELOG/vault) no mesmo
  commit.
- Mudanças que afetam carga/plano passam por **`--dry-run`** ou validação com
  dados reais antes de tocar o fluxo do timer diário.

## Status atual (2026-09-26)

Benchmark competitivo + decisões da sessão (features 1/3/4 implementadas;
2/5/6 no backlog; implicações estratégicas em `docs/PITCH-DECK.md`):

- **Benchmark (26/09): IntervalCoach (intervalcoach.app)** — coach de IA
  multi-esporte sobre o Intervals.icu, 4,8★/194 avaliações, Free/Pro €3/mês/
  Max €8/mês. Diferenciais deles: ajuste diário por recuperação (60+ sinais),
  Race Recon, detecção de doença, 5 modelos de periodização, Coach+ (chat) e
  multi-esporte com carga compartilhada. Lições: **preço de referência mais
  baixo que o estimado** (€3–8 vs US$8–15 do slide 4 — ver PITCH-DECK), e a
  **recuperação diária vira feature esperada**, não extra. Nosso edge se
  mantém: motor determinístico (R$0, auditável) + base fisiológica
  documentada + visão B2B coach.
- **Decisões do usuário (respostas 1-7):** (1) ajuste diário por recuperação
  **SIM, não obrigatório** — atleta decide; (2) Race Recon → **#28**;
  (3) alerta de doença **SIM** + aviso opcional ao treinador via
  `COACH_WEBHOOK`; (4) modelos de periodização **SIM**; (5) Coach+ → **#29**,
  menor prioridade; (6) multi-esporte → **#30**, sem urgência; (7) implicações
  estratégicas no **PITCH-DECK** (seção benchmark competitivo).
- **Implementado hoje (#31 `check` — prontidão do dia, v0.0.27):** `training_plan.py check`
  lê wellness (RHR/HRV/sono/readiness), avalia os sinais (`src/readiness.py`:
  RHR acima da média +3 bpm, HRV < 80% da média, sono < 6h ou 2h abaixo,
  readiness < 60), **sugere** (nunca impõe) trocar o treino de hoje por
  recuperação Z2 curta; `--apply` aplica no `plan.json` (depois `push`).
  **Alerta de início de doença** (RHR 2+ noites subindo + HRV caindo → aviso
  na tela) e, com `COACH_WEBHOOK` no `.env`, aviso ao treinador
  (`coach_alert_payload`; não-bloqueante).
- **Implementado hoje (#32 — periodização, v0.0.27):** `PERIODIZATION` no
  `.env` seleciona 1 de 5 modelos (`src/plan.py::PERIODIZATION_TEMPLATES`):
  polarized | pyramidal | undulating | linear | block — cada um com templates
  por TSB (mesmo mecanismo do `GOAL_TEMPLATES`); `build`/`all` aplicam o modelo
  quando configurado (com prioridade sobre o GOAL na distribuição de focos).
  **Decisão do usuário: por ora o TSB governa (sem `PERIODIZATION` no `.env`).**
- **Adicionado (v0.0.28, explicação para o atleta):**
  `training_plan.py periodization` (módulo `src/periodization.py`) lista os
  5 modelos em linguagem de atleta (o que significa, o que se sente na
  prática, com que perfil combina), sugere o melhor para o GOAL/TSB atual
  (fadiga alta → `undulating`; fresco → `linear`/qualidade) e detalha um
  modelo com `--model NOME` + afinidade com o objetivo. Não altera nada;
  serve para o treinador/atleta decidir com base em explicação.
- Suíte: **354 testes OK (3 skipped)** incluindo `tests/test_readiness.py`
  (sinais, doença, sugestão, payload do treinador, periodização) e
  `tests/test_periodization_explain.py` (13 testes do comando `periodization`).
  Lembra que a **decisão atual é deixar o TSB governar** (sem `PERIODIZATION` no
  `.env`); o comando `periodization` existe para consulta/oferta ao atleta.
- **Decisões de UX do portal (26/09; #23):** aprovação **obrigatória** antes de
  publicar (vale para `build` **e** `reconcile`; solo = atleta, com coach =
  treinador); **sem chat** — interface por **ações/opções pré-definidas**
  (chat/LLM fica para o futuro, #29); **Dashboard só com o essencial** (resumo
  do dia + semana + alertas; detalhes no Calendário). Registradas em
  `docs/PORTAL-UI-DESIGN.md` (Fase 0/1).
- **Análise (27/09): Motor local do `model` diverge do Intervals** porque a
  pipeline interna do Intervals usa carga ~2× o `icu_training_load` (visto nos
  eventos reais: transição 29.1→54.3 de ATL com loads 54/57/49/57 exige carga
  efetiva ~110; `strain_score` 60.5 e `joules` 417900 num treino de 52min).
  Janela/zeros/cold-start não explicam a divergência — o **#33** foi então
  resolvido via **bootstrap presente** (motor local parte do estado atual do
  Intervals; diferença ±0.0 no `model` v0.0.29) e a recriação da pipeline
  ficou registrada no **#34** (adiada). Não afeta `build`/`reconcile`/`push`,
  que usam as métricas do Intervals como autoritativa.
- **Hiato de 2 anos (27/09):** EWMA tem memória exponencial — após 30d sem
  treino o CTL cai à metade (τ=42) e o ATL a ~1% (τ=7); após 2 anos ambos vão a
  ~0. O zero pós-hiato é fisiologicamente correto (memória de treino expira) e
  não explica a divergência. **Cadeia de proteção contra lesão:** a decisão do
  treino (foco por TSB julgado no `build`/`reconcile`/`push`) usa **só** as
  métricas do Intervals (`latest_metrics`), idênticas às do painel dele; o
  modelo local (gráficos/diagnóstico) quando erra, erra **para menos**
  (rampas/recovery mais conservadoras = viés de segurança). Alinhar o gráfico
  do `summary` (abaixo) é uma melhoria de diagnóstico, não de segurança.
- **Implementado hoje (#21 alinhado ao Intervals, v0.0.29):** o PMC do gráfico
  do `summary` agora **ancora nos valores reais** `icu_ctl`/`icu_atl` que a API
  devolve em cada treino feito (`coach.real_pmc_by_day`) e decai EWMA 42/7
  entre os dias (`recovery.pmc_series_anchored`) — plotando o **mesmo número
  do Intervals** em vez da reconstrução local de zero (CTL 25.3 vs os antigos
  ~15.8 no período atual; fim da série 26/09 = 25.34, último real 25/09 25.95
  decaído 1 dia). A reconstrução local (`pmc_series` sobre `actual_daily_load`)
  vira **fallback** quando a API não traz os valores (ex.: clientes de teste).
  Também vale para `--export` (HTML/PDF). **#35** registra a validação com um
  2º atleta de verdade. Comparação numérica e explicativa das duas abordagens
  em `docs/COMPARACAO-PMC.md`.
- Suíte: **369 testes OK (3 skipped)** (27/09), incluindo
  `PmcSeriesAnchoredTest` (5), `RealPmcByDayTest` (3) e cobertura do
  `_summary_chart_data` preferindo real/fallback no `SummaryChartDataTest`.
- **Decisões pendentes do portal (antes/durante a Fase 1):** P1 o que acontece
  se não houver aprovação até o treino (publica com aviso? fica pendente?);
  P2 aprovar na fila dedicada vs inline no calendário; P3 notificação de
  pendência (badge/Telegram — #2); P4 profundidade Dashboard vs Calendário
  (validar com protótipo); P5 catálogo de ações pré-definidas da v1; P6 quando
  entra o chat/Coach+ (#29) e se começa como perguntas pré-formatadas;
  P7 protótipo navegável do Dashboard (validar P2/P4/P5 na tela — outra
  sessão; não bloqueia a Fase 0). **Design do portal: seguir o visual dos
  relatórios HTML** (`src/report.py`/`brand.py`: 22 temas do Omarchy, default
  tokyo-night, cards, barra de TSS, linha de forma por zona — kit em
  `docs/TEMAS.md`); registrado em `docs/PORTAL-UI-DESIGN.md`.

## Status atual (2026-09-27)

Revisão dos itens (sessão de 27/09; fix do #33 no `recovery`/`build --recovery`):

- **#21 já alinhado ao Intervals (v0.0.29)** — ver histórico acima (PMC do
  `summary` ancorado nos `icu_ctl`/`icu_atl` reais; comparação em
  `docs/COMPARACAO-PMC.md`).
- **#19 recuperado do modelo antigo (27/09):** o `recovery` (CLI) e o
  `build --recovery` ainda reconstruíam o PMC de zero sobre `icu_training_load`
  (carga ~½ da efetiva do Intervals) — CTL 9.8/pico 23.9 vs os reais
  24.7/32.0. Agora consomem a **mesma série ancorada** do `summary`
  (`_pmc_rows`: `real_pmc_by_day` + `pmc_series_anchored`, fallback na
  reconstrução local) e **calibram a rampa** para a moeda de TSS do plano
  (`recovery.calibrated_state`: teto = volume atual × CTL pico / CTL atual —
  não `pico × 7`, que misturaria a escala ~2× do Intervals com o TSS do plano;
  ex.: 100 × 32/24.7 ≈ **130 TSS/sem**). Valores de pico/melhor-mês/TSB
  reportados agora são os do Intervals; a saída exibe o CTL calibrado em
  "TSS/semana no plano".
- Suíte: **374 testes OK (3 skipped)** (27/09). Validação real: `recovery`
  reporta CTL 24.7/ATL 40.8/TSB −16.1, pico 32.0 em 2022-02-28;
  `build --recovery` ora pelo teto calibrado.

Revisão dos itens (sessões de 23-25/09; suporte a SaaS estendido):

- **Implementados:** #16 (semente TSB-alvo no `race`), #17 (zonas extremas no
  Expected PMC), #19 `recovery` (v0.0.21), #20 `summary` (v0.0.22), **#21
  gráficos + relatório (v0.0.23)**.
- **#21 publicado (v0.0.23):** `src/charts.py` (PMC 90d + carga semanal) e
  `src/report.py` (`--export` HTML/PDF com SVG); **temas** (`src/brand.py`:
  22 temas do Omarchy quattro; menu "Temas"/tecla T no HTML, `--theme` na CLI
  — com o `:root` do padrão emitido antes dos `[data-theme]` no CSS para
  nenhum tema ser sobrescrito) e **linha de forma (TSB) por zona** (risco ≤
  −10 / ideal / fresco ≥ +10). **274 testes OK**; validado no chromium:
  22/22 temas com as 3 cores de zona corretas. Kit portátil dos temas:
  `docs/TEMAS.md`.
- **Benchmark (24/09):** Pillar (4,9★; plano adaptativo, cadastro 200+ eventos)
  e Analog Sports Ana (2,6★ App Store; 90-day PMC dashboards, IA chat, mas
  sync/UX ruim) → **#21** implementado, **#22** (clear next action) no
  backlog; lição de UX/robustez registrada na Fase 4.
- **#19 conectado ao build (v0.0.24, 24/09):** `build --recovery` ora o plano
  pelos tetos semanais da rampa do `recovery` (`--ramp-pts`, `--recovery-weeks`;
  também no `all`) — release v0.0.24 publicada.
- **Abertos / Roadmap SaaS (#24-#27, 25/09):** incorporadas as tarefas de
  infraestrutura multi-tenant, migração para PostgreSQL, criação de endpoints
  FastAPI, agendamento Redis/Celery e camada de pagamentos Stripe.
- Suíte: **278 testes OK** (24/09).

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
- **Benchmark tipos de plano (22/09)**: Xert/Pillar/TriDot/RunDot **não usam**
  catálogo estático — todas adaptativas por objetivo/evento; nossas escolhas
  (`GOAL` + `race`/taper + `ftp-scan`) já seguem o padrão. **Novas entradas de
  backlog #9-#11** (perfil de esforço no `race`, catálogo de eventos, nível do
  atleta) marcadas como **"possível — validar c/ treinador"**; perguntas 9-12
  adicionadas ao ROTEIRO-TREINADOR seção 1 (vault).
- **Benchmark comercial (22/09) — app pago?** **Sim, viável.** O núcleo já
  entrega o que Xert/Pillar/TriDot vendem (planos por objetivo, sem potência,
  threshold sem teste) + automação ponta-a-ponta que eles não têm. Preços de
  referência: solo **US$8–15/mês** (Xert, Pillar, RunDot; TriDot entry
  US$14,99), multi-atleta/coach **US$99–249/mês** (TriDot Complete/Coached).
  **Nova entrada #12** (app comercial: tiers solo/coach + retenção) marcada
  como **"possível — validar c/ treinador"**; detalhe na Fase 3.
  ROTEIRO-TREINADOR 3.6 ganha a âncora de preços de mercado.


## UI Foundation (platform-independent)

> **Nota:** Este bloco consolida a reconciliação da auditoria de desacoplamento UI/plataforma (UI-0 concluído anteriormente). Priorização: P0 arquiteturais antes de heurísticas (PMC-1/POL-1). Não altera prescrição.

| ID | Item | Prioridade | Status | Dependências | Origem |
|---|---|---|---|---|---|
| UI-1 | Application seam + adapters de config/plano + redução de dependência `get_client()` | **P0** | **DONE** | — | UI-1 (reconciliado) |
| UI-2 | Lifecycle local + `HermesWorkoutId` | **P0** | **DONE** | UI-1 | UI-2 |
| UI-3 | Provider capabilities + `IntervalsAdapter` + normalização DTOs (provider boundary) | **P0** | **DONE** | UI-1, UI-2 | UI-3 |
| UI-4 | Completion local + snapshot normalizado + sync freshness | **P0** | **DONE** | UI-2, UI-3 | UI-4 |
| UI-5 | ApplicationState/PlanView + contratos DTO/View | **P1** | **DONE** | UI-1 (+ UI-3/UI-4) | UI-5 |
| RDY-1 | Readiness View + separação dados/heurísticas/policy | **P1** | **DONE** | UI-5, PMC-1 | Reconciliação |
| PMC-1 | `form_pct` derivado (view-only). `form_pct = (TSB/CTL)*100` se CTL>0; None caso contrário. CTL/ATL/TSB normalizados; sem efeito prescritivo automático | **P1** | **DONE** | UI-1/UI-3 (normalização PMC) | Reconciliação |
| POL-1 | Policy advisory `form_pct <= -30%` (configurável, default -30%, advisory-only, não axioma fisiológico universal; sem deload automático) | **P2** | **DONE** | PMC-1, RDY-1 | Reconciliação |
| HR-1 | CTL ramp rate (janela/limites, heuristic) | **P2** | **DONE** | PMC-1 | Futuras heurísticas |
| STREAM-1 | Normalized activity streams boundary | **P2** | **DONE** | UI-3/UI-4 | Dependência técnica HR-2 |
| STREAM-2 | Heart rate stream confirmation + temporal alignment | **P2** | **DONE** | STREAM-1 + evidência provider | Dependência técnica HR-2 |
| HR-2 | Pw:HR/aerobic decoupling (metrica observacional com validade metodologica explicita) | **P2** | **DONE** | STREAM-1 + STREAM-2 | Contexto steady/aerobico permanece explicitamente unverified |
| HR-3 | HRV / RHR (FCR em PT-BR) (heuristic, baseline individual) | **P3** | **DONE** | Provenance/freshness | — |
| HR-4 | Sleep + subjective wellness (observado) | **P3** | **PARTIAL** | Provenance/freshness | Aguardando decisão treinador; pesquisar provider só para sinais aprovados |
| TEST-1 | Estabilizar `IntegracaoCliTest::test_saida_avisa_quando_a_leitura_nao_foi_aplicada` (era date-fragile: o fixture criava wellness até D+1, então a decisão ancorava no 1º dia do plano). Falha pré-existente desde `931fe16`; **não** corrigido em PMC-1 (§26) | **P3** | **DONE** | — | PMC-1 §25/§27 |

**UI-1 — estado real (03/10/2026): DONE.** `src/application.py` expõe a fachada `Application` (config adapter `load_env`/`get_env`, plan adapter `load_plan`/`load_plan_meta`/`save_plan` delegando ao módulo `plan`, e `client()` com provider injetável via `client_factory`) e os casos de uso do ciclo de vida do plano: `build_workouts`, `reconcile_workouts`, `push_workouts`, `summarize_period`, `recovery_outlook` (rampa `compute_return_ramp`) e `assess_daily_readiness`. O composition root da CLI é `_make_app()` em `training_plan.py`; os handlers `build`, `reconcile`, `push`, `summary`, `recovery` e `check` agora só parseiam args, chamam o caso de uso (provider + serviços de domínio injetados) e formatam a saída — nenhum handler chama `get_client()` diretamente (`grep -rn "get_client" src/` só aparece em `application.client()` e no próprio `get_client`). Casos de uso são chamáveis sem `argparse` e sem rede, cobertos por `tests/test_application.py` (provider fake). Os demais handlers (`info`, `ftp-check`, `model`, `periodization`, `adherence`, `ftp-scan`) permanecem adapters de diagnose/interativos sobre módulos de domínio já encapsulados (`wellness_summary`, `suggest_ftp_test`, `daily_tss_series`/`forecast_pmc`, `periodization`, `adherence_report`, `ftp_scan`); não carregam orquestração reutilizável e não foram içados (evita mover código só para bater métrica). Correção adjacente: `src/plan.py` não importava `zone_floor`/`zone_ceiling`/`ZONE_BANDS` no branch `try`, latente para execução top-level; corrigido e coberto por `tests/test_plan.py::PlanTopLevelImportTest`.

**UI-2 — estado real (03/10/2026): DONE.** Identidade local explícita (`HermesWorkoutId`) e lifecycle desacoplado do provider. `src/workout_identity.py` deriva UUIDv5 determinístico do dia (`uuid5(NAMESPACE_URL, "https://hermes-coach.local/workout")` + `day`), anexado ao campo `id`; `src/lifecycle.py` modela o estado declarado (`planned`/`postponed`/`substituted`/`cancelled`/`completed`/`missed`, default `planned`) e o observado (`derive` com data + evidência de execução), com `VALID_TRANSITIONS` e `validate_transition`. `Application.load_plan`/`save_plan` enriquecem em memória de forma idempotente (planos antigos recebem o mesmo id em toda leitura e estabilizam no próximo save; campos aditivos). Novos métodos de Application: `get_workout`, `workout_lifecycle`, `derive_workout_lifecycle`, `set_workout_lifecycle`, `postpone_workout`, `cancel_workout` — locais, sem rede e sem tocar no calendário do Intervals. Migração: `plan.adherence_report` passou a classificar via `lifecycle.derive`; `reconcile`/`_done_and_extra`/`session_execution_state` seguem usando `external_id`/`paired_activity_id` como linkage/evidência (documentado em `docs/UI-2-LIFECYCLE.md`). `reconciled` **não** é lifecycle: é o livro-razão de faltas absorvidas (`absorbed_ids`). Testes: `tests/test_workout_identity.py`, `tests/test_lifecycle.py` e `WorkoutLifecycleApplicationTest`/`BuildUseCaseTest` em `tests/test_application.py`. Suíte: **863 testes, 0 falhas, 3 skips**.

**UI-3 — estado real (03/10/2026): PARTIAL.** Boundary de provider explícito. `src/provider.py` define `ProviderCapability` (enum), a taxonomia de erro (`ProviderError`/`ProviderUnavailable`/`ProviderAuthError`/`ProviderOperationError`), os contratos `TrainingMetricsProvider`/`ActivityProvider`/`WorkoutSyncProvider` (o primeiro reusa o do UI-1, sem duplicar) e os records normalizados `TrainingEvent`/`WellnessSnapshot`/`ActivitySnapshot` (Mapping que preserva o payload original e expõe campos normalizados: `training_load`, `ctl`, `atl`, `tsb`, `ftp`, `resting_hr`, `sleep_secs`, etc.). `src/intervals_adapter.py` é o único ponto que conhece `icu_*`/HTTP: traduz respostas, declara capabilities e mapeia `IntervalsApiError` (agora com `.status`) para `ProviderError`. Composition root: `get_provider()` = `IntervalsAdapter(get_client())`, injetado por `_make_app()`. A Application não conhece `icu_*` (regressão coberta por teste) e usa records normalizados nos fluxos migrados; `IntervalsApiError`/`requests` não vazam. `IntervalsApiError` ganhou `.status` (aditivo). **DONE após UI-4 (04/10/2026):** o residual acima foi resolvido — o domínio determinístico passou a ler por `provider_fields` (nomes canônicos) e `grep -R "icu_ctl|icu_atl|icu_tsb|icu_training_load" src` não retorna nenhuma **leitura de código** fora de `provider_fields.py`/`intervals_adapter.py` (as demais ocorrências são prosa). Detalhes e auditoria em `docs/UI-3-PROVIDER-BOUNDARY.md`. Suíte: **920 testes, 0 falhas, 3 skips**.

**UI-4 — estado real (04/10/2026): DONE.** Três eixos separados: lifecycle local (UI-2), **completion evidence** (`workout["completion"]` com `source`/`observed_at`) e **sync freshness** (`SyncFreshness`). `Application` ganhou `mark_completed`, `completion_status`, `reconcile_completion`, `load_training_snapshot`/`save_training_snapshot`/`sync_freshness` e `sync_provider_state` + `SyncResult`. Matching `external_id ↔ dia` continua sendo descoberta, mas o resultado aponta para `HermesWorkoutId` antes de mutar estado local; estado declarado incompatível gera conflito preservado e `completed` segue terminal. Snapshot normalizado (`src/snapshot.py`) persiste em `training_snapshot.json` (arquivo separado do `plan.json`) com eventos/wellness canônicos e timestamp; leitura local não exige provider. Compatibilidade de leitura via `src/provider_fields.py` (mapa único de aliases legados → canônico) evita reescrever 70+ fixtures e mantém planos antigos. Backward-compatible (campos aditivos; snapshot ausente/corrompido → vazio; `absorbed_ids` mantido por `external_id`). Testes novos: `tests/test_provider_fields.py`, `tests/test_snapshot.py`, `tests/test_completion.py`. Detalhes em `docs/UI-4-COMPLETION-SNAPSHOT.md`.

**UI-5 — estado real (04/10/2026): DONE.** Contrato de leitura para consumidores independentes de UI. `src/ui_state.py` define DTOs imutáveis (`frozen=True`) com `to_dict()`: `ApplicationState`, `PlanView`, `WorkoutView`, `PlanMetaView`, `CompletionView`, `ProviderLinkView`, `SnapshotView`, `FreshnessView`. `Application` ganhou as queries puras `plan_view()` e `get_application_state()`. A View expõe `lifecycle_declared` vs `lifecycle_effective` (resolução `lifecycle.derive` com `today` injetado e evidência vinda do completion local, não do provider), `completed`, `CompletionView` (source/observed_at/activity_id), `ProviderLinkView` (linkage separado da identidade) e `conflict=True` quando há evidência de provider com estado declarado incompativel. Um conceito por representação: **não** existe `SyncView` (a idade da sync vive em `SnapshotView.freshness`, delegando a política ao `SyncFreshness` do UI-4 sem novo threshold). `ui_state.py` não importa `application`, `provider` nem `provider_fields` (só `lifecycle`), coberto por teste que tokeniza a fonte ignorando comentários. Queries são offline e read-only: não gravam plano/snapshot, não chamam provider e não alteram lifecycle (teste com `client_factory` que levanta + comparação byte a byte e mtime). `next_workout` é derivado, não prescritivo. `cmd_adherence` passou a consumir a View com `stdout` idêntico (única mudança: `plan.json` vazio passa a orientar `build` em vez de imprimir relatório vazio). Fora de escopo: `form_pct`, readiness, policy, heurísticas, UI/API. Testes: `tests/test_ui_state.py` (27). Suíte: **947 testes, 943 passed, 3 skipped, 1 falha pré-existente** (`tests/test_readiness_step_a.py::IntegracaoCliTest::test_saida_avisa_quando_a_leitura_nao_foi_aplicada`, já falhava no commit `931fe16`, anterior a UI-1; ver `docs/UI-5-APPLICATION-STATE.md` §11). Detalhes em `docs/UI-5-APPLICATION-STATE.md`.

**PMC-1 — estado real (04/10/2026): DONE.** `form_pct` (Form relativo = TSB/CTL × 100) exposto no contrato de leitura como derivação **pura** do Hermes. `src/ui_state.py` ganhou `derive_form_pct(ctl, tsb)` (divisão única; sem I/O, sem provider, sem recalcular PMC) e o DTO `PmcView(ctl, atl, tsb, form_pct, tss, ftp, day)`, que **substituiu** o dict `metrics` sem tipagem em `SnapshotView` — um conceito, uma representação. `None` (nunca 0) quando `ctl is None`, `tsb is None` ou `ctl <= 0`; float full, sem clamp e sem arredondamento (formatação é do consumidor). Provenance explícita: `ctl`/`atl`/`tsb` são **observados** do provider (UI-3), `form_pct` é **derivado** pelo Hermes. Snapshot stale **ainda** calcula `form_pct` (freshness informa idade, não bloqueia derivação — não existe regra "stale ⇒ None"). Sem snapshot, `snapshot is None` e não se cria objeto artificial. Nenhuma policy embutida: sem `form_pct <= -30`, sem labels, sem deload (POL-1). `form_pct` não existe no `IntervalsAdapter` nem no `provider.py` (garantido por teste). A CLI não foi alterada: `cmd_info`/`cmd_model` leem PMC ao vivo do provider e imprimi-la lá duplicaria o contrato — o produto aqui é o contrato `Application`/View. Detalhe conceitual em `docs/EMBASAMENTO-CIENTIFICO.md` §8 e `docs/GLOSSARIO.md`; detalhes de implementação em `docs/PMC-1-FORM-PCT.md`. Testes: `tests/test_pmc_form.py` (30). Suíte: **977 testes, 973 passed, 3 skipped, 1 known pre-existing failure, 0 new failures**.

**RDY-1 — estado real (04/10/2026): DONE.** `Application.get_readiness_view(today=..., now=...)` é uma query local, imutável e side-effect free sobre `TrainingSnapshot`: não chama provider/rede, não grava plano/snapshot, não altera lifecycle/completion/freshness, não imprime e não reconcilia. A API é deliberadamente separada de `ApplicationState`, pois readiness tem `target_day` próprio e executa a heurística existente; `reference_day` expõe qual leitura de wellness a heurística realmente descreveu (inclusive divergência D vs D+1, sem tentar corrigir TEST-1). `ReadinessView` separa `WellnessView` (observados canônicos: RHR, HRV/SDNN, sleep, readiness composto, stress), `PmcView` reutilizado (CTL/ATL/TSB observados + `form_pct` derivado), freshness/captured_at e resultado **heurístico existente** (`heuristic_level`, score, confidence, trace/sinais, illness/composite). Não expõe nem chama `ReadinessAction`/`readiness_decision`: advice e prescrição (`reduce`/`replace`/deload) continuam fora da View; POL-1 passou a ser advisory paralelo, sem alterar essa separação. Ajuste de compatibilidade: `readiness.py` aceita wellness canônico do snapshot por uma borda de normalização e recebeu `today=` opcional para `stale_days` determinístico, sem alterar thresholds ou fluxo CLI. Testes: `tests/test_readiness_view.py` (16; datas explícitas, offline, side effects, serialization, guardrails). Detalhes em `docs/RDY-1-READINESS-VIEW.md`. Suíte: **993 testes, 989 passed, 3 skipped, 1 known pre-existing failure, 0 new failures**.

**POL-1 — estado real (04/10/2026): DONE.** `src/form_advisory.py` define a policy isolada `evaluate_form_advisory(form_pct, threshold=-30.0)` e o DTO frozen `FormAdvisory`. Default centralizado e injetável: `-30%` é threshold **operacional/advisory**, não axioma fisiológico, diagnóstico ou regra de deload; threshold inválido (não-numérico, não-finito ou não-negativo) levanta `ValueError`. Estados mínimos: `unavailable` (form ausente/inválido), `normal` (`form_pct > threshold`) e `high_negative_form` (`form_pct <= threshold`, igualdade incluída). A Application expõe `get_form_advisory()` lendo apenas `PmcView.form_pct` do snapshot local; não recalcula ratio, não chama provider, não toca readiness heuristic, plano, lifecycle, completion, freshness, reconcile/push/check ou stdout. Snapshot stale não bloqueia o advisory; freshness segue no `ReadinessView` para apresentação. Coexistência é intencional: readiness GREEN e advisory de form negativo podem ocorrer sem resolução automática. Sem `ReadinessAction`/REDUCE/REPLACE/deload/cancelamento ou novas faixas. Detalhes em `docs/POL-1-FORM-ADVISORY.md`; testes em `tests/test_form_advisory.py` (15). Suíte: **1008 testes, 1004 passed, 3 skipped, 1 known pre-existing failure, 0 new failures**.

**HR-1 — estado real (04/10/2026): DONE.** O snapshot UI-4 já persiste eventos canônicos que podem conter CTL observado por dia e um `PmcView` datado; não há série diária garantida. HR-1 escolheu portanto a definição mínima e auditável `ramp_rate_7d = CTL(D) - CTL(D-7)`, em **pontos de CTL por 7 dias**, sem reconstruir CTL, interpolar gaps, nearest-prior ou converter ausência em zero. `src/ui_state.py` ganhou `derive_ctl_ramp_rate`, `ctl_history_by_day` e `CtlRampView` (tendência temporal separada de `PmcView` pontual, com target/baseline/valores observados/rate/freshness). `Application.get_ctl_ramp_view(target_day=..., window_days=7)` exige target explícito e funciona offline. `src/ctl_ramp_advisory.py` é policy opt-in separada: `get_ctl_ramp_advisory(..., max_ramp_points=...)`. Não há limite default (nem 5/7 arbitrário): o consumidor injeta um limite operacional finito/não-negativo; estados `unavailable`/`within_advisory_range`/`high_ramp`. A igualdade atinge advisory, mas não há `ReadinessAction`, deload/reduce/replace/cancel, mudança de plano ou policy composta com form/readiness. Snapshot stale não bloqueia cálculo; freshness fica visível na View. Limitação explícita: delta absoluto tem interpretação dependente do CTL basal (ex.: +6 em CTL 30 ≠ +6 em CTL 100). Detalhes em `docs/HR-1-CTL-RAMP-RATE.md`; testes em `tests/test_ctl_ramp.py` (19). Suíte: **1027 testes, 1023 passed, 3 skipped, 1 known pre-existing failure, 0 new failures**.

**STREAM-1 — estado real (05/10/2026): DONE.** `ProviderCapability.READ_ACTIVITY_STREAMS`, `ActivityStreamProvider`, `ActivityStreamPoint` e `ActivityStream` agora definem a leitura temporal agnóstica. O `IntervalsAdapter` normaliza somente os formatos confirmados `time` (offset em segundos) e `watts`; valida comprimentos, preserva zero/None, ordena tempos finitos sem agregar duplicatas e sinaliza `empty`/`missing_time`/`length_mismatch`/`invalid_time` sem interpolar. Streams ficam em `activity_streams.json`, cache separado de `training_snapshot.json`, chave `provider:activity_id`. `Application.fetch_activity_stream()` é remoto e explícito; `get_cached_activity_stream()` é local/offline/read-only. Não há capability HR nem nome bruto presumido para a API; portanto STREAM-1 não contém Pw:HR, split, eligibility, threshold, advisory ou prescrição. Detalhes em `docs/STREAM-1-ACTIVITY-STREAMS.md`; testes em `tests/test_activity_streams.py` (15).

**STREAM-2 — estado real (05/10/2026): DONE.** Pesquisa primária confirmou `heartrate` como stream armazenado e `fixed_heartrate` como variante corrigida. STREAM-2B consultou três VirtualRides reais sanitizadas: `time`/`watts`/`heartrate` tiveram comprimentos idênticos, `time` foi finito e monótono de 0 até moving time, e médias de `heartrate` arredondaram para `average_heartrate` dos resumos (forte evidência empírica de bpm). A fixture compacta preserva shape `{type,data}`, comprimentos originais e sete índices distribuídos sem dados identificáveis. `IntervalsAdapter` agora requisita/mapeia `heartrate`; `READ_HEART_RATE_STREAM` declara a capability. Mismatch retorna `heart_rate_length_mismatch`, sem truncar/interpolar; `fixed_heartrate` não é tratado como alias. Cache preserva HR e leitura STREAM-1 continua compatível. Detalhes/fontes em `docs/STREAM-2-HEART-RATE-STREAM.md` e `docs/research/STREAM-2-INTERVALS-HR-STREAM.md`; testes em `tests/test_activity_streams.py`.

**HR-2 — estado real (05/10/2026): DONE.** `src/pw_hr_decoupling.py` implementa fórmula TrainingPeaks-style (`EF = NP / FC média` por metade; `((EF1 - EF2) / EF1) * 100`) com sinal positivo para queda de EF. A escolha diverge da fórmula publicada pelo maintainer do Intervals.icu (`potência média / FC média`), portanto o resultado é Hermes-specific e não alega equivalência numérica com nenhum provider. Eligibility de dados e contexto metodológico são representados separadamente: gaps, duplicatas, missing e desalinhamento retornam razão explícita; amostras de 1 s contínuas são guardrail computacional para NP, não fisiologia. `PwHrDecouplingView.computable` pode ser verdadeiro enquanto `methodological_context="unverified"`: o Hermes não infere steady/aerobic effort, warm-up, intervalos, pausa, coasting, temperatura ou contexto individual sem dados defensáveis. `Application.get_pw_hr_decoupling()` é offline/read-only. Não há threshold, advisory, readiness/form/ramp integration ou prescrição; a conclusão explícita de não classificar automaticamente o contexto fecha HR-2.

**TEST-1 — estado real (05/10/2026): DONE.** A causa era o fixture, não o motor:
`assess_readiness_assessment` ancora a decisão em `ReadinessTrace.reference_day`
(último registro de wellness), e `build` começa o plano em D+1 — com registros
até D+1, a âncora caía no primeiro dia do plano e a leitura era legitimamente
aplicada, quebrando a asserção que promete "não aplicada". Correção restrita a
`tests/test_readiness_step_a.py`: a janela de wellness passa a **terminar em
D-1** (três registros, para a avaliação ter janela). `_readiness_applies_on` e
`_readiness_situacao` já estavam corretos — `dia_alvo_fora_do_plano` emite
`nao aplicada — leitura e de um dia fora do plano; nao foi transferida para
outra sessao`, que é exatamente o que o teste afirma. Nada em `src/` mudou: sem
seam novo, sem `--today`, sem clock abstrato, sem tocar em thresholds, ação,
policy ou saída de CLI, e sem relaxar as três asserções originais. A correção é
estrutural (D-1 nunca pertence ao plano), verificada freezing `date.today()` em
75 dias consecutivos — inclusive virada de mês e fim de semana: `nao aplicada` e
`nao foi transferida` presentes, `aplicada em` ausente em todos. Detalhes em
`docs/KNOWN_ISSUES.md`. Suíte: **1063 testes, 0 falhas, 0 skips**.

**HR-3 — estado real (05/10/2026): DONE.** HRV e RHR estão implementados como camada observacional local e offline: `HeartRateTrendView`/`HeartRateMetricTrend` em `src/ui_state.py` expõem, por sinal, valor observado, baseline individual (média da janela inclusiva), delta absoluto, delta percentual e `sample_count`; `Application.get_heart_rate_trend_view(today=..., window_days=7)` consome só o snapshot local — sem provider, sem stdout, sem escrita. Funções puras separadas: `_hr_metric` (rejeita `bool`, string não numérica, `NaN`, `inf` e zero — mais estrito que `_f`, que aceita `bool` e propaga `NaN`), `_hr_series` (sem interpolação), `derive_hr_baseline`, `derive_hr_delta`, `derive_hr_delta_pct` (`None` se baseline 0). Ausência é sempre `None`, nunca 0; freshness é reportado e **não** bloqueia, então dado stale ainda produz derivado. `reference_day` é o último dia com wellness de qualquer tipo — não o `target_day` e não o último dia de uma série específica. HRV **não mistura** `hrv` com `hrv_sdnn`: usa `hrv` se existe qualquer observação na janela, só cai para `hrv_sdnn` quando `hrv` está totalmente ausente, e declara a escolha em `hrv_field`. Estados explícitos: `available`, `insufficient_history`, `missing_current_value`. Nenhum advisory, policy, `ReadinessAction`, prescrição, auto-deload, threshold fisiológico universal novo, nem integração com POL-1 ou HR-2; as heurísticas `hrv_low`/`rhr_rising` seguem intactas em `readiness.py` com `HRV_LOW_RATIO = 0.80` e `RHR_RISE_BPM = 3.0`, e a suíte de readiness não muda. ****`FCR` resolvido (PROMPT 29):** decisão do responsável — `FCR` é *frequência cardíaca de repouso*, o termo PT-BR de `RHR`. Não é heart-rate recovery. Como alias terminológico, **não** ganhou campo: `HeartRateTrendView` expõe só `hrv` e `rhr`, dois sinais reais, sem duplicar o mesmo número sob dois nomes. O campo provisório `fcr_heart_rate_recovery` e o status `HR_TREND_UNSUPPORTED_FIELD` foram removidos (nenhum consumidor real além da própria View). *Heart-rate recovery* fica fora do escopo e sem backlog. **Bug computacional corrigido em PROMPT 28:** `_low_hrv` (`src/readiness.py:111`) mediava `rows` inteiro, incluindo o valor corrente na base contra a qual ele é comparado — a série `[60,59,58,57,56,45,44]` dava base 54.14 e `44 < 43.31` falso, mascarando uma queda de 27%. Passou a usar `rows[:-1]`, alinhando com `_rising_rhr`; `HRV_LOW_RATIO = 0.80` e a janela de 7 dias intactas. Isso é correção de seleção de amostras do baseline, não novo threshold fisiológico. Efeito: `hrv_low` passa a disparar onde não disparava, propagando para `Readiness.reason`, `suggest_swap` e o eixo `hrv_score`. `_illness` e `composite_low` não mudam — o primeiro tem lógica própria (`hrv_last < hrv_prev`), o segundo deriva de `readiness_low`. Detalhes em §11 de `docs/HR-3-HRV-RHR-TRENDS.md`; regressão em `tests/test_readiness.py::LowHrvBaselineContaminationTest` (15). Detalhes e limitações em `docs/HR-3-HRV-RHR-TRENDS.md`; testes em `tests/test_hr3_hr_trends.py`. Suíte: **1132 testes, 0 falhas, 0 skips**.

**Fundação de leitura para consumidores independentes (04/10/2026): concluída.** UI-1..UI-5 DONE. Isso significa apenas que **os contratos base existem** — não que a UI esteja pronta: nenhuma tela, endpoint HTTP ou `ApplicationState` consumido fora da CLI existe ainda.

**Dependências (visão geral):**
```text
UI-1
 ↓
UI-2, UI-3, normalização/Application contracts
 ↓
UI-4, UI-5, RDY-1, PMC-1
 ↓
POL-1
```

**HR-4 — estado real (05/10/2026): PARTIAL — aguardando decisão treinador/provider.**
O inventário auditado antes de qualquer edição (`docs/HR-4-SUBJECTIVE-WELLNESS.md`
§2) encontrou **quatro** conceitos com campo real em `/wellness` e **três** sem
nenhum: `sleep_secs` (segundos, unidade confirmada), `sleep_score`, `stress` e
`readiness` (composto do provider). `soreness`, `motivation` e `fatigue` **não
existem** em `src/` — nem no boundary, nem no snapshot, nem como alias — e
`mood` também não; `subjective_fatigue_score` é eixo do modelo que nunca recebe
dado porque RPE não chega em `/wellness`. HR-4 é **PARTIAL** porque falta a
decisão do treinador sobre quais sinais realmente usar e para quê; ausência no
provider não é bloqueio eterno: para cada sinal desejado haverá contrato
implementável ou decisão explícita `not used`/`provider unsupported`. A lacuna é
o resultado — não se criou campo, alias nem nome parecido para preencher a linha.

Implementado: `ObservedWellnessView`/`WellnessMetricView`/`WellnessMetricSpec`
em `src/ui_state.py`, com os sete conceitos sempre presentes
(`observed` / `missing_current` / `unsupported_field`) e
`Application.get_observed_wellness_view(today=..., window_days=7)` — local,
offline, read-only, sem provider, stdout ou escrita. O nome do contrato é
`Observed`, não `Subjective`, porque `sleep_secs`/`sleep_score`/`stress`/
`readiness` vêm do provider e os itens genuinamente subjetivos são justamente os
inexistentes.

Baseline e delta para `sleep_duration`, `sleep_score` e `stress`; **não** para
`provider_readiness`, que é composto de versão interna não estável. `delta` e
`delta_pct` ficam `None` com `sample_count < 2`: com uma observação a média da
janela é o próprio `current`, e `delta = 0.0` afirmaria "sem mudança" sem nada
para comparar. `delta_pct` é `None` quando o baseline é 0. Ausência é `None`,
nunca zero; zero observado é aceito (decisão por campo registrada em §8 do
documento) e negativo é sempre rejeitado. Freshness é reportada e não bloqueia.

**Nenhuma direção foi assumida.** O contrato do repositório não documenta a
direção de `stress`, `sleep_score` ou `readiness`, e não há fonte primária
acessível que fixe a escala do `stress` — logo `unit`/`scale` ficam `unknown` e o
dataclass não tem campo `direction`. Nenhum valor rotulado como bom/ruim.

Readiness **não** mudou: `SLEEP_SHORT_HOURS = 6.0`, `SLEEP_BELOW_AVG_HOURS =
2.0`, `READINESS_LOW = 60`, `HRV_LOW_RATIO = 0.80` e `RHR_RISE_BPM = 3.0`
intocados; `composite_low` continua lendo `readiness` como sinal separado pelo
mesmo limiar; `provider_readiness` é campo próprio para não se confundir com
`ReadinessView`. Zero score composto, zero advisory, zero policy, zero
prescrição, zero auto-deload. Detalhes em `docs/HR-4-SUBJECTIVE-WELLNESS.md`;
testes em `tests/test_hr4_subjective_wellness.py` (71). Suíte atual: **1259 testes, 0
falhas, 0 erros, 0 skips**.

## Trilha FTP canônico e histórico (2026-10-07)

**FTP Canonical History Base — DONE.** `FtpReference`/`FtpHistory`,
`resolve_ftp_at()` determinístico, correções auditáveis por
`supersedes_reference_id`, persistência local versionada em `ftp_history.json`
e queries/use-case locais em `Application` estão implementados. A base é isolada
de provider, `.env`, plano e prescrição; a suíte está em **1401 testes, 0
falhas, 0 erros**.

O contrato é prospectivo: uma referência só vale a partir de seu
`effective_from`; períodos anteriores à primeira referência, atividades sem
referência vigente e planos legados permanecem `UNKNOWN`. Isso é comportamento
correto, não gap preenchível por inferência. `.env FTP` continua legado
operacional durante a transição, não o modelo canônico futuro. `activity.icu_pm_ftp`,
`activity.icu_ftp`, FTP atual do provider, best20 e `ftp-scan` continuam sendo
evidência/estimate, nunca estado canônico Hermes.

| Ordem | ID | Próximo passo | Status / dependências |
|---|---|---|---|
| 1 | FTP-H1 | ~~Integrar `AthletePhysiologicalProfile` com `FtpHistory`~~ — **DONE**: `profile.ftp` vem de `FtpHistory.resolve_ftp_at` no instante `now`; ausência continua `None`, sem `DEFAULT_FTP` nem `.env` como fonte fisiológica canônica. | **DONE** — divergência transicional preservada: `profile.ftp` = canônico; `build`/`get_ftp()` = legado `.env`/fallback. |
| 2 | FTP-H2 | Modelar `FtpEvidence → Advice → confirmação explícita → FtpReference` para eFTP/provider estimate, best20, `ftp_scan`, testes, Zwift, Hermes e coach-defined. | **IMPLEMENTADO (2026-10-08)** — `src/ftp_evidence.py` (FtpEvidence/Advice/`advise_ftp`/repo), persistência `ftp_evidence.json`, use-cases na Application, CLI `ftp-evidence` (read-only) e `ftp-confirm` (confirmação explícita), `ftp-scan` registra evidência; nenhuma promoção automática; build/prescrição/.env intactos (FTP-H6 pendente); independente de FTP-H6. |
| 3 | FTP-H3 | Definir boundary persistida e canônica de novo bloco. | **IMPLEMENTADO (BlockContext v1)** — `src/training_block.py`, metadata aditiva `block_context` em `plan.json` e `Application.start_training_block()`; não seleciona fase, FTP ou prescrição. Spec: `docs/SPEC-ftp-h3-block-context.md`. |
| 4 | FTP-H4 | Advice de teste quando `canonical FTP == UNKNOWN` no início de bloco. | **PENDENTE — depende de FTP-H3**. `RETEST_RECOMMENDED` é Advice; não muda FTP, plano ou readiness/TSB. |
| 5 | FTP-H5 | Sessão de teste de FTP como Prescription. | **PARTIAL — aguarda TRAINER SAFETY CONTRACT** (auditoria 2026-10-08): PROTOCOL_EXTERNAL_V1 + PLACEMENT_USER_SELECTED definidos — teste externo, data escolhida pelo usuário, preparo D-2/D-1/D+1 reutilizado, resultado manual + confirmação explícita antes de virar referência. Perguntas mínimas de safety/placement registradas em `docs/ROTEIRO-TREINADOR.md` §1.7. Sem resposta do treinador → não `READY_FOR_IMPLEMENTATION`; FTP-H2 precede a implementação. |
| 6 | FTP-H6 | Fazer build/prescrição consumir FTP canônico em vez de `.env` como fonte principal. | **PARTIAL** — decisão de ownership dos watts **RESOLVIDA** (ADR-006, NÍVEL 1, 2026-10-08); restam decisões técnicas: resolução temporal build-time vs `workout.day` (inclui âncora de fuso) e comportamento com FTP canônico `UNKNOWN` no build. **Não DONE**; não reorganiza prioridades. |
| 7 | FTP-H7 | Reabrir FTP temporal para `ObservedIntensityDistribution`. | **BLOCKED/PARTIAL**; `WorkoutExecutionView`, taxonomia LOW/MODERATE/HIGH e histórico prospectivo existem, mas só períodos cobertos por `FtpHistory` podem ter threshold canônico. Ainda faltam contrato de duração/cobertura de streams irregulares e classifier/zone contract detalhado. |

**Guardrails da trilha.** `FtpHistory` não resolve retrospectivamente atividades
anteriores. FTP planejado (`PlannedWorkout.ftp_watts`) continua contexto da
prescrição e não é FTP histórico resolvido. Nenhum scan, provider, activity,
confirmação explícita.

**Estados preservados.** `ObservedIntensityDistribution` continua
**BLOCKED/PARTIAL**; `AdaptationState` continua **BLOCKED** (a história de FTP
não cria classificação de estímulo, ledger de exposição ou provenance de
adaptação); `training_decision` continua **PARTIAL**; `progression` continua
**NOT_READY_FOR_PRODUCTION**. Nenhum desses status é promovido por esta base.

## Trilha FTP — FTP-H2: evidência → confirmação → referência (2026-10-08)

**Status: IMPLEMENTADO (2026-10-08).** Contrato entregue, sem prescrição tocada:

- `FtpEvidence` (evidência/estimativa), `AdviceKind`/`Advice` (advisória) e
  `advise_ftp()` em `src/ftp_evidence.py`; persistência local em
  `ftp_evidence.json` (schema_version 1, atômica via `FtpEvidenceRepository`).
- Use-cases na `Application`: `record_ftp_evidence`,
  `get_ftp_advice`, e `confirm_ftp_evidence` — a **única ponte** evidência →
  `FtpReference`, com confirmação explícita (não automática).
- CLI: `ftp-evidence` (lista evidência + Advice, read-only) e `ftp-confirm`
  (prompt `s/N` antes de criar a referência canônica; `ftp-scan` agora registra
  evidência local dos candidatos validados).
- Provenance: cada referência confirma guarda `evidence_id`/activity/workout/
  provider (campo novo `evidence_id` em `FtpReference`, aditivo e
  backward-compatible).
- Guardrail mantido: **nenhuma evidência cria referência sozinha**; build,
  `.env`, provider e calendário permanecem intocados (FTP-H6 pendente).
- Suíte: 1481 testes OK (novos em `tests/test_ftp_evidence.py` + regressões em
  `tests/test_training_plan.py` e `tests/test_plan.py`).

Fluxo aprovado (contrato original):

```text
FtpEvidence            = evidence / estimate
   → Advice            = sugestao de revisar/testar/confirmar
   → confirmacao explicita do usuario
   → FtpReference      = estado canonico confirmado
```

**Fontes de `FtpEvidence` candidatas futuras:** `activity.icu_pm_ftp` / eFTP;
`activity.icu_ftp` somente como provider evidence quando apropriado; best20;
`ftp_scan` `proposed_ftp`; resultado de teste Hermes; resultado Zwift informado
pelo usuário; resultado de outra plataforma; entrada do treinador.

**Guardrail:** nenhuma dessas fontes cria `FtpReference` automaticamente —
evidência e canonical state **não se misturam**.

**Separação de responsabilidades:** `FtpEvidence` = evidence/estimate;
`Advice` = sugestão de revisar/testar/confirmar; `FtpReference` = estado
canônico confirmado.

**Dependências:** requer `FtpHistory` existente (DONE), contrato canônico já
aprovado (FTP-H1) e confirmação explícita. **Não depende de FTP-H6** — pode ser
implementado independentemente da migração do build. Não altera prescrição nem
`build_plan` nesta fase.

## Trilha FTP — auditoria FTP-H6 (2026-10-08)

**Resultado: `FTP_H6_NEEDS_PRODUCT_DECISION`.** Migração classificada como
**Prescription migration** (não é View integration), portanto exige gate
separado via auditoria — executada em modo read-only; **nenhum código alterado**.

**Achados da auditoria (contrato atual):**
- O motor de prescrição é **relativo**: `build_plan` gera durações e frações
  `%FTP` (`params.on_power` etc.); **nenhum alvo em watts absolutos é calculado
  no build**. O uso real do argumento `ftp` no build é **carimbar `ftp_watts`
  por sessão** (`plan.py:1067`, `_prep_workout`, `_race_workout`,
  `_insert_recovery`, `_reduce_next_hard`, `rebuild_workout`) — e `int(None)`
  quebraria hoje (FTP UNKNOWN não é suportado na estampa).
- Os **watts do calendário são derivados pelo provider**: o payload do `push`
  é texto `%FTP` (`workout_text`; o parâmetro `ftp` não é usado no caminho
  POWER em `event_payload`/`workout_text`) e o Intervals calcula
  `83% (151w)` com o **FTP treinado dele** (`icu_ftp`), não com o nosso.
  Logo, migrar a fonte do build muda a estampa/relatório, mas **não muda os
  watts exibidos** a menos que decidamos injetá-los — ver decisão abaixo.
- **TSS planejado é independente de FTP absoluto**: `estimated_tss` usa só
  frações `%FTP` (o parâmetro `ftp` é compat legado, `coach.py:283`). Trocar o
  FTP canônico não altera TSS previsto, duração, intensidade nem nome.
- `planned_workout_profile` já trata `ftp_watts` ausente/`None` com
  `has_structured_blocks=False` e sem watts (estado vazio honesto).
- `_ftp_indicators` (cabeçalho do relatório) lê `.env FTP`/`ftp_candidates`
  aplicados — fonte **legada**, não canônica; `profile.ftp` (canônico) e
  cabeçalho podem divergir; aceitável e deve ser rotulado.
- `PlannedWorkout.ftp_watts` **congela** o FTP usado no build na sessão
  persistida (snapshot da prescrição); `resolve_ftp_at` é prospectivo
  (`effective_from`), logo mudanças futuras no `FtpHistory` **não reescrevem**
  workouts já prescritos (freeze já garantido). Sessão de hoje preservada
  mantém `ftp_watts` verbatim.
- **Determinismo:** rebuild é determinístico dado (inputs, `FtpHistory`,
  timestamps de resolução); não usa `.env`/provider implicita além do que já
  lê. Resolução por dia de trabalho (`resolve_ftp_at(workout.day)`) é o modelo
  coerente com o contrato prospectivo, **mas** exige âncora de dia
  (instante timezone-aware) — o projeto não tem fuso suportado
  (`readiness_eligibility`, `_agora`). Resolver uma vez no início do build é
  mais simples e hoje é o comportamento; muda apenas quando uma referência
  entra vigente no meio do plano.
- **Legacy:** `ftp_watts` ausente, `DEFAULT_FTP` ou valor de `.env` não são
  distinguíveis pela provenance (182 pode ser medição real ou default) —
  limitation registrada; não migrar.

**Decisão bloqueadora principal (UMA):** **quem passa a ser o dono dos watts do
calendário após a migração** — (a) o Hermes injeta watts canônicos
(`canonical × %FTP`) em texto/payload estruturado, assumindo a semântica de
potência; ou (b) o Hermes mantém prescrição relativa `%FTP` e o FTP canônico
serve só de estampa/profile/consistência, deixando os watts ao FTP treinado do
Intervals. Cada opção tem contrato, UX e payload diferentes.

> **RESOLVIDA em ADR-006 (2026-10-08): NÍVEL 1 escolhido** — ver seção "Trilha
> FTP — decisão de ownership dos watts" abaixo. A decisão bloqueadora de
> produto não é mais blocker; a migração continua bloqueada apenas pelas
> decisões técnicas pendentes listadas ali.

**Decisões obrigatórias antes de qualquer implementação (gate §31):**
comportamento com `FTP == UNKNOWN` no build (estampa `None` + Advice, sem
bloquear); resolução por workout-day vs build-time + âncora timezone-aware;
compatibilidade HR mode (já independente de FTP: `FTHR` + RPE); tratamento de
legacy `ftp_watts`; payload provider (watts ou `%FTP`); preservação da sessão
de hoje; remoção do fallback `DEFAULT_FTP`/`.env` no build.

**Seam recomendado (futuro):** `Application` resolve o estado externo
(`FtpHistory`) e injeta entrada explícita no domínio (ex.: `ftp_by_day`/resolver
puro `date → Optional[int]`); `plan.py` **não** abre `ftp_history.json` e não
recebe repository. Passar `FtpPrescriptionContext` apenas se for mesmo
necessário; o menor contrato é `Optional[int]` por dia.

**Relações preservadas:** FTP-H2 é independente (só entra no build depois de
`confirmação explícita → FtpReference`); FTP-H3/H4 ficam separados (FTP-H6 não
implementa `RETEST_RECOMMENDED`); FTP-H6 não desbloqueia observed intensity.

## Trilha FTP — decisão de ownership dos watts (ADR-006, 2026-10-08)

**Decisão: NÍVEL 1 — prescrição relativa como fonte primária.** Registrada
formalmente em ADR-006 (vault `03-Decisoes/`, aceito em 2026-10-08).

**O que fica garantido (garantias Hermes):**
- build continua em `%FTP`/estrutura relativa, sem watts absolutos;
- `FtpReference`/`FtpHistory` permanece a referência FTP canônica (perfil);
- `PlannedWorkout.ftp_watts` permanece snapshot da referência usada na
  prescrição (freeze) — `plan.json` não muda retroativamente; rebuild
  determinístico conforme inputs; sessão persistida preserva o contexto;
- materialização local de watts apenas para Views/reports
  (`planned_workout_profile`: `%FTP × ftp_watts`);
- payload provider **relativo** (sem watts absolutos injetados, sem republish).

**O que NÃO é garantido (fora da garantia Hermes):** imutabilidade do rendering
do provider; watts históricos exibidos pelo Intervals; comportamento do
calendário após alteração do FTP no provider. Divergência esperada e aceita:
watts do calendário (FTP do Intervals) vs watts locais (snapshot Hermes).
Provenance obrigatória: `HERMES_PRESCRIPTION_REFERENCE` (`ftp_watts`) vs
`PROVIDER_RENDERED_WATTS` (materialização do Intervals sobre `%FTP`) — não
comparar sem informar a origem.

**Provider FTP:** Hermes **não** fará sync automático do `FtpHistory` para o
Intervals nesta decisão; se for desejado no futuro, será use-case explícito
separado (provider write, confirmação, auditability, semântica de erro) — fora
do FTP-H6.

**Escopo futuro de FTP-H6 (quando implementado):** resolver FTP canônico via
`FtpHistory`; fornecer a referência explicitamente ao build (`ftp_by_day`/
resolver puro, `plan.py` sem repository); congelar `ftp_watts` por sessão;
manter estrutura e payload **relativos**; **não** sincronizar FTP do provider;
**não** materializar watts absolutos no payload.

**Decisões técnicas pendentes antes de implementar (chumbo da violação da
gate §31 — não foram decididas aqui):** (1) resolução temporal — build-time vs
`resolve_ftp_at(workout.day)` + âncora de dia timezone-aware (preferência
arquitetural a avaliar: per-workout-day; não decidido); (2) comportamento do
build com FTP canônico `UNKNOWN` (recomendação da auditoria: estampa `None`-safe
+ Advice, sem bloquear; não decidido). Enquanto persistirem, FTP-H6 fica
`PARTIAL` — não `DONE`, não reordenado.

## Hermes Agent — integração opcional (auditoria arquitetural, 2026-10-07)

> **OPTIONAL — não compromete o roteiro.** O Hermes Coach funciona completo sem o
> Hermes Agent: CLI local, relatórios, prescrição, `reconcile`/`push`/`check` e a
> sincronia com o Intervals não dependem dele. Esta seção registra **uma opção de
> produto** auditada — não uma dependência nem uma feature aprovada.

**Auditoria concluída — resultado: `INTEGRATION_OPTION_READY` (somente leitura).**
[Hermes Agent](https://hermes-agent.nousresearch.com/docs) é o framework agêntico
open-source da Nous Research (repo
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)): casca
de conversa/automação/messaging com gateway em 21+ plataformas (Telegram,
Discord, Slack, WhatsApp, Signal, e-mail, Microsoft Teams, WhatsApp
Business Cloud API, iMessage via BlueBubbles/Photon, etc. — 19 nativos + IRC e
Teams via plugins), cron, subagentes com `output_schema` (saída estruturada),
memória persistente (mem0/Honcho/Holographic FTS5/supermemory, etc. via plugin),
completion contracts (Persistent Goals com contrato estruturado) e execução 24/7
(gateway como serviço + cron; backends local/Docker/SSH/Daytona/Modal/Singularity).
**Ele não é um motor de treino**: o Hermes Coach permanece a fonte fisiológica,
de prescrição e de estado; o agente só opera como **interface/orquestração**
sobre os use-cases da `Application`.

### Guardrails (não negociáveis)

- O agente **nunca** é: fonte fisiológica, motor de prescrição, substituto da
  `Application`, armazenamento canônico, executor direto de mutações no provider,
  autoridade de lifecycle/completion nem fonte de FTP canônico.
- Prescrição, TSB/PMC e zonas continuam decisão/motor do Hermes Coach; o agente
  **propõe** por use-cases existentes, nunca decide por si.
- Mutação de plano/calendário exige **aprovação explícita** pelo fluxo atual do
  Coach (mesma política do portal, #23); sem auto-apply do agente.
- Credenciais do Intervals **nunca** entram na config do agente; o agente fala com
  o seam do Coach (API/CLI) e não conhece o provider.

### Fases (ordem fixa; nenhuma avança sem aprovação explícita)

| ID | Escopo | Status |
|---|---|---|
| AGENT-0 | **Orquestrador local determinístico** — `scripts/hermes_agent.py` como facade sobre o CLI existente (`status`/`today`/`build`/`push`/`daily`/`vault`/`raw`/interativo; confirmação antes de mutações; sem LLM, sem gateway, sem mutação fora do fluxo de aprovação do Coach) | **DONE — 2026-10-08**; HOWTO em `docs/HOWTO-HERMES-AGENT.md`; AGENT-1..5 seguem inalterados |
| AGENT-1 | **Protótipo read-only** — gateway Telegram + adapter que expõe somente as Views de leitura da `Application` (plan view, readiness, heart-rate trend, wellness observado, CTL ramp, Pw:HR, FTP history, completion status) como comandos; **zero mutação** | **RESEARCH/READY_FOR_PROTOTYPE** — somente com aprovação explícita |
| AGENT-2 | Entrega de resumo/notificação via gateway (usa `summarize_period`/completion já existentes; o Coach gera, o agente transporta) — pode absorver/expandir o item #2 | TODO/FUTURE |
| AGENT-3 | Q&A interativo sobre heurísticas existentes (readiness, form advisory, recovery outlook) — read-only, sem auto-apply | TODO/FUTURE |
| AGENT-4 | Proposta estruturada de mutação que **reentra no fluxo de aprovação atual** do Coach (nunca mutação direta do agente) | TODO/FUTURE |
| AGENT-5 | Hub multi-atleta/treinador se o produto chegar lá — decisão separada, alinhada aos itens #24–#27; um agente por atleta, o Hermes segue superfície de comentário | TODO/FUTURE |

### Canal inicial

**Telegram — candidate first adapter, não dependência**: documentado e sem risco
de política de conta. WhatsApp via Baileys (bridge) é não oficial (risco de
política de conta); WhatsApp Business Cloud API é oficial da Meta, mas exige
verificação empresarial; iMessage (BlueBubbles/Photon) exige servidor macOS e não
é oficial da Apple. O item #2 da Fase 1 segue independente: o `Notifier` do Coach
pode usar qualquer canal, com ou sem agente.

### Observações da auditoria

- **AGENT-0 (local) não adianta AGENT-1 (gateway):** o orquestrador local
  determinístico (`scripts/hermes_agent.py`) é camada de interface local já
  publicada no repo; o protótipo read-only do gateway continua
  RESEARCH/aguardando aprovação explícita.

- **Integração barata para deixar para depois:** o seam da `Application`
  (Views DTOs + use-cases, UI-1..UI-5) já é o contrato que um adapter externo
  consumiria; para o agente, o Hermes Coach é só mais um consumidor, não um novo
  boundary a criar.
- **Não ativa por esta opção:** GEPA (repo separado
  `NousResearch/hermes-agent-self-evolution`; otimização de skills/prompts/código
  com revisão humana obrigatória — não toca o domínio de treino), completion
  contracts auto-aplicados no Coach, escrita no calendário, reescrita de plano,
  alteração de `ftp_history.json`/FTP canônico (trilha FTP-H*) nem
  reduce/replace/deload automático.
- **Relação com o roteiro atual:** #2 (notificações) → candidato a AGENT-2
  opcional; #29 (Coach+ chat) → possível montagem sobre AGENT-3/4 mantendo a
  prescrição no motor; #23/#24–#27 (portal/SaaS) → AGENT-5 é decisão posterior.
- **Messaging é uma interface entre outras** — a UI web/mobile (portal #23)
  permanece possível; o Hermes Agent não torna o portal obsoleto.
- **Fonte das capacidades:** docs oficiais `hermes-agent.nousresearch.com`
  (messaging, cron, delegation, security, memory-providers, goals, api-server,
  programmatic-integration e guias) — auditoria em 2026-10-07.

## Trilha Progressão — PROG-1..PROG-6: contrato de progressão semanal (2026-10-08)

> Auditoria PROMPT 67 → `PROGRESSION_NEEDS_ARCHITECTURE`. PROG-1 (contrato) está
> **documentado** em `docs/SPEC-progression.md`; **implementação NÃO iniciada**.
> Gates Q1-Q4 do treinador em `docs/ROTEIRO-TREINADOR.md` §1.8 e no formulário
> derivado (`docs/ROTEIRO-TREINADOR-TALLY.md` §12.2, IDs `PROG_Q1`–`PROG_Q4`).
> Não existe política de progressão semanal produtiva hoje.

| ID | Escopo | Status |
|---|---|---|
| PROG-1 | Contrato `ProgressionEvidence` → `ProgressionDecision` (actions, targets, reasons, hierarquia de precedência, missing-data, determinismo) | **SPEC/CONTRACT DONE — 2026-10-08**; documentação em `docs/SPEC-progression.md`. **NÃO confundir com código DONE** — implementação ainda não iniciada |
| PROG-2 | Guardrails de progressão + matriz de teste normativa | **BLOCKED / TRAINER DECISIONS Q1-Q4** — gates em ROTEIRO-TREINADOR §1.8 / TALLY §12.2 |
| PROG-3 | Integração de evidência (adherence + WorkoutExecutionView + readiness + phase + ramp + seams key-workout e recovery-week) | FUTURE |
| PROG-4 | Progressão de estímulo (biblioteca `SEQUENCES` p/ REPETITIONS/INTERVAL_DURATION; ranking de Q3) | FUTURE |
| PROG-5 | Mutation de prescrição (`PrescriptionProgression`, use-case separado) | FUTURE — permanece por último |
| PROG-6 | Validação histórica / backtest (depende de histórico observado; `AdaptationState` permanece BLOCKED) | FUTURE |

Ordem recomendada (PROMPT 41): PROG-1 → trainer Q1-Q4 → PROG-2 → PROG-3 →
PROG-4 → PROG-6 → PROG-5.

## INSIGHT M1 v2 — contrato de apresentação LLM read-only (2026-10-13)

| item | escopo | status |
|---|---|---|
| INSIGHT M1 v2 | Origem histórica: `lab/m1-contrato`; implementação limpa incorporada em `master` no commit `6b4a9791dfca5e562261b2c4c64c75de4e9b2e0c` via `FAST_FORWARD_ONLY`, com CI de master verde (run `38578649393`). Não houve release; Hermes permanece 0.0.36. INSIGHT-1..6: contrato read-only; renderer grounded + fallback determinístico; boundary de provider; harness offline G1–G7; seam `Application.get_insight_view`; e apresentação CLI segura. O LLM continua somente `InsightPresentation` read-only: flag `HERMES_INSIGHT_ENABLED` default OFF, sem provider/model concreto, invocação online, Presentation→action, promoção de FTP evidence ou alteração de `Prescription`; FTP canônico é omitido fail-closed. P3 não bloqueantes abertos: `INSIGHT2-AUD-03` (limites globais de tamanho de fact/input/output) e `INSIGHT3-AUD-01` (consistência request/provenance em futuro runtime de invocação). Fora do M1 implementado: integração de harness externo, workflow dedicado de eval, chat autônomo, tool calling e memory. | **MERGED TO MASTER** |

### INSIGHT M1.1 — hardening antes de runtime online

**Status: IN PROGRESS.** M1.1-A está concluído; M1.1-B é o próximo gate de
implementação. Pré-requisito técnico obrigatório do M2; não introduz provider,
modelo, rede ou mudança de `Prescription`. Mantém
`HERMES_INSIGHT_ENABLED` default OFF e o fallback determinístico.

| ID | Escopo | Critério de saída |
|---|---|---|
| INSIGHT2-AUD-03 | Limites explícitos para quantidade de facts; tamanho de key/value/unit; `InsightView` serializado; input/prompt; raw response; e `InsightPresentation`. Excesso falha fechado, emite status observável equivalente a `SIZE_LIMIT_EXCEEDED` e usa fallback, sem truncamento silencioso ou alteração de Prescription. Valores numéricos serão definidos em SPEC/implementação posterior, com testes de boundary/off-by-one. | **CLOSED**; M1.1-A publicado em `07f7529d82ecfd050bdc744843dea42dbbfd6229`; follow-up de invariância em `fb18b18a7d9656b691e298ac5b8db595988befa7`; CI final de master: run `38801992928`, `tests`/`unittest`, success. Nenhum finding P0/P1/P2/P3 restante neste gate. |
| INSIGHT3-AUD-01 | Unificar a fonte de verdade por invocation para `InsightModelRequest` e `RuntimeProvenance`: prompt version/hash, provider, requested/resolved model, runtime/harness version, commit/build e `executed_at`. Mismatch falha fechado; requested e resolved continuam distintos; alias não é identidade imutável; timestamp permanece injetável; domínio não lê env. | **OPEN**; M1.1-B — `REQUEST_PROVENANCE` é o próximo gate de implementação. |

**M1.1-A fechado:** bounds de count para facts/provenance; budgets UTF-8 de
key/value/unit; serializer canônico e budget de `InsightView`; budgets de input
de request, response de provider, Presentation agregada e expansão do renderer;
`InsightSizeLimitError` tipado, fail-closed sem truncamento silencioso; testes de
boundary/off-by-one e Unicode; composição determinística de fallback; e teste de
não-mutação/invariância.

**Saída de M1.1:** ambos P3 fechados; invariância de Prescription preservada;
suíte e evals offline verdes; core sem provider/rede obrigatórios; documentação
atualizada. M2 permanece bloqueado até M1.1-B/`INSIGHT3-AUD-01` concluir;
nenhum runtime online pode iniciar antes dessa saída.

### INSIGHT M2 — runtime online de explicação

**Status: PLANNED / DESIGN REQUIRED.** Objetivo: gerar somente uma apresentação
explicativa a partir de `InsightView` estruturado. Fluxo permitido:

```text
Application → InsightView → invocation runtime → InsightModelProvider concreto
→ raw response → validação de schema/grounding → InsightPresentation → UI/CLI
```

Toda falha resulta em fallback determinístico. Nunca há retorno de
`InsightPresentation` para Advice, Policy, Prescription, lifecycle, confirmação
de FTP ou sync de provider.

**Segurança:** input mínimo e allowlisted; output de schema fechado; sem execução
de shell, acesso arbitrário ao filesystem, ferramentas mutáveis, writes no
provider, tool/function calling, segredos no prompt, memory ou agent loop.

| ID | Etapa | Guardrails / decisão pendente |
|---|---|---|
| INSIGHT-M2-1 | Provider adapter concreto | Isolado atrás de `InsightModelProvider`; config/auth no runtime/composition boundary; sem imports de SDK no domínio; taxonomia normalizada; sem auto-retry, tools, function calling, memory ou agent loop. `FIRST_PROVIDER: OPEN`. |
| INSIGHT-M2-2 | Seleção e pinning de modelo | Registrar requested e resolved model por invocation; alias não é pin imutável; custo/latência observáveis separadamente; toda troca exige revisão. `FIRST_MODEL: OPEN`. |
| INSIGHT-M2-3 | Invocation runtime | Construir request a partir de `InsightView`; prompt version/hash e provenance consistentes; timeout e timestamp injetável; falhas de provider, modelo, schema, grounding ou tamanho caem em fallback; sem writes de plan/readiness/FTP. |
| INSIGHT-M2-4 | Data egress allowlist | Definir facts permitidos antes de qualquer chamada externa. Proibir raw provider payload, IDs externos de atleta/atividade, segredos, tokens, arquivos e provenance desnecessária. Subject é texto controlado; planned e observed seguem distintos; FTP canônico/evidence permanecem fail-closed. `ALLOWED_FACTS_FOR_EXTERNAL_PROVIDER: OPEN`. |
| INSIGHT-M2-5 | Prompt versionado | Camada de implementação, não domínio; version/hash determinísticos; mudança semântica revisada; fixtures/injeção em testes; sem thresholds fisiológicos, lógica de readiness/progressão/FTP ou decisões novas. |
| INSIGHT-M2-6 | Validação de resposta | `raw → closed schema → no prescription fields → grounding → caution provenance → contradiction guards → InsightPresentation`; sem silent repair; qualquer falha usa fallback. |
| INSIGHT-M2-7 | Gate de eval online/offline | Preservar G1–G7; core tests continuam offline; workflow online separado com `PASS`/`FAIL`/`SKIPPED`/`INFRA_ERROR` (`SKIPPED`/`INFRA_ERROR` ≠ `PASS`). Dataset é Hermes-owned; runner externo só pinado por tag/SHA/release, nunca branch flutuante. `ONLINE_EVAL_PROVIDER` e `ONLINE_EVAL_SCHEDULING: OPEN`. |
| INSIGHT-M2-8 | Observabilidade | Por invocation, sem secrets: provider, requested/resolved model, prompt version/hash, runtime/harness version, commit/build, executed_at, latência, status, fallback, grader/eval e custo separado. Não registrar keys, tokens ou raw sensitive payloads sem política futura explícita. |
| INSIGHT-M2-9 | Rollout controlado | Permanece OFF até M1.1, provider/model, egress, evals, observabilidade, fallback e invariância aprovados. Mesmo ON, continua presentation-only. `TIMEOUT_POLICY`, `COST_BUDGET`, `RETRY_POLICY`, `INITIAL_ROLLOUT_SURFACE` e disclosure/fallback UX: OPEN. |
| INSIGHT-M2-10 | Integração de apresentação | UI/CLI mantém estado estruturado separado; nunca parseia texto em ação, botão, mutação ou workflow de domínio. |

**Guardrails de autoridade e ciência:** `observed > derived > heuristic > advice
> prescription > InsightPresentation`. O runtime só verbaliza state/advice
existente: não recalcula readiness, progression, form/CTL-ramp advisory,
recovery, deload ou training-load thresholds; não infere illness; não transforma
planned em observed ou missing em zero/healthy; não confirma FTP nem promove
estimate/evidence. `FtpReference` só é canônico quando confirmado;
`PlannedWorkout.ftp_watts` continua snapshot `PRESCRIPTION`; `DEFAULT_FTP` nunca
é fisiologia; não há sync automático de FTP.

**Ordem obrigatória:** M1.1 primeiro (size limits, depois unificação
request/provenance); somente então M2: provider selection/design, adapter
concreto, seleção/pinning de modelo, allowlist de egress, invocation runtime,
contrato de prompt, validação de resposta, observabilidade, eval online e rollout
controlado/UI. Runtime online antes da conclusão de M1.1 é proibido.

**Decisões abertas:** `FIRST_PROVIDER`, `FIRST_MODEL`,
`ALLOWED_EXTERNAL_FACTS`, `TIMEOUT_POLICY`, `COST_BUDGET`,
`ONLINE_EVAL_PROVIDER`, `ONLINE_EVAL_SCHEDULING`, `RETRY_POLICY`,
`INITIAL_ROLLOUT_SURFACE` e user-facing disclosure/fallback UX.

**Critérios de conclusão de M2:** M1.1 fechado; provider/model e allowlist
aprovados; adapter e runtime provenance consistentes; prompt version/hash,
schema/grounding/fallback e no-domain-mutation cobertos; invariância de
Prescription comprovada; core offline independente de rede; workflow de eval
online separado; rollout decidido explicitamente; docs e CI/evals atualizados.

- **PROG-1 é contract/documentation DONE; a implementação ainda não começou.**
- `src/progression.py` e `src/training_decision.py` **permanecem órfãos**; destino
  conceitual documentado na spec (§30-31) — não evoluir como engines concorrentes ao
  build nem à futura policy.
- `AdaptationState` segue **BLOCKED** (§32 da spec); não entra como evidence até
  histórico observado válido.
- **Nenhum threshold novo.** `LOW_ADHERENCE` e `INCOMPLETE_WORKOUTS` são conceituais
  até Q1/Q2 (sem número na spec/código).
- Dívidas registradas na spec: key-workout (sem seam canônico; `dias_qualidade` não é
  equivalente) e recovery-week (sem state persistido); PROG-3 deve resolver ou explicitar
  ambos os seams.
- Validação do caso real foi read-only (PROMPT 67): lição abstrata "boa adesão +
  readiness degradada + missing data pode resultar em MAINTAIN" — sem dados pessoais
  em repo.

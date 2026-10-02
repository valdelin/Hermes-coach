# Roadmap — próximas implementações

Plano consolidado das próximas implementações do Hermes Coach. Cada item tem
rastreio no GitHub (issue) e estágio. Fonte canônica: vault do Obsidian
(`01-Projetos/hermes-coach/PLANO-NOVAS-IMPLEMENTACOES.md`); este arquivo é o
espelho público.

Referências: [ADR-003](https://github.com/valdelin/Hermes-coach/issues) (visão
de produto: "Runna do ciclismo indoor" — ver `docs/ARQUITETURA.md` e vault);
**fundamentação científica** do algoritmo em `docs/EMBASAMENTO-CIENTIFICO.md`
(o **contrato algorítmico**; a tabela científica Z1–Z7 completa — com %FCmáx,
%FC de limiar, RPE e ressalvas por zona — está no documento canônico do vault,
ao qual o arquivo do repo aponta);
**visão SaaS** (arquitetura alvo multi-tenant) em
`docs/ROADMAP-2-CRIACAO-DE-SAAS.md` (itens #24-#27, Fases 1B/3B); **parecer da
revisão técnica** (propostas aplicadas/não aplicadas) em
`docs/proposta-de-melhorias-do-sistema.md`.

## Backlog

| # | Tipo | Item | Issue | Fase |
|---|---|---|---|---|
| 1 | bug | Limpeza de "fantasmas" (atividades MANUAL criadas pelo Intervals ao parear treino) — **prioridade baixa** (cosmético, bug do Intervals, não do agente) | [#1](https://github.com/valdelin/Hermes-coach/issues/1) | 0 |
| 2 | feature | Notificações de treino (Telegram → e-mail/WhatsApp) | [#2](https://github.com/valdelin/Hermes-coach/issues/2) | 1 |
| 3 | feature | ~~Treinos sem medidor de potência (outdoor/FC: FTHR, hrTSS, %FTHR/RPE)~~ **implementado e issue fechada** (v0.0.16, modo FC %FTHR+RPE; validado 23/09 — 202 testes e 25/09 contra a API real — target HR) | [#3](https://github.com/valdelin/Hermes-coach/issues/3) | 2 ✅ |
| 4 | feature | ~~Ativar sync de wellness~~ **implementado e issue fechada** (RHR/sono no `info`; HRV sem suporte no FR935) | [#4](https://github.com/valdelin/Hermes-coach/issues/4) | 0 ✅ |
| 5 | feature | ~~Tipos de plano de treino (`GOAL`)~~ **implementado e issue fechada** (v0.0.9) — 7 tipos + `RACE_DATE`/tapper + variedade | [#5](https://github.com/valdelin/Hermes-coach/issues/5) | 2 ✅ |
| 6 | feature | ~~FTP sugerido a partir de treinos não agendados~~ (prova/treino livre) **implementado e issue fechada** (v0.0.15, `ftp-scan`: best-20min × 0,95 com gates + confirmação) | [#6](https://github.com/valdelin/Hermes-coach/issues/6) | 2 ✅ |
| 7 | produto | Casca estilo Runna: PWA + onboarding por objetivo + assinatura | — | 3 |
| 8 | produto | Multi-atleta / modo treinador (dashboard por atleta) | — | 4 |
| 9 | feature | **Perfil de esforço-alvo no `GOAL=race`** (estilo "Athlete Type" do Xert: Rouleur/TT/escalador) — ajusta a distribuição de focos dentro do mesmo objetivo | — (benchmark 22/09) | **possível — validar c/ treinador** | 2 |
| 10 | feature | **Nível do atleta** (iniciante/intermediário/avançado) como ajuste fino de volume/intensidade — hoje o TSB já calibra | — (benchmark 22/09) | **possível — validar c/ treinador** | 2 |
| 11 | produto | **Catálogo de eventos estilo Pillar** (200+ provas) — onboarding por prova-alvo (distância/perfil) | — (benchmark 22/09) | **possível — validar c/ treinador** | 3 |
| 12 | produto | **App comercial de ciclismo indoor** (posicionamento + preços — benchmark 22/09): consolidar #7/#8/#11 em produto com assinatura (tiers solo/coach), notificações (#2), catálogo de eventos e retenção | — (benchmark 22/09; ADR-003) | **possível — validar c/ treinador** (ROTEIRO-TREINADOR seções 3-4) | 3 |
| 13 | produto | **Assistentes de IA no padrão Tredict** — análise do histórico e criação de planos via LLM (MCP server / apps ChatGPT/Claude) como interface do motor; o nosso é determinístico/auditável (diferencial de confiança), o deles é LLM aberto | — (benchmark Tredict 23/09) | **possível — validar c/ treinador** | 3 |
| 14 | decisão | **W′/CP — não implementar agora**: análise Tredict (post mai/2026) mostra modelo de critical power instável e pouco acionável para endurance; CP/W′ ficam como **contexto/candidata** (ver `docs/GLOSSARIO.md`) | — (benchmark Tredict 23/09) | **possível — validar c/ treinador** | 2 |
| 15 | feature | **Wellness objetivo no alerta de sobrecarga** — dados coletados das plataformas via Intervals (Google Fit: peso, RC em repouso, sono, SpO2, tensão arterial, hidratação, kCal, gordura corporal; Garmin: + pontuação/qualidade do sono, VO2max, HRV rMSSD, passos) complementando o alerta `TSB ≤ −10` do Expected PMC. **Não é RPE/"como se sentiu"** (RPE continua âncora do modo FC — ver `docs/GLOSSARIO.md`); S2S (23/09): métricas de recuperação detectam overreaching | — (Science to Sport 23/09) | **possível — validar c/ treinador** | 1 |
| 16 | feature | **TSB-alvo pessoal de prova** — aprender o TSB ótimo de corrida correlacionando os melhores dias de forma com o TSB do dia (S2S: ótimo varia, `−5..+5` a `+10..+20` por atleta); usar para ajustar o taper do `GOAL=race`. **Semente implementada (v0.0.20)** no `GOAL=race`: o `build` projeta o TSB no dia da prova (Expected PMC) e compara com a faixa `−10..+20` (`_tsb_race_verdict`: cansado/ok/acima); falta o aprendizado pessoal | — (Science to Sport 23/09; Friel case study 2010) | **semente implementada — aprendizado pessoal: validar c/ treinador** | 2 |
| 17 | feature | ~~**Indicadores de zona extrema no Expected PMC**~~ **implementado (v0.0.19)**: Friel — `TSB < −30` = risco alto (R&R), `> +25` = transição (descanso longo); `forecast_pmc()` etiqueta a zona por dia (`_tsb_zone`) e o `model` avisa | — (Joe Friel 23/09) | **implementado** | 2 ✅ |
| 18 | feature | **Módulo de corrida a pé (esporte #2)** — `sport` no domínio (plan.json/workouts/eventos), limiar por pace/LTHR, `rftp-scan`, carga via Intervals (rTSS/gCTB), workouts de corrida em FIT, metas 5K/10K/meia/maratona (estilo RunDot), **PMC único multi-esporte** (TSS de todos os esportes no mesmo CTL/ATL — abordagem tri). Fora de escopo: passada/forma, Stryd/RunPower. **Prescrição SEM power meter** (protótipo `src/plan_run.py`): variável de controle é **p/ template**, não global — contínua/longa = `hr` (%LTHR; estado estável), tempo/limiar/VO2 = `pace` (ritmo-alvo do rFTP, FC como âncora), **fartlek = `rpe`** (surto < 2' nunca alcança a zona de FC; prescreve esforço "ritmo 5-10K"); sem `RFTP_PACE`, alvo `pace` cai p/ `hr`. Atleta escolhe no build; **decisão final: validação c/ treinador** (quando usar cada controle) | — (análise 23/09) | **possível — validar c/ treinador** | 2 |
| 19 | feature | **`recovery` — retorno a forma** (prazo realista + prescrição segura de rampa): varre **todo** o histórico real do Intervals (paginação com hiatos), reconstrói o PMC por dia (EWMA 42/7; zero nos hiatos para o decaimento não comprimir o tempo) e compara o hoje com o pico histórico (CTL, melhor mês, TSB). Estima semanas/meses para voltar a 90%/99% do CTL de pico sob rampas conservador/realista/otimista e entrega a rampa semanal de TSS com deload a cada 4 sem e teto = carga que sustenta o CTL-alvo (`src/recovery.py`; CLI `recovery`). **`build --recovery` (conexão ao build, 24/09)**: o plano dos próximos dias é orçado pelos tetos semanais da rampa (`--ramp-pts`, `--recovery-weeks`; também no `all`)~~ + **PMC real do Intervals + rampa calibrada (27/09)**: série ancorada nos `icu_ctl`/`icu_atl` reais (fallback reconstrução) e teto em TSS do plano via `calibrated_state` (teto = vol atual × pico/atual, ex.: 130 TSS/sem) | — (análise 23/09 — seu histórico real; 27/09 — alinhado) | **implementado (v0.0.21) + build conectado (24/09) + alinhado ao Intervals (27/09)** — validar a rampa c/ treinador | 2 |
| 20 | feature | ~~**`summary` — resumo dos treinos feitos por período**~~ (dia/semana/mês, janela terminando no dia-ancla, default ontem): sessões, carga total (TSS), tempo, distância, elevação, potência média/NP e FC média ponderadas pelo tempo + detalhe de cada treino; usa só atividades pareadas (`src/activity_summary.py`; CLI `summary --period --date`). **+ Períodos flexíveis (25/09):** `quarter`/`semester`/`year` (90/180/365d), duração livre `45d`/`6m`/`1y`, `plan` (primeiro→último dia do plano salvo = relatório final do ciclo) e `custom` (`--start`/`--end`); PMC acompanha a janela do período (piso 90d) | — (pedido 24/09 — "resumo do dia, semana, mes"; 25/09 — 6 meses/ano/fim do plano/custom) | **implementado (v0.0.22 + 25/09)** | 2 ✅ |
| 21 | feature | ~~**Gráficos no `summary`** (estilo Pillar "Advanced Progress Tracking"/Analog 90-day dashboards): **PMC CTL/ATL/TSB trailing 90d** em sparklines unicode (escala global compartilhada) + **barras de carga semanal** (TSS/semana ISO); `--chart auto|none|pmc|load|all` (default `auto` = PMC sempre + carga p/ semana/mês; `src/charts.py`); **`--export` para HTML/PDF** (SVG inline via `src/report.py`; PDF = mesmo HTML no chromium headless `--print-to-pdf`)~~ + **tema no relatório** (`src/brand.py`: 22 temas inspirados no Omarchy quattro; menu "Temas"/tecla T no HTML, `--theme` na CLI) e **linha de forma (TSB) por zona** (risco ≤ −10 / ideal / fresco ≥ +10, cores por tema)~~ + **alinhado ao Intervals (27/09, v0.0.29)** — PMC do gráfico parte dos valores REAIS `icu_ctl`/`icu_atl` de cada treino (`coach.real_pmc_by_day`) com decaimento EWMA entre os dias (`recovery.pmc_series_anchored`): mesmo número que o Intervals plota (CTL 25.3 vs ~15.8); reconstrução local de zero vira fallback | — (benchmark Pillar/Analog 24/09; alinhamento 27/09) | **implementado (v0.0.23 + alinhado 27/09)** | 2 ✅ |
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
| 34 | feature | **Recriar a pipeline de carga do Intervals no motor local** — como o `icu_ctl`/`icu_atl` da API é calculado internamente pelo Intervals (carga efetiva ~2× o `icu_training_load`; `strain_score`, NP, constantes `ctl_days`/`atl_days` configuráveis do atleta), bater sem bootstrap exigiria baixar streams de potência de todos os treinos e replicar a matemática deles (frágil a mudanças e a configurações da conta). **Decisão 27/09: não fazer agora** — o bootstrap presente já dá o diagnóstico 1:1; reabrir se quisermos TSB independente do Intervals ou diagnósticos sem a API | — (sessão 27/09 — análise do ~2×) | **decisão: adiado — reavaliar em Fase 0 futura** | 2 |
| 35 | validação | **Consistência com dados de outros atletas** — a divergência Motor local vs Intervals (carga ~2×) e a solução de bootstrap/ancorar nos `icu_ctl`/`icu_atl` (#33/#21 v0.0.29) foram validadas na conta do próprio usuário (1 atleta, ~5 semanas de retorno). Para confiar que o modelo Carrega/Decai igual para qualquer perfil (outdoor/NP, sem power meter/FTHR, atleta treinando há anos com CTL alto, periodização por blocos), inscrever **ao menos um 2º atleta de verdade** no fluxo real do portal (#23) e conferir: (a) gráfico local ancorado ≈ Intervals, (b) decisões de foco/TSB coerentes, (c) bootstrap presente sem divergência ao longo do tempo | — (27/09 — "precisamos de dados de outros atletas") | **aberto — depende do portal (#23) testar com 2º atleta** | 3 |
| 36 | bug | **Orçamento semanal inflado em ~1,4× (`cap × 7`)** — o teto da janela rolante de 7 dias era `cap diário × 7`, mas `avg_load` é a média **por dia de treino**; multiplicar por 7 concedia 7 sessões numa semana de 5 dias. Corrigido para `cap × len(training_days)` (287 → 220 TSS); `weekly_budget()` virou a única fonte (o `cap * 7` hardcoded no `build_plan` foi removido). Em paralelo, `avg_load` passou a contar só sessões **realizadas** (`paired_activity_id` presente): carga prescrita nunca executada não é evidência de tolerância (média 44,1 → 47,1). Achado adicional: mesmo com o teto fiel, o template `ftp-builder` produz ~217 no pico (folga de 1,4% do teto), ou seja **é o template que limita a prescrição, não o teto** | — (sessão 01/10 — "recalibração deveria respeitar o volume semanal") | **implementado (v0.0.30)** | 0 ✅ |
| 37 | bug | **Treino perdido por substituição binária em vez de absorção pelo orçamento** — o `reconcile` inseria "recuperação" e reduzia −5% no próximo Limiar para **qualquer** falta, sem distinguir a natureza do treino perdido (inclusive quando o perdido era o próprio active recovery). Corrigido: a carga não feita é **redistribuída** nos treinos Z2/SweetSpot posteriores com folga no teto (`_absorb_missed_into_budget`), limitada pelo teto e não por fator arbitrário. **O que não se compensa:** active recovery (o propósito é *não* gerar carga) e Limiar/VO2máx (a adaptação vem da intensidade acima do LT1, não de volume — fica como "débito" para o `build` repriorizar pelo TSB real). Detalhado em `docs/EMBASAMENTO-CIENTIFICO.md` §5 (Seiler, Friel) | — (sessão 01/10 — "1 treino perdido pode virar recuperação?") | **implementado (v0.0.30)** | 0 ✅ |
| 38 | bug | **`push` nunca varria órfãos além do horizonte do plano** — `newest` era derivado do **último dia do plano**, então eventos `hermes-plan-*` de um plano anterior **mais longo** nunca entravam na busca de órfãos e sobreviviam indefinidamente (o `--dry-run` reportava "0 órfãos" em silêncio). Caso real: 16 eventos de 16/10 a 06/11 (incluindo o **Ramp Test de 22/10**, `ftp_test_date`) sobraram de um plano de 20 dias quando o atual tinha 14. Corrigido com varredura em **duas camadas**: a busca é ampla (`start + 120d`) só para **enxergar** o que existe, mas só se **apaga** o que está **dentro** do horizonte do plano; além do horizonte é reportado como mantido. Sem essa distinção, um plano mais curto apagaria o plano mais longo legítimo | — (sessão 01/10 — duplicatas no calendário após `push`) | **implementado (v0.0.30)** | 1 ✅ |
| 39 | bug | **Duplicatas manuais no calendário não eram removíveis** — eventos criados direto no app do Intervals têm `external_id = None`, e `orphan_external_ids` filtra por `EXTERNAL_ID_PREFIX` **e** o `bulk-delete` só aceita `external_id`; logo, um treino manual que repetia um dia do plano (ex.: `VO2max 2026-10-14` vs `Treino de Sweet Spot`) coexistia para sempre sem caminho de limpeza. Adicionado `IntervalsClient.delete_event(id)` (`DELETE /events/{id}`) e `plan.manual_duplicate_ids()` (detecta manual sem `external_id` cujo dia existe no plano), ligado ao `push` com relatório no `--dry-run`. **Precedência:** evento do Hermes vence sobre o manual do mesmo dia; evento manual em dia **sem** treino no plano **não** é duplicata e é preservado | — (sessão 01/10 — "trate das duplicatas manuais") | **implementado (v0.0.30)** | 1 ✅ |
| 40 | refactor | **Idempotência do `reconcile`** — `absorbed_ids` é **reconstruído a cada execução** dentro de `_absorb_missed_into_budget()` e não é persistido em `plan.json`. Efeito: o mesmo treino perdido pode ser absorvido repetidamente em execuções sucessivas do timer (`daily_reconcile.sh`), elevando `on_sec` a cada run até bater no teto — a absorção não é convergente. Correção: persistir os `external_id` já absorvidos na meta do plano e pulá-los, tornando `reconcile` idempotente | — (sessão 01/10 — revisão pós-release) | **aberto — fazer depois** | 1 |
| 41 | limpeza | **`by_id` não utilizado em `_absorb_missed_into_budget()`** — mapa `by_id` é montado e populado mas nunca consultado na função (dead code). Remover junto da #40, ambos tocam a mesma função | — (sessão 01/10 — revisão pós-release) | **aberto — fazer depois** | 0 |
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
| 52 | dominio | **Critical Power / W′** — `CriticalPowerProfile` + ajuste `P = CP + W′/t` apenas com dados suficientes; CP/W′ complementam o FTP e não o substituem. | — (sessão 01/10 — P2-01) | **implementado (v0.0.34)** | 0 ✅ |
| 53 | feature | **Gerador estruturado VO2max** — `VO2Workout` com `interval_duration`, `repetitions`, `work_power_range`, `recovery_duration`, `recovery_power`, `total_work_time`, `progression_step` e `lever`, em três famílias; escadas por dimensão via `progression_ledger()`; `Z5_CEILING` impede o degrau de intensidade de atravessar para Z6. **Nenhuma estrutura de protocolo é superior** (NMA de 19 publicações, 240 atletas, todas as comparações não significativas) — os templates são formatos configuráveis, não recomendações de eficácia. | — (sessão 02/10 — P2-02) | **implementado (v0.0.35)** | 0 ✅ |
| 54 | feature | **Intenção e dose por família** (`src/zone_intent.py`) — `FamilyProfile` para `ENDURANCE`/`SWEET_SPOT`/`THRESHOLD` com `intent`, `dose`, `dose_shape`, `levers`, `not_claim` e `criterion`. **Sobreposição explícita**: `sweetspot` (84–97%) e `threshold` (91–105%) se cruzam em 91–97% FTP; `classify()` levanta `AmbiguousIntensity` nessa faixa em vez de escolher pelo número. Bandas vêm de `ZONE_BANDS` e não são redefinidas. | — (sessão 02/10 — P2-03) | **implementado (v0.0.35)** | 0 ✅ |
| 55 | docs | **Embasamento científico reestruturado** — 15 seções classificadas (`EMBASAMENTO CIENTÍFICA` / `HEURÍSTICA DO SISTEMA` / `MODELO COMPUTACIONAL`), índice, sem superlativo sem base comparativa; 5 autores e 2 PMIDs conferidos contra o abstract no NCBI (Düking corrigido: **34489178**, não 34469178); seção 14 de limitações; contrato testado por 19 testes documentais. | — (sessão 02/10 — P2-04) | **implementado (v0.0.35)** | 0 ✅ |
| 56 | teste | **Suíte de regressão científica** (`tests/scientific/`) — 222 testes em nove módulos, um por contrato algorítmico: training load (22), periodização (20), progressão (22), readiness (19), adaptação (20), FTP (34), CP/W′ (35), VO2max (24) e distribuição de intensidade (26). Cada docstring declara se a asserção é evidência, heurística ou modelo. Expôs quatro divergências doc↔código, registradas em #57. | — (sessão 02/10 — P3-01) | **implementado (v0.0.35)** | 0 ✅ |
| 57 | docs | **Correção de quatro divergências doc↔código** expostas por #56 — §11 (as quatro transições de `SEQUENCES` que quebram a regra de dimensão única, e a escada não ser caminho para subir potência), §12 (`MIXED_TEMPLATES` não muda duas dimensões em todo degrau; lever `INTENSITY` inerte na faixa padrão), §10 (`decay()` sem teto superior), §3 (OLS enviesado no `estimate_cp`). Nenhuma mudança de comportamento: em todos os casos o código é coerente com a intenção e era o texto que superdeclava. Quatro entradas novas em §14 + trava de teste date-dependent em `test_plan.ReconcileTest`. | — (sessão 02/10 — P3-02) | **implementado (v0.0.35)** | 0 ✅ |
| 58 | decisão | **Os 10 módulos de P0–P3 não afetam a publicação** — `training_phase`, `progression`, `intensity_distribution`, `athlete_profile`, `adaptation`, `training_decision`, `readiness_assessment`, `critical_power`, `vo2_generator` e `zone_intent` não participam de `build`/`push`, não alteram `plan.json` nem os valores de `focus`. São contratos testados, ainda não integrados. **Enquanto isso não for decidido, o trabalho P0–P3 é computação correta que não chega ao treino.** Integração é decisão de escopo: `plan.json` é contrato persistido e os valores de `focus` são publicados no Intervals. | — (sessão 02/10 — rastreio de §14 lim. 6) | **aberto — decisão de escopo** | 0 |
| 59 | decisão | **Quatro limites de implementação abertos** — todos documentados em §14 com trava de teste, nenhum corrigido: (a) `SEQUENCES` × regra de dimensão única (§11) — corrigir as sequências ou emendar a regra? (b) lever `INTENSITY` inerte na faixa padrão (§12) — estreitar a faixa, baixar `Z5_CEILING` ou aceitar? (c) `decay()` sem teto superior (§10) — `min(1, ...)` no fator? (d) `estimate_cp` enviesado (§3) — regressão ponderada por 1/t²? Cada um muda comportamento de prescrição, então é decisão explícita e não efeito colateral de suíte. | — (sessão 02/10 — rastreio de §14 lim. 9–12) | **aberto — decisão de escopo** | 0 |

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
  CP/W′ ficam como **contexto/candidata** no glossário, **fora do motor por
  ora** (backlog #14);
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

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
| 1 | bug | Limpeza de "fantasmas" (atividades MANUAL criadas pelo Intervals ao parear treino) — **prioridade baixa** (cosmético, bug do Intervals, não do agente) | [#1](https://github.com/valdelin/Hermes-coach/issues/1) | 0 |
| 2 | feature | Notificações de treino (Telegram → e-mail/WhatsApp) | [#2](https://github.com/valdelin/Hermes-coach/issues/2) | 1 |
| 3 | feature | ~~Treinos sem medidor de potência (outdoor/FC: FTHR, hrTSS, %FTHR/RPE)~~ **implementado e issue fechada** (v0.0.16, modo FC %FTHR+RPE; validado 23/09 — 202 testes) | [#3](https://github.com/valdelin/Hermes-coach/issues/3) | 2 ✅ |
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
| 15 | feature | **Input subjetivo de wellness** (RPE/"como se sentiu" pós-sessão via Intervals) no cálculo/alerta de sobrecarga — Science to Sport (23/09): sensibilidade a overreaching pode ser **maior** que métricas de potência; complementa o alerta `TSB ≤ −10` do Expected PMC | — (Science to Sport 23/09) | **possível — validar c/ treinador** | 1 |
| 16 | feature | **TSB-alvo pessoal de prova** — aprender o TSB ótimo de corrida correlacionando os melhores dias de forma com o TSB do dia (S2S: ótimo varia, `−5..+5` a `+10..+20` por atleta); usar para ajustar o taper do `GOAL=race`. **Semente implementada (v0.0.20)** no `GOAL=race`: o `build` projeta o TSB no dia da prova (Expected PMC) e compara com a faixa `−10..+20` (`_tsb_race_verdict`: cansado/ok/acima); falta o aprendizado pessoal | — (Science to Sport 23/09; Friel case study 2010) | **semente implementada — aprendizado pessoal: validar c/ treinador** | 2 |
| 17 | feature | ~~**Indicadores de zona extrema no Expected PMC**~~ **implementado (v0.0.19)**: Friel — `TSB < −30` = risco alto (R&R), `> +25` = transição (descanso longo); `forecast_pmc()` etiqueta a zona por dia (`_tsb_zone`) e o `model` avisa | — (Joe Friel 23/09) | **implementado** | 2 ✅ |
| 18 | feature | **Módulo de corrida a pé (esporte #2)** — `sport` no domínio (plan.json/workouts/eventos), limiar por pace/LTHR, `rftp-scan`, carga via Intervals (rTSS/gCTB), workouts de corrida em FIT, metas 5K/10K/meia/maratona (estilo RunDot), **PMC único multi-esporte** (TSS de todos os esportes no mesmo CTL/ATL — abordagem tri). Fora de escopo: passada/forma, Stryd/RunPower. **Prescrição SEM power meter** (protótipo `src/plan_run.py`): variável de controle é **p/ template**, não global — contínua/longa = `hr` (%LTHR; estado estável), tempo/limiar/VO2 = `pace` (ritmo-alvo do rFTP, FC como âncora), **fartlek = `rpe`** (surto < 2' nunca alcança a zona de FC; prescreve esforço "ritmo 5-10K"); sem `RFTP_PACE`, alvo `pace` cai p/ `hr`. Atleta escolhe no build; **decisão final: validação c/ treinador** (quando usar cada controle) | — (análise 23/09) | **possível — validar c/ treinador** | 2 |
| 19 | feature | **`recovery` — retorno a forma** (prazo realista + prescrição segura de rampa): varre **todo** o histórico real do Intervals (paginação com hiatos), reconstrói o PMC por dia (EWMA 42/7; zero nos hiatos para o decaimento não comprimir o tempo) e compara o hoje com o pico histórico (CTL, melhor mês, TSB). Estima semanas/meses para voltar a 90%/99% do CTL de pico sob rampas conservador/realista/otimista e entrega a rampa semanal de TSS com deload a cada 4 sem e teto = carga que sustenta o CTL-alvo (`src/recovery.py`; CLI `recovery`). **`build --recovery` (conexão ao build, 24/09)**: o plano dos próximos dias é orçado pelos tetos semanais da rampa (`--ramp-pts`, `--recovery-weeks`; também no `all`) | — (análise 23/09 — seu histórico real) | **implementado (v0.0.21) + build conectado (24/09)** — validar a rampa c/ treinador | 2 |
| 20 | feature | ~~**`summary` — resumo dos treinos feitos por período**~~ (dia/semana/mês, janela terminando no dia-ancla, default ontem): sessões, carga total (TSS), tempo, distância, elevação, potência média/NP e FC média ponderadas pelo tempo + detalhe de cada treino; usa só atividades pareadas (`src/activity_summary.py`; CLI `summary --period --date`) | — (pedido 24/09 — "resumo do dia, semana, mes") | **implementado (v0.0.22)** | 2 ✅ |
| 21 | feature | ~~**Gráficos no `summary`** (estilo Pillar "Advanced Progress Tracking"/Analog 90-day dashboards): **PMC CTL/ATL/TSB trailing 90d** em sparklines unicode (escala global compartilhada) + **barras de carga semanal** (TSS/semana ISO); `--chart auto|none|pmc|load|all` (default `auto` = PMC sempre + carga p/ semana/mês; `src/charts.py`); **`--export` para HTML/PDF** (SVG inline via `src/report.py`; PDF = mesmo HTML no chromium headless `--print-to-pdf`)~~ + **tema no relatório** (`src/brand.py`: 22 temas inspirados no Omarchy quattro; menu "Temas"/tecla T no HTML, `--theme` na CLI) e **linha de forma (TSB) por zona** (risco ≤ −10 / ideal / fresco ≥ +10, cores por tema) | — (benchmark Pillar/Analog 24/09) | **implementado (v0.0.23)** | 2 ✅ |
| 22 | feature | **"Próximo passo" pós-treino** — post-ride insight → ação clara única (estilo Analog Sports "clear next action"; ex.: "amanhã: recuperação — cargas caíram, TSB vira +"...): ainda sob análise se vira `summary`/`reconcile` enrichment | — (benchmark Analog Sports 24/09) | **possível — validar c/ treinador** | 2 |
| 23 | produto | **Portal do sistema + teste real de inscrição de outros atletas** — casca do produto (login/OAuth Intervals + onboarding por objetivo) pronta para receber um **2º atleta de verdade**: criar conta, conectar o Intervals, gerar plano e ver publicar no calendário dele; validar o fluxo ponta-a-ponta (não só o motor) num futuro não muito distante | — (decisão 24/09) | **aberto — futuro próximo** | 3 |

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

### Fase 1 — Comunicação (issue #2)
- Resumo do treino (foco + TSB + TSS previsto/real + avisos do reconcile) via
  **Telegram** primeiro; interface `Notifier` extensível (e-mail/WhatsApp);
  config `NOTIFY_CHANNEL`/token/chat id no `.env`.
- Regra: envio **assíncrono e não-bloqueante** (não derruba o timer diário).

### Fase 2 — Dados incompletos (issue #3) + tipos de plano (#5) + FTP sugerido (#6)
- ✅ **Sem medidor de potência (issue #3) — implementado (próxima release)**:
  `FTHR` no `.env` (`parse_fthr`/`get_fthr`); `build --no-power` carimba
  `hr_mode` nos workouts e o `push` envia `target: HEART_RATE` com texto em
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

### Fase 3 — Produto (casca estilo Runna, ADR-003)
- PWA + onboarding por objetivo → `build` → calendário → Zwift (`.zwo`) +
  assinatura mensal; login com API key do Intervals.
- **Parcialmente iniciado no agente (v0.0.10–0.0.11):** onboarding por objetivo
  (menu GOAL de 7 tipos) + troca de objetivo no meio do plano + disponibilidade
  (`WEEKLY_HOURS`/`LONG_DAY`). Falta a casca (PWA, tela de seleção, assinatura).
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
    `−5..+5` a `+10..+20`). **O que justifica:** **#15** (wellness subjetivo no
    alerta de sobrecarga) e **#16** (TSB-alvo de prova aprendido por
    correlação).

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

## Status atual (2026-09-24)

Revisão dos itens (sessões de 23-24/09; releases v0.0.20 → v0.0.23):

- **Implementados:** #16 (semente TSB-alvo no `race`), #17 (zonas extremas no
  Expected PMC), #19 `recovery` (v0.0.21), #20 `summary` (v0.0.22), **#21
  gráficos + relatório (v0.0.23)** — ver abaixo.
- **#21 publicado (v0.0.23):** `src/charts.py` (PMC 90d + carga semanal) e
  `src/report.py` (`--export` HTML/PDF com SVG); **temas** (`src/brand.py`:
  22 temas do Omarchy quattro; menu "Temas"/tecla T no HTML, `--theme` na CLI
  — com o `:root` do padrão emitido antes dos `[data-theme]` no CSS para
  nenhum tema ser sobrescrito) e **linha de forma (TSB) por zona** (risco ≤
  −10 / ideal / fresco ≥ +10). **274 testes OK**; validado no chromium:
  22/22 temas com as 3 cores de zona corretas. Kit portátil dos temas:
  `docs/TEMAS.md`.
- **Benchmark (24/09):** Pillar (4,9★; plano adaptativo,cadastro 200+ eventos)
  e Analog Sports Ana (2,6★ App Store; 90-day PMC dashboards, IA chat, mas
  sync/UX ruim) → **#21** implementado, **#22** (clear next action) no
  backlog; lição de UX/robustez registrada na Fase 4.
- **Abertos:** #1 fantasmas (baixa), #2 notificações (Fase 1), #7/#8/#11/#12
  (produto, Fase 3), #9/#10/#13-#15/#22 (possível — validar c/ treinador).
- **#19 conectado ao build (v0.0.24, 24/09):** `build --recovery` ora o plano
  pelos tetos semanais da rampa do `recovery` (`--ramp-pts`, `--recovery-weeks`;
  também no `all`) — release v0.0.24 publicada.
- **Novo no roadmap (#23, 24/09):** **portal do sistema + teste real de
  inscrição de outros atletas** — futuro próximo: casca (login/OAuth Intervals
  + onboarding por objetivo) pronta para receber um **2º atleta de verdade**
  (criar conta, conectar, gerar plano, publicar no calendário).
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
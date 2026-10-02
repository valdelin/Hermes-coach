# Changelog

Todas as mudanças relevantes do **Hermes Coach**. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o versionamento,
[SemVer](https://semver.org/lang/pt-BR/).

As versões aqui correspondem às **tags** do repositório (git tag) e aos
[releases publicados no GitHub](https://github.com/valdelin/Hermes-coach/releases).
As versões intermediárias (v0.0.3–v0.0.6) foram bumpados no `VERSION` sem tag
própria — foram agrupadas na tag/release v0.0.7.

## [Unreleased]

## [0.0.35] - 2026-10-02

Camada algorítmica: gerador VO2max, intenção de zona, embasamento
reestruturado em contrato testado e a suíte de regressão que fecha o
ciclo. **Nenhuma mudança em `ZONE_BANDS`, `plan.json`, valores de `focus` ou
na publicação no Intervals.icu** — os módulos novos continuam isolados do
fluxo `build`/`push` (ver limitações).

### Adicionado
- **Suíte de regressão científica** (`tests/scientific/`) — 222 testes em nove
  módulos, um por contrato algorítmico do embasamento: `test_training_load`
  (22), `test_periodization` (20), `test_progression` (22), `test_readiness`
  (19), `test_adaptation` (20), `test_ftp` (34), `test_critical_power` (35),
  `test_vo2` (24) e `test_intensity_distribution` (26). Cada teste registra
  em docstring se é **evidência**, **heurística do sistema** ou
  **modelo computacional**, e fixa a fronteira: o que a evidência sustenta e
  o que o Hermes escolheu.
- **Contrato documental testado** (`tests/test_embasamento_cientifico.py`) — 19
  testes que verificam as 15 seções do embasamento em ordem, o uso das três
  classificações, os 11 PMIDs exigidos, ausência de PMID órfão ou fora do
  limite estrutural, e ausência de superlativo sem base comparativa.

### Alterado
- **`docs/EMBASAMENTO-CIENTIFICO.md` reestruturado** em 15 seções (Princípios,
  FTP, CP/W′, Zonas, Periodização, Distribuição, Training Load, CTL/ATL/TSB,
  Readiness, Adaptation State, Progression Engine, VO2max, Recovery/Deload,
  Limitações, Referências), com índice e classificação explícita de cada bloco
  como **EVIDÊNCIA CIENTÍFICA**, **HEURÍSTICA DO SISTEMA** ou **MODELO
  COMPUTACIONAL**. Nenhuma faixa de `ZONE_BANDS` foi alterada.
- **Autores corrigidos na bibliografia** — conferidos contra o abstract no
  NCBI: Mackey (34304689), Inglis (31689684), Sitko (33728842), Schoenmakers
  (42237396) e Held (42482078). As citações anteriores traziam autores de
  memória.

### Correções
- **Nenhuma mudança de comportamento em `src/` no P3.** As 222 travas novas e a
  correção documental abaixo passaram sem exigir alteração de motor. As quatro
  divergências entre documentação e código expostas pela suíte científica foram
  corrigidas **na documentação**, porque em todos os casos o código é coerente
  com a intenção e era o texto que superdeclava:
  - `SEQUENCES` em `src/progression.py` quebra a invariante "uma dimensão por
    degrau" da §11 em quatro transições (3x12→2x15 min, 5x3→4x4 min, 8x1→6x2
    min, e o par de Sweet Spot/Limiar). A §11 agora traz a tabela das exceções,
    diz que elas trocam a **forma** do bloco preservando o volume total, e
    registra que a escada não é caminho para subir potência (intensidade fixa em
    0,90).
  - A §12 agora tem tabela de quais transições de `MIXED_TEMPLATES` mudam duas
    dimensões e quais mudam uma — `variable_intervals` é escada só de
    repetições — e declara que o lever `INTENSITY` é **inoperante** com
    `DEFAULT_INTENSITY_RANGE`, porque a faixa padrão encosta no teto de Z5 e a
    truncagem em `Z5_CEILING` zera o efeito de todo degrau.
  - A §10 declara que `decay()` só limita por baixo: com `days` ou `daily_rate`
    negativo a adaptação cresce acima do estado anterior.
  - A §3 declara que `estimate_cp()` usa OLS de P contra 1/t, que enviesa o
    intercepto, pesa um esforço de 120 s dez vezes mais que um de 1200 s, não
    pondera por duração e não filtra outlier.
- **Quatro limites novos na §14 (Limitações)** — as três primeiras ressalvas do
  conjunto acima, mais o bias do estimador de CP, enumerados como "limites de
  implementação conhecidos", distintos das limitações de literatura, cada um
  apontando para a trava que o fixa.
- **PMID 34469178 não existe**; o correto é **34489178** (Düking et al., 2021).
  Um teste agora rejeita PMIDs fora do limite estrutural.
- **Prontidão não prediz desempenho** (seção nova): treino guiado por HRV teve
  efeito médio em parâmetros submáximos (g = 0,296) mas efeito pequeno e não
  significativo em desempenho (g = 0,079; p = 0,597) e V̇O₂*pico* (g = 0,171;
  p = 0,130) — PMID 34489178. Noutra meta-análise o efeito no desempenho foi
  pequeno e **condicionado ao nível e sexo** do atleta (ES = 0,402; PMID
  33143175).
- **TSS é metodologia de indústria**, não evidência fisiológica, e não equivale a
  MLSS, LT, RCP ou CP. Marcado como tal na referência e na seção 7.
- **Seção 14 (Limitações)** nova, enumerando oito ressalvas: FTP não é
  fisiologia; não há modelo de periodização superior; não há protocolo de
  VO2max superior; TSS é indústria; prontidão não prediz desempenho; módulos
  isolados não afetam a publicação; heurísticas não são constantes fisiológicas;
  base de evidência restrita.

### Adicionado
- **Intenção e dose por família** (`src/zone_intent.py`) — `FamilyProfile` para
  `ENDURANCE`, `SWEET_SPOT` e `THRESHOLD`, com `intent`, `dose`, `dose_shape`,
  `levers`, `not_claim` e `criterion`. As bandas %FTP vêm de `ZONE_BANDS` e não
  são redefinidas.
- **Sobreposição explícita** — `sweetspot` (84–97%) e `threshold` (91–105%) se
  cruzam em 91–97% FTP. `classify()` levanta `AmbiguousIntensity` nessa faixa
  em vez de escolher pelo número: a potência não decide a família.
- **Alavancas de dose por família** — Z2 progride em duração e volume
  (contínuo, sem intervalos artificiais); Sweet Spot em duração e volume;
  Limiar em duração, repetições e recuperação. `distinguishes()` expõe os eixos
  de   divergência.
- **Gerador estruturado VO2max** (`src/vo2_generator.py`) — `VO2Workout` com
  `interval_duration`, `repetitions`, `work_power_range`, `recovery_duration`,
  `recovery_power`, `total_work_time`, `progression_step` e `lever`. Famílias
  `LONG_INTERVALS`, `SHORT_INTERVALS` e `VARIABLE_INTERVALS`, com templates 4x4,
  5x3 e 3x5 via `generate_mixed()`.
- **Progressão por dimensão** — escadas separadas para duração do intervalo,
  repetições, tempo total e intensidade, de modo que cada degrau altera **uma**
  variável só. `progression_ledger()` expõe as escadas para verificação.
- **Faixa de intensidade configurável** — 106–120% FTP por padrão, ancorada em
  `ZONE_BANDS[FOCUS_ZONE5_VO2MAX]` por teste; 115% não é valor universal. O
  degrau de intensidade é limitado por `Z5_CEILING` e não atravessa para Z6.
- **`evaluate()`** — avalia intensidade, duração do trabalho, recuperação
  proporcional e trabalho acumulado, com limites configuráveis.

### Notas científicas
- **95% FTP não é MLSS.** FTP correlaciona-se com a potência de lactato
  4,0 mmol/L (r = 0,88), mas com limites de concordância de −45 a +51 W, o que
  refuta equivalência; LT, IAT e Dmax diferiram significativamente (PMID 31269000).
  MLSS medida foi 88,5% do FTP (DP 4,8%) e respondeu ao treino (+12 W, p = 0,002)
  enquanto FTP95% não respondeu (p = 0,75) — PMID 31689684.
- **FTP está mais perto de RCP do que de VT** (r 0,71–0,90), com ressalva
  explícita de não usar os conceitos indistintamente (PMID 33728842).
- **Sweet Spot não é zona fisiológica universal** nem equivalente a limiar
  fisiológico; é categoria de prescrição sobreposta a Z3/Z4. As quatro
  ressalvas ficam em `not_claim`, expostas por perfil.
- Nenhuma estrutura de protocolo de HIIT mostrou superioridade estatística para
  tempo acumulado ≥90% V̇O₂max (network meta-analysis, PMID 42482078): as
  comparações de referência foram não significativas, com I² = 69,2%. Os
  templates e a direção da progressão de intensidade são **heurísticas do
  sistema**, não recomendações de eficácia.
- Intervalos ≥2 min produziram mais tempo perto de V̇O₂max que intervalos curtos
  ou moderados, e intensidade variável superou ritmo par (SMD = 0,80;
  PMID 42237396). A recuperação ativa vs. passiva não afetou esse tempo, então
  `recovery_power` e `recovery_ratio` são convenções do gerador.
- 17 testes novos do gerador VO2 e 14 da intenção por família; suíte com 470
  testes. Ambos os módulos isolados: não alteram `build`/`push`, `plan.json`,
  `ZONE_BANDS` nem a publicação no Intervals.icu.

## [0.0.34] - 2026-10-01

Camada de decisão adaptativa adicionada como módulos isolados. Nenhum deles
substitui o motor de publicação: `plan.json`, os valores de `focus` e os
identificadores do Intervals.icu seguem idênticos.

### Adicionado

- **Fases de treino** (`src/training_phase.py`) — `TrainingPhaseEngine` explicita
  `BASE`, `BUILD`, `SPECIFIC`, `PEAK`, `RECOVERY` e `TEST`, cada uma com
  objetivo, duração configurável, estímulos, limites de carga e critérios de
  progressão, deload e saída. Arquitetura de plano, não sequência fisiológica
  universal.
- **Progressão de estímulos** (`src/progression.py`) — `ProgressionEngine`
  indexa sequências por família (`sweet_spot`, `threshold`, `vo2max`,
  `endurance`, `anaerobic`). `CompletionScore` classifica `COMPLETED`,
  `PARTIAL`, `FAILED` e `EASY`; a sequência só avança após sucesso, parcial
  repete e falha reduz um degrau.
- **Distribuição de intensidade** (`src/intensity_distribution.py`) — relatório
  semanal de minutos efetivos de baixa, moderada e alta intensidade, por tempo
  e não por número de sessões. `POLARIZED`, `PYRAMIDAL`, `THRESHOLD_HEAVY` e
  `CUSTOM` são rótulos de configuração; o motor não pressupõe 80/20.
- **Perfil fisiológico** (`src/athlete_profile.py`) — marcadores opcionais
  (CP, W′, VO₂max, FC, volume, training age) com `FtpSource` e `FtpConfidence`
  explícitos. FTP-only permanece válido; nenhum marcador ausente é inferido.
- **Estado de adaptação** (`src/adaptation.py`) — seis domínios normalizados de
  0 a 1 com vetor de contribuição, decaimento temporal e saturação. Heurística
  computacional, não medição fisiológica.
- **Motor de decisão** (`src/training_decision.py`) — `TrainingDecisionEngine`
  compõe objetivo, fase, prioridades de adaptação, carga recente, readiness,
  família, progressão, dose e segurança num resultado com `rationale` e
  `confidence`.
- **Prontidão multimodal** (`src/readiness_assessment.py`) — combina HRV contra
  baseline individual, tendência de RHR, sono, fadiga subjetiva, carga,
  desempenho opcional e consistência. `GREEN`/`YELLOW`/`RED` indicam adequação
  ao treino, não diagnóstico; um sinal isolado não cancela sessão automaticamente.
- **Critical Power / W′** (`src/critical_power.py`) — `CriticalPowerProfile` com
  `protocol`, `confidence` e `test_dates`. `estimate_cp()` e `estimate_w_prime()`
  ajustam `P = CP + W′/t` e devolvem `None` sem dados suficientes;
  `work_above_cp()`, `w_prime_balance()` e `w_prime_reconstitution()` tratam
  esforço, saldo e recuperação de W′. Complementares ao FTP — nunca o
  substituem, nem equivalentes a MLSS, LT ou RCP.

### Testes

- **439 testes** verdes, incluindo fronteiras de CP/W′, dado insuficiente,
  saturação de adaptação, sinal isolado de prontidão e isolamento de dose por
  carga.

## [0.0.33] - 2026-10-01

### Mudado

- **Periodização separada de autoregulação** — `TrainingPlanState` explicita
  goal, fase, semana/ciclo, cargas, TSB e readiness. `GOAL` e proximidade de
  prova escolhem fase e alvo semanal; TSB baixo ou readiness desfavorável
  adaptam apenas a primeira sessão de qualidade para recuperação Z2.

### Testes

- **409 testes** verdes. A validação independente cobriu 8 critérios da spec e
  eliminou 3/3 mutações comportamentais.

## [0.0.32] - 2026-10-01

### Adicionado

- **Contrato explícito de carga de treino** — `TrainingLoadComponents` separa
  carga executada por potência, TSS estimado do treino planejado, carga externa
  e carga interna. Os quatro sinais não são somados ou convertidos entre si sem
  uma fonte e unidade declaradas.
- **TSS executado por potência** — `power_training_load()` calcula
  `horas × (NP / FTP)² × 100` quando NP e FTP válidos são observados após a
  sessão. Não infere NP de potência média, duração ou treino planejado; também
  retorna carga desconhecida para segmentos de até 30 segundos.

### Mudado

- **TSS planejado agora é nomeado** `estimated_tss()` — a estimativa baseada
  nos blocos em %FTP continua orçando `build`, `reconcile` e forecast, mas não
  é apresentada como uma medida executada. `estimate_tss()` permanece como alias
  compatível para os consumidores e formatos persistidos existentes.
- **CTL/ATL/TSB preservam a autoridade do Intervals.icu** — os fluxos atuais
  continuam usando `icu_training_load`; o Hermes não tenta reconstruir a
  pipeline proprietária do Intervals a partir de TSS local.

### Testes

- **401 testes** verdes, incluindo fórmula de TSS por NP/FTP, bordas sem
  NP/FTP, segmentos curtos, carga nula e compatibilidade do alias planejado.

## [0.0.31] - 2026-10-01

### Mudado

- **Fonte única da verdade para o embasamento científico** — a tabela Z1–Z7
  (com %FCmáx, %FC de limiar, RPE, sistema energético, recuperação típica,
  ressalvas por zona e a matriz de geração `.ZWO`) passa a viver **exclusivamente
  no documento canônico do vault**, e `docs/EMBASAMENTO-CIENTIFICO.md` no
  repositório passa a ser o **contrato algorítmico** — o que o código faz e por
  quê, em seção e fórmula — apontando explicitamente para o vault. Isso elimina
  uma divergência real: o arquivo do repo prometia uma "Tabela Científica Z1–Z7"
  que ele **não continha** (só tinha as seções de blocos, e apenas SweetSpot e
  VO₂máx), enquanto `ZoneIntegrityTest` e comentários em `src/` citavam aquele
  arquivo como origem da tabela.
- **Seções 1–3 do documento do repo reescritas** — descreviam o algoritmo
  anterior: "reagendamento Ter/Qui/Sáb" (a agenda é configurável via
  `TRAINING_DAYS`, padrão seg–sex), "redução de volume de 5% a 25%" (o teto é
  `cap × nº de dias de treino × escala do goal`, com `avg_load` contando só
  carga realizada) e "corte de 10% se IF > 1,15" (a redução agora é
  hierárquica e preserva a zona declarada).
- **Nova seção 6 no documento do repo — "Zonas como Invariante do Código"**,
  espelhando a §6 do vault: as quatro decisões que a tabela impõe ao motor
  (bandas ≠ focos; Z7 fora de `ZONE_BANDS` por ser potência máxima; active
  recovery é sessão dentro de Z2 e não foco Z1; um foco pode servir mais de uma
  zona), o mapeamento `FOCUS_ZONE` e a justificativa de por que as **constantes**
  renomearam mas os **valores string** não (persistência em `plan.json` +
  calendário do Intervals.icu).
- **Seção 6 antiga removida** — os blocos "SweetSpot" e "VO2máx" do repo eram
  redundantes com o vault e estavam desatualizados quanto à terminologia: o
  documento canônico **rejeita explicitamente** "vVO₂max" como nome de zona
  para ciclismo, e o texto antigo ainda usava essa notação.

### Corrigido

- **Referências que prometiam uma tabela ausente** — comentários em
  `src/coach.py` e `src/plan.py`, docstrings de `tests/test_plan.py`, e as
  entradas de ROADMAP/CHANGELOG passaram a apontar para a origem correta
  (documento canônico do vault, via seção que faz a ponte).

### Testes

- Sem mudança de comportamento: **395 testes** verdes (nenhum código de motor
  alterado nesta versão).
### Corrigido

- **Integridade de zona: `_fit_budget` rebaixava a potência abaixo da zona
  declarada** — ao apertar o orçamento semanal, o redutor cortava `on_power`
  até um piso fixo de **0.55**, independente da zona do treino. Isso produzia
  treinos nomeados que não entregavam a zona prometida: um `focus=sweetspot`
  (piso 84% FTP) saía com **0.55**, ou seja, estímulo de recuperação com o
  nome "Treino de Sweet Spot" intacto. Caso real observed no plano:
  `2026-10-02` com `focus=sweetspot` @ 55% FTP. Isso quebrava também a
  detecção de *active recovery* (que se baseia em `on_power` baixo), e
  tensionava a Zona 2 base (0.70 → 0.65 → 0.60 → 0.55, atravessando Z1).
  Agora a redução de carga é **hierárquica e preserva a zona**: (1) corta
  `repeats` — remove um intervalo inteiro, o corte de volume mais honesto;
  (2) encurta `on_sec`; (3) encurta `off_sec`; (4) só então reduz `on_power`,
  e **nunca abaixo do piso da zona**. As três primeiras levers são volume
  puro e preservam intensidade, nome e `focus`. O limite de zona passa a
  prevalecer sobre o teto: quando não cabe sem sair da zona, o plano
  preferencialmente estoura o teto a rebaixar o estímulo.

- **Orçamento semanal: teto inflado em ~1,4×** — o teto de TSS da janela
  rolante de 7 dias era calculado como `cap diário × 7`. Como a média de
  carga (`avg_load`) é **por dia de treino** (não por dia-calendário),
  multiplicar por 7 concedia 7 sessões numa semana que tem apenas `n` dias
  de treino. Com 5 dias, o teto caiu de ~287 para ~220 TSS, e 5 dias de
  treino passaram a caber em 5 sessões. `weekly_budget()` passou a receber
  `training_days` e virou a única fonte da fórmula (antes `build_plan`
  hardcodeava `cap * 7`, deixando a função oficial sem uso).

- **`avg_load` contava carga prescrita não realizada** — eventos de treino
  **nunca executados** (`paired_activity_id` ausente) entravam na média de
  carga que deriva o teto. Carga prescrita não é evidência de tolerância.
  Agora só sessões efetivamente realizadas alimentam a média (fallback
  conservador de 40 TSS/dia preservado). Impacto real: média 44,1 → 47,1
  TSS/dia.

- **`push` nunca varria órfãos além do horizonte do plano** (#38) — o limite
  superior da busca de órfãos era derivado do **último dia do plano**, então
  eventos `hermes-plan-*` de um plano anterior **mais longo** nunca eram
  examinados e sobreviviam indefinidamente, com o `--dry-run` reportando
  "0 órfãos" em silêncio. Caso real: 16 eventos de 16/10 a 06/11 — incluindo o
  **Ramp Test de 22/10**, o `ftp_test_date` do plano — sobraram de um plano de
  20 dias quando o vigente tinha 14. A varredura passou a ter **duas
  camadas**: a busca é ampla (`start + 120 dias`) apenas para **enxergar** o que
  existe no calendário, mas só se **apaga** o que está **dentro** do horizonte
  do plano; o que está além é reportado como mantido, de plano anterior mais
  longo. Sem essa distinção, um plano mais curto apagaria um plano mais longo
  legítimo — que foi exatamente o que a primeira versão da correção faria.

- **Duplicatas manuais no calendário eram inalcançáveis para limpeza** (#39) —
  eventos criados direto no app do Intervals têm `external_id = None`;
  `orphan_external_ids` filtra pelo prefixo `hermes-plan-` e `bulk-delete`
  aceita apenas `external_id`. Um treino manual que repetia um dia do plano
  (ex.: `VO2max 2026-10-14` convivendo com `Treino de Sweet Spot`) não tinha
  caminho de remoção. Adicionado `IntervalsClient.delete_event(id)`
  (`DELETE /events/{id}`) e `plan.manual_duplicate_ids()`, que detecta evento
  manual sem `external_id` cujo dia existe no plano — ambos ligados ao `push`,
  com relatório no `--dry-run`. Precedência: o evento do Hermes vence sobre o
  manual do mesmo dia; evento manual em dia **sem** treino no plano **não** é
  duplicata e é preservado.

### Mudado

- **Treino perdido é absorvido pelo orçamento semanal, não substituído por
  recuperação** — a regra anterior inseria uma sessão binária de
  "recuperação" e reduzia −5% no próximo Limiar para **qualquer** falta,
  sem distinguir a natureza do treino perdido. Agora a carga não feita é
  redistribuída nos treinos Z2/SweetSpot posteriores que ainda têm folga
  dentro do teto semanal — limitada pelo teto, não por fator arbitrário.
  O que **não** se compensa:
  - **Active recovery** (Z2 ≈0,55–0,60): o propósito do treino é *não*
    gerar carga; compensar exigiria carga, contradizendo o objetivo. Perder
    é quase sem custo.
  - **Limiar / VO2máx**: o estímulo é de alta intensidade e não se substitui
    com mais volume de base (a adaptação aeróbica vem da intensidade acima do
    LT1). A falta fica como "débito" e o `build` seguinte reprioriza pelo TSB
    real.

  Limites de segurança da absorção: apenas Z2/SweetSpot recebem elevação;
  cada treino cresce no máximo 20% de `on_sec` por reconciliação; só absorve
  enquanto a soma rolante de 7 dias couber no teto.

### Adicionado

- **`ZONE_BANDS` — faixas de prescrição por zona** (`src/coach.py`), espelhando
  a "Tabela Científica Z1–Z7" de `docs/EMBASAMENTO-CIENTIFICO.md`, com helpers
  `zone_floor()` / `zone_ceiling()`. Torna a tabela do documento uma
  **invariante verificável em código**: um teste de regressão compara `ZONE_BANDS`
  com os valores da tabela, de modo que divergir entre código e documento falha
  a suíte. Z1 (`<55%`) não entra como zona independente — é uma *intenção de
  sessão* executada dentro da banda Z2 (*active recovery* ≈0,60), sem foco
  próprio no código.
- `reconcile` passa a devolver `info` com `missed_tss`, `absorbable_tss` e
  `absorbed_tss`, permitindo reportar quanto da falta foi efetivamente
  redistribuído dentro do orçamento (e o que ficou para o TSB absorver).
- Documentação: seção "Orçamento Semanal de Carga" e "Treino Perdido:
  Absorver pelo Orçamento" em `docs/EMBASAMENTO-CIENTIFICO.md`, com as
  referências de Seiler (*Periodization Theory*) e Friel (*Periodization
  Bible*). Diagrama de estados atualizado (`Perdido → Ajustado` absorve pelo
  teto; nova transition `Perdido → Debito` para faltas de alta intensidade).
- Documentação: "Tabela Científica Z1–Z7" em `docs/EMBASAMENTO-CIENTIFICO.md`
  (vault), com %FCmáx, %FC de limiar, RPE Borg, sistema energético e recuperação
  típica por zona; ressalva de que %FTP/%FC/RPE não têm conversão universal;
  hierarquia de controle por zona (não usar FC como "segunda régua"); tabela de
  prescrição para geração de `.ZWO`; ressalvas por zona (Sweet Spot não é zona
  fisiológica universal; FTP ≠ limiar fisiológico; FC inutilizável em Z6/Z7;
  sprint ≠ "150% FTP"). 4 referências novas (PMC5033582, PMC7552657,
  PubMed 42237396, PubMed 39788807).

### Testes

- `ZoneIntegrityTest` (5 casos): `_fit_budget` nunca rebaixa `on_power` abaixo
  do piso da zona; `focus` não muda ao cortar carga; templates-base nascem
  dentro da faixa; plano gerado (5 valores de TSB × 2 FTP) respeita a faixa de
  cada zona; *active recovery* continua detectável e limitado a Z2; `ZONE_BANDS`
  bate com a tabela do documento. Varredura de 2.000 treinos (5 TSB × 4 FTP ×
  5 `weekly_hours`): **0 violações de zona**.
- `ManualDuplicateTest` (3 casos): identifica duplicatas manuais por dia,
  ignora eventos `hermes-plan-*`, respeita janela `start`.
- Cliente HTTP: `delete_event(id)` (DELETE `/events/{id}`) com teste de regressão
  dedicado.

## [0.0.29] - 2026-09-28

### Corrigido

- **`model` — Motor local alinhado ao Intervals (bootstrap presente)** — a
  pipeline interna do Intervals não é reproduzível por EWMA simples sobre o
  `icu_training_load` (carga efetiva ~2×; ver ROADMAP #34). O `cmd_model`
  agora parte do estado atual do Intervals (`latest_metrics`) em vez de
  reconstruir a trajetória do passado — diferença CTL/ATL/TSB passa de
  ~−10.9/−29.7 para **±0.0**, confirmando 1:1 o que o `build`/`reconcile`/
  `push` usam. Refatoração: `coach.metrics_history` (extrai PMC de todos os
  itens), `impulse_response.fill_daily_series` (série com zeros, útil p/ o
  `forecast_pmc`) e `cmd_model` simplificado com aviso claro quando não há
  métricas da API para bootstrappar.
- **`summary` — gráfico PMC alinhado ao Intervals** — o PMC no resumo (e no
  `--export` HTML/PDF) agora ancora nos valores **reais** `icu_ctl`/`icu_atl`
  que a API devolve por treino (`coach.real_pmc_by_day`), decaindo EWMA 42/7
  entre os dias (`recovery.pmc_series_anchored`) — plota o mesmo número do
  Intervals em vez da reconstrução local partindo de zero (CTL 25.3 vs os
  antigos ~15.8 na janela atual). A reconstrução local (`pmc_series`) vira
  fallback para quando não há valores reais. Comparação numérica das duas
  abordagens (60 dias: antigo CTL 10.0/ATL 24.2/TSB −14.2 vs atual CTL
  25.3/ATL 47.1/TSB −21.8) em `docs/COMPARACAO-PMC.md`. Ver direção em ROADMAP
  #35 (validar consistência com dados de um 2º atleta).
- **`recovery` e `build --recovery` — mesmo bug do `summary` corrigido no
  retorno a forma** — os dois ainda reconstruíam o PMC de zero sobre o
  `icu_training_load` (carga ~½ da efetiva do Intervals), subestimando o
  histórico: CTL 9.8/pico 23.9 em vez dos reais 24.7/32.0 (fev/22). Agora
  consomem a mesma série ancorada do `summary` (`_pmc_rows`:
  `real_pmc_by_day` + `pmc_series_anchored`, fallback na reconstrução) e
  **calibram a rampa para a moeda de TSS do plano** (`recovery.calibrated_state`:
  teto = volume semanal atual × CTL pico / CTL atual, em vez de `pico × 7`,
  que misturaria a escala ~2× do Intervals com o TSS do plano; ex.:
  100 × 32/24.7 ≈ **130 TSS/sem**). Pico/melhor-mês/TSB reportados agora são
  os do Intervals; a estimativa de retorno e a prescrição `--weeks`/`build
  --recovery` usam o teto calibrado. Novo: `recovery.calibrated_state`,
  `training_plan._pmc_rows` (compartilhado com o `summary`).

### Documentação

- **Diagramas UML alinhados ao código (v0.0.29)** — `docs/diagramas/*.mmd` e
  `docs/DIAGRAMAS.md` atualizados: classes `Recovery` (agora com
  `fetch_full_history`/`pmc_series_anchored`/`state`/`calibrated_state`/
  `estimate_return`/`ramp_schedule`, removidos `time_to_target`/`safe_ramp`),
  `WorkoutParams` completo, `SummaryAgg` com as chaves reais de `summarize`,
  `ReportRenderer.export_pdf`, `ImpulseResponseEngine.calculate_tss`; verbo
  `PUT` no `bulk-delete` dos diagramas de sequência. PNGs regenerados.

### Testes

- 374 testes OK (3 skipped), incluindo calibração da rampa de retorno
  (`CalibratedStateTest`) e ancoragem nos valores reais do Intervals.

## [0.0.28] - 2026-09-26

### Adicionado

- **`periodization` — explicação dos modelos para o atleta** —
  `training_plan.py periodization` lista os 5 modelos de periodização em
  linguagem de atleta (o que significa, o que se sente na prática, com que
  perfil combina) e sugere o melhor modelo para o `GOAL`/TSB atual
  (`src/periodization.py`; `--model NOME` detalha um modelo e mostra a
  afinidade com o objetivo). Não altera nada: apenas orienta a decisão
  (ex.: TSB baixo favorece `undulating`, TSB fresco libera `linear`/qualidade).
- **Decisão do usuário: o TSB governa a semana** — sem `PERIODIZATION` no
  `.env` (só os modelos disponíveis para consulta via `periodization`); o motor
  mantém o ciclo de foco por faixa de TSB.

### Documentação

- README: lista de comandos ganha `check` e `periodization`; DIAGRAMAS
  (v0.0.28) com o novo módulo `periodization.py`; ROADMAP "Status atual"
  registra a decisão do usuário e a nova explicação; `O-QUE-O-AGENTE-FAZ.md`
  (vault) espelha as capacidades atualizadas.

## [0.0.27] - 2026-09-26

### Adicionado

- **`check` — prontidão do dia (benchmark IntervalCoach 26/09)** — `training_plan.py check`
  lê wellness (RHR/HRV/sono/readiness) e avalia sinais de recuperação
  (`src/readiness.py`: RHR acima da média +3 bpm, HRV < 80% da média, sono < 6h
  ou 2h abaixo da média, readiness < 60). **Sugere** (nunca impõe) trocar o
  treino de hoje por uma recuperação Z2 curta; `--apply` aplica no `plan.json`
  (depois `push`). **Alerta de início de doença** (RHR subindo 2+ noites +
  HRV caindo) com aviso opcional ao treinador via `COACH_WEBHOOK` no `.env`
  (`coach_alert_payload`; envio não-bloqueante, não derruba o fluxo).
- **Modelos de periodização (`PERIODIZATION`)** — 5 modelos selecionáveis no
  `.env` (`src/plan.py::PERIODIZATION_TEMPLATES`): `polarized` (Z2 + VO2),
  `pyramidal` (base Z2 + progressão), `undulating` (alterna qualidade/leve),
  `linear` (progressão na semana) e `block` (semanas em bloco). O modelo ajusta
  a distribuição de focos por TSB (mesmo mecanismo do `GOAL_TEMPLATES`),
  prioridade sobre o GOAL; `build`/`all` aplicam quando configurado e o label
  aparece no resumo do plano.

### Documentação

- ROADMAP: benchmark competitivo **IntervalCoach** e decisões da sessão
  (26/09) na seção "Status atual"; itens **#28 Race Recon**, **#29 Coach+**
  (menor prioridade) e **#30 Multi-esporte** (sem urgência) no backlog;
  implicações estratégicas apontam para `docs/PITCH-DECK.md`.

## [0.0.26] - 2026-09-26

### Adicionado

- **Tooltip temático nos relatórios HTML (#21)** — gráficos de PMC e carga
  ganham tooltip explicando o eixo tema (`data-pmc`/`data-load` + JS): ao
  passar o mouse, mostra a data, a métrica e o tema do dia (dica de
  interpretação, não só o número).
- **`summary` — períodos trimestre, semestre, ano, plano e custom (#20)** —
  além de dia/semana/mês, o resumo aceita `--period quarter|semester|year|plan|custom`
  e duração livre (`45d`, `6m`, `1y`); `plan` gera o relatório final do ciclo
  (primeiro → último dia do `plan.json`) e `custom --start --end` janela
  arbitrária. O PMC acompanha a janela do período (piso 90 dias).
- **Resiliência de rede no `IntervalsClient`** — retry com backoff exponencial
  (0.5s → 1.0s → 2.0s) para falhas transitórias (`ConnectionError`, `Timeout`,
  HTTP 429/500/502/503/504); falha imediata para 4xx; mensagens amigáveis na
  CLI via `IntervalsApiError` (sem traceback cru; 401/403 indica credenciais).

### Documentação

- ROADMAP sincronizado com o vault: itens SaaS **#24-#27**, Fases 1B/3B e
  "Status atual (2026-09-25)" fundidos no `docs/ROADMAP.md` (única fonte no
  repo; `ROADMAP CONSOLIDADO.md` = ROADMAP.md + ROADMAP 2 CRIAÇÃO DE SAAS).
- Novos espelhos no repo: `docs/EMBASAMENTO-CIENTIFICO.md` (base fisiológica
  do algoritmo: Banister, Seiler, Coggan, Billat) e
  `docs/ROADMAP-2-CRIACAO-DE-SAAS.md` (visão SaaS multi-tenant).
- Arquivo vault `proposta de melhorias do sistema.md` revisado com o veredito
  de cada ponto (aplicado / já resolvido / não aplicado) — ver seção própria.

### Testes

- 297 → **312 testes OK (+15)** com `tests/test_intervals_client.py` (retry/
  backoff, `IntervalsApiError`, 401/404, `create_events` bulk, streams);
  suíte completa **315 testes OK (3 skipped)**. Smoke test real da API OK.

## [Unreleased]

_Próximas mudanças a documentar._

## [0.0.25] - 2026-09-25

### Corrigido

- **`target: HR` no push do modo FC (#3)** — o Intervals usa o enum `HR` (não
  `HEART_RATE`) no campo `target` dos eventos: `build --no-power` + `push`
  recusava com HTTP 400 ("JSON parse error") na API real. O mesmo valia para
  os eventos de corrida (`event_payload_run`). Peguei num smoke test real da
  API (25/09) com FTHR estimado dos rides reais; os testes com client fake não
  acusavam porque só gravavam o payload, sem validar o enum emitido.

### Validado

- **Smoke test real do modo FC (sem pedalar)**: `build --no-power` → plano em
  15 de FC (FTHR 168 bpm provisional, estimado do melhor 20 min dos rides) →
  `push --dry-run` → push real (HTTP 200, 10 eventos) → `GET` confirmando
  `target: HR`, texto °FTHR + RPE e `icu_training_load` calculado pelo
  Intervals a partir do texto. Teste **revertido** (plano/.env/calendário
  de volta a `target: POWER`). O `.env` segue **sem FTHR** — o valor real
  será definido quando o atleta usar o modo FC na rua.

### Testes

- 278 testes OK (contagem estável: 3 asserts do enum `target` atualizados de
  `HEART_RATE` para `HR`). ROTEIRO-TESTES documenta a validação real.

## [Unreleased]

_Próximas mudanças a documentar._

## [0.0.24] - 2026-09-24

### Adicionado

- **`build --recovery` (#19)** — o `build` pode ser orçado pelos **tetos
  semanais da rampa de retorno a forma**: consulta todo o histórico real do
  Intervals (mesmo pipeline do `recovery`), calcula o pico de CTL e o volume
  atual e usa `ramp_schedule` (crescimento `--ramp-pts`/sem, deload a cada 4
  semanas, teto = carga que sustenta o CTL-alvo) como orçamento em vez do
  padrão. Flags `--recovery`, `--ramp-pts`, `--recovery-weeks` (também no
  `all`). O `recovery --weeks` agora aponta direto para o `build --recovery`.
  A rampa é um teto, não um piso: o plano nunca fura o alvo além do piso de
  TSS de um treino.

### Testes

- +4 (274 → **278**): orçamento semanal da rampa no `build_plan`
  (`recovery_ramp` — semana apertada/solta, rampa curta mantém o último teto,
  redução abaixo do orçamento padrão) e wiring do CLI `build --recovery` com
  o pipeline do `recovery`.

## [0.0.23] - 2026-09-24

### Adicionado

- **Temas no relatório (`--theme TEMA`)** — o export HTML/PDF leva os **22
  temas** do kit de identidade `src/brand.py` (inspirados nos color schemes do
  Omarchy quattro; hex dos `colors.toml` reais). No HTML o leitor troca pelo
  menu **"Temas"** (ou tecla **T**) a qualquer momento; a escolha fica no
  `localStorage` (`hc-theme`); PDF honra o tema passado na CLI. Corrigido bug
  de cascata do CSS: o `:root` (tema padrão) agora é emitido **antes** de todos
  os `[data-theme]` — mesma especificidade, e quem vem depois vence (antes, o
  tokyo-night sobrescrevia os 18 temas listados antes dele no CSS).
- **Forma (TSB) colorida por zona do atleta** — a linha de forma muda de cor
  conforme o estado (como no Intervals/Friel): **risco** (TSB ≤ −10, vermelho),
  **ideal** (−10..+10, verde) e **fresco** (≥ +10, azul). Cores por tema
  (`fresh`/`risk`); segmento Bezier a segmento + ponto final e chip **"Estado"**
  no resumo do PMC. Descrição do PMC reescrita (explicação S2S/Friel + refs:
  *Monitoring your training load* — Science2Sport; *Managing Training Using
  TSB* — Joe Friel).
- **`docs/TEMAS.md`** — kit portátil dos temas: tokens documentados, consumo
  em CSS (com a regra de ouro da ordem do `:root`), switcher JS mínimo e o
  módulo completo copiável para outro projeto.
- Gráficos do `summary` (PMC 90d + carga semanal) e `--export` HTML/PDF
  (gráficos + temas) — seção 0.0.23 (mesma release).

### Testes

- +6 (268 → **274**): zonas da forma (segmentos risco/ideal/fresco + estado de
  risco + refs na descrição) e regressão da ordem do CSS (todos os 22 temas
  com bloco `[data-theme]` e `--fresh`/`--risk`; `:root` antes).
- Validação real no chromium headless: **os 22 temas** resolvem as três cores
  de zona corretamente.

## [0.0.22] - 2026-09-24

### Adicionado

- **`summary` — resumo dos treinos realizados** por período (dia/semana/mês):
  janela terminando no dia-ancla (por padrão ontem), usando só atividades
  pareadas (planejado-não-feito fica fora). Agrega sessões, carga total (TSS),
  tempo, distância, elevação, potência média/NP e FC média (ponderadas pelo
  tempo), e lista o detalhe de cada treino feito. Módulo `src/activity_summary.py`.

### Testes

- +13 (233 → **246**): `tests/test_activity_summary.py` (janela de período,
  filtro de treinos feitos, agregados ponderados, formatação) e CLI `summary`
  no `tests/test_training_plan.py`.

## [0.0.21] - 2026-09-23

### Adicionado

- **`recovery` — retorno a forma**: varre todo o histórico real do Intervals
  (só treinos feitos, com atividade pareada; planejado-nao-feito fica fora),
  reconstrói o PMC (CTL/ATL/TSB, EWMA 42/7, hiatos com zero) do primeiro dia
  até hoje e compara o estado atual com o pico histórico (CTL, melhor mês,
  TSB). Estima o prazo (semanas/meses) de volta a 90%/99% do CTL de pico sob
  rampas conservadora/realista/otimista (deload a cada 4 semanas, teto =
  carga que sustenta o CTL-alvo) e prescreve a rampa semanal de TSS
  (`recovery --weeks N --ramp-pts R`). Módulo `src/recovery.py` (backlog #19).

### Testes

- +17 (216 → **233**): `tests/test_recovery.py` (carga só de treinos feitos,
  série PMC com hiatos, estado/pico, estimativa de retorno, rampa com deload)
  e CLI `recovery` no `tests/test_training_plan.py`.

## [0.0.20] - 2026-09-23

### Adicionado

- **Taper progressivo para `GOAL=race`** (periodização do Joe Friel, case
  study 2010): a última semana antes da prova deixa de ser "Z2 uniforme 20'"
  e vira preparação por fases — **D-6** último estímulo de qualidade
  (Limiar curto ~2×6' "abrir a perna"), **D-5..D-3** recuperação Z2 curta,
  **D-2/D-1** spin muito leve (<60% FTP). Nomes por fase no plano.
- **Evento do dia da prova**: o plano garante `Prova: dia de prova` na data
  (mesmo fora da agenda de treino; TSS 0 = marcador, a carga real entra pela
  API) e **D+1** recuperação pós-prova quando é dia de treino.
- **Projeção de TSB no dia da prova (#16 — semente)**: `build` com
  `GOAL=race` projeta o TSB em `RACE_DATE` via Expected PMC e compara com a
  faixa-alvo `−10..+20` (Friel ~+20; S2S: individual), avisando se o atleta
  chega **cansado** (`< −10`) ou **passou do pico** (`> +20`).

## [0.0.19] - 2026-09-23

### Adicionado

- **Indicadores de zona extrema no Expected PMC (#17 — Friel)**:
  `forecast_pmc()` etiqueta cada dia da projeção com a **zona de TSB** de Joe
  Friel (`high-risk` < −30, `optimal` −30..−10, `grey` −10..+5, `freshness`
  +5..+25, `transition` > +25) via `_tsb_zone()`; retorna listas
  `high_risk`/`transition` e o `model` imprime a zona por linha + avisos de
  R&R (risco alto) e descanso longo (transição).
- **Módulo de corrida a pé (backlog #18)** — esporte #2 registrado no ROADMAP:
  `sport` no domínio, limiar por pace/LTHR, `rftp-scan`, carga via Intervals
  (rTSS), workouts de corrida em FIT, metas 5K/10K/meia/maratona, **PMC único
  multi-esporte**. **Possível — validar c/ treinador.**
- **Issue #3 fechada** — prescrição sem medidor de potência (%FTHR + RPE,
  target `HEART_RATE`, modo FC) validada na suíte (202 testes); ROADMAP nº 3
  refletido como fechado.
- **Docs (acumulado 22–23/09):** glossário de acrônimos (`docs/GLOSSARIO.md`);
  benchmark Tredict + referências de ciência **Joe Friel/Science to Sport** no
  ROADMAP (backlog #13–#17); pitch deck atualizado (Tredict, v0.0.18); portal
  de acesso (desenho v0, `docs/PORTAL-UI-DESIGN.md`); containerização + guia
  de deploy (`dev/DEPLOY.md`); repo privado.

### Testes

- +4 (198 → **202**): zonas de TSB — risco alto, transição, frescor (bordas) e
  plano vazio com `high_risk`/`transition` vazios.

## [0.0.18] - 2026-09-22

### Adicionado

- **Expected PMC (projeção de CTL/ATL/TSB do plano)** — nova
  `forecast_pmc()` em `src/impulse_response.py` mistura o real com o
  planejado: carga dos eventos até hoje (com dias de descanso zerados, sem
  comprimir o decaimento exponencial) + `tss` do `plan.json` de amanhã em
  diante. Retorna a série diária `(data, CTL, ATL, TSB)`, além de **alertas
  quando a projeção cruza TSB ≤ −10** (mesmo gatilho do portal). O `model`
  agora imprime a tabela da projeção e o aviso; com `initial_ctl/atl` da API
  simula só o futuro, e sem elas o histórico real estabelece o ponto de
  partida (fallback).
- **Plan Adherence (relatório de cumprimento)** — nova `adherence_report()`
  em `src/plan.py` reutiliza o critério de conclusão do `reconcile`
  (`_done_and_extra`): cada treino planejado é `feito`/`perdido`/`pendente`,
  agregado por semana ISO com % de cumprimento. Novo subcomando `adherence`
  imprime o relatório (hoje o `build` só listava os `missed` de passagem).
- **Testes**: +16 (181 → 197) — ancoragem de data, decaimento em dia de
  descanso, múltiplos treinos no mesmo dia, horizonte, alerta TSB, agrupamento
  semanal e classificação done/missed/pending.

### Corrigido

- **`adherence` contava o treino de hoje como "perdido"** no meio do dia: só
  o que efetivamente venceu (dia estritamente anterior) deve ser `perdido` —
  o de hoje, ainda não concluído, é `pendente`. Alinhe com o critério do
  `reconcile` (`w["day"] < today`). Sem o alinhamento, um plano com treinos
  pela manhã mostrava % de cumprimento artificialmente baixo (ex.: W39 saía
  `1 feito / 1 perdido` antes do treino do dia acontecer). Teste
  `test_treino_de_hoje_ainda_nao_conta_como_perdido` cobre o caso. (198 testes)

## [0.0.17] - 2026-09-22

### Corrigido

- **CLI quebrava ao carregar qualquer comando** (`info`/`build`/`push`/etc.)
  com `ValueError: badly formed help string`: o help do argparse de
  `--no-power` continha `%FTHR` sem escapar — argparse interpreta `%` como
  formato e abortava a montagem do parser. Escapado para `%%FTHR` nos dois
  subparsers (`build` e `all`). **Derrubaria o timer diário à meia-noite.**
  Encontrado pelo novo `dev/diagnose.sh`.

### Adicionado

- **Diretório `dev/`** — diagnóstico e recuperação para quando a aplicação
  quebrar: `dev/DIAGNOSTICO.md` (fluxo de investigação passo a passo) +
  `dev/diagnose.sh` (snapshot de estado: versão, timer systemd, log, `plan.json`,
  `.env` sanitizado, health check via `info` e suíte de testes).
- **Docs: benchmark de mercado + avaliação comercial** — Xert/Pillar/TriDot/
  RunDot (preços, prescrição, posicionamento) e avaliação de produto
  (ADR-003 como treinador automático por cima do Intervals, não app de tracking).
- **Docs: pitch deck para investidor** — `docs/PITCH-DECK.md` (12 slides,
  texto de tela + notas do apresentador) + `docs/PITCH-DECK-SLIDES.md` (versão
  só-slides para importar no Gamma). Ask proposto: US$ 25k, meta 100 atletas +
  3 treinadores (~US$ 82k ARR). Estratégia de beta testers (treinadores
  conhecidos) embutida nos slides 7/9/12 e no ROTEIRO-TREINADOR.
- **Docs: diagramas UML do sistema** — `docs/DIAGRAMAS.md` com 6 diagramas
  Mermaid (componentes, sequência do timer diário, ciclo manual
  build/reconcile/push, classes, decisão de foco, estados de evento) + PNGs
  renderizados em `docs/diagramas/` para o pitch deck.

## [0.0.16] - 2026-09-22

### Adicionado

- **Issue [#3](https://github.com/valdelin/Hermes-coach/issues/3)** —
  **implementado** (treinos **sem medidor de potência / modo FC**):
  - `FTHR` no `.env` (bpm) e `build --no-power`: o plano passa a prescrever em
    **%FTHR + RPE** (`FOCUS_HR_PCT`/`FOCUS_RPE`/`FOCUS_HR_HINT`, alvo em bpm
    via `hr_target_bpm`), e o `push` envia os eventos com
    `target: HEART_RATE` (o texto do Intervals mantém a regra de cues sem `%`/
    duração abreviada);
  - `reconcile` **preserva o modo FC** ao reescrever treinos (recuperação,
    limiar reduzido);
  - `info`/`reconcile` avisam **"Plano em modo FC — sem medidor de potência;
    carga estimada por FC (icu_training_load)"**;
  - a **carga real** sem watts segue do Intervals (`average_heartrate` →
    `hr_load`/`icu_training_load`), sem TRIMP local.

## [0.0.15] - 2026-09-22

### Adicionado

- **Issue [#6](https://github.com/valdelin/Hermes-coach/issues/6)** — **implementado**
  (comando `ftp-scan`): **FTP sugerido a partir de treinos fora do plano**.
  Detecta eventos pareados não-hermes, aplica filtros baratos no detalhe
  (não-MANUAL, ≥ 45 min, com potência, intensidade ≥ 75% do FTP), estima via
  melhor média móvel de 20 min × 0,95 (`src/ftp_estimation.py`) com gates de
  qualidade, propõe **somente para cima** (+3%..+30%), exige **confirmação
  antes de aplicar** e, no sim, atualiza `.env FTP` (+ `.env.bak`) e o
  `indoor_ftp` via `PUT /athlete/{id}/sport-settings/{ride}`. Candidatos ficam
  na meta do `plan.json` (`ftp_candidates`, com `applied`), preservada por
  `build`/`reconcile`; `info`/`ftp-check` avisam quando há pendência. Detalhes
  em `docs/KNOWN_ISSUES.md`.
- **`src/ftp_estimation.py`** (mecânica pura #6, determinística): `best_effort`
  (melhor média móvel, padrão 20 min), `clean_power` (clipe de spikes
  > 2,5× mediana, suporta anomalias da plataforma — só subestima) e
  `analyze_ride` → `proposed_ftp = round(best20 × 0,95)` com gates
  **CV ≤ 15%**, **min ≥ 80% da média** (anti-apagão) e **diff do atual em
  +3%..+30%** (só propõe para cima; >+30% = anomalia). 16 testes sintéticos;
  validado com dados reais (treinos agendados reprovam/sem novidade, como
  esperado).
- **`README.md`**: nova seção **"O que o cycling coach faz"** — inventário das
  capacidades (plano/cargas, GOAL, FTP, automação, segurança) + contagem de
  testes corrigida.

### Corrigido

- **#7** — `build` preservava o treino de hoje **descartando `WEEKLY_HOURS`/
  `LONG_DAY`**: a chamada recursiva agora repassa as duas opções (o treino de
  hoje preservado não é escalado). Testes `PreserveTodayWithAvailabilityTest`.
- **#8** — `reconcile` regravava `plan.json` **sem a meta**: agora carrega e
  regrava a meta (`goal`/`race_date`/`ftp_test_date`). Testes
  `ReconcileMetaTest`. Pré-requisito da #6 (os `ftp_candidates` vivem na meta).

### Atualizado

- **`docs/KNOWN_ISSUES.md`**: #7 e #8 marcadas **corrigidas** (2026-09-22);
  nota operacional do incidente do timer (evento de hoje apagado e restaurado);
  entrada nova da #6 (implementada).
- **`docs/ROTEIRO-TESTES.md`**: resultados completos da sessão de testes de
  22/09 (S1-S14 + bug hunt + correções).
- **`docs/ROADMAP.md`** sincronizado com o estado real (revisão de 21/09):
  registro dos 5 itens em aberto (#1–#3, #6, #7), dos fechados (#4, #5 —
  resta validação com treinador), da Fase 3 parcialmente iniciada no agente
  (onboarding + disponibilidade, v0.0.10–0.0.11) e do roteiro de testes
  (`docs/ROTEIRO-TESTES.md`, execução em 22/09). Na v0.0.15 o #6 entra nos
  **fechados** (ftp-scan entregue).
- Vault do Obsidian sincronizado: `HISTORICO.md` (entradas 2026-09-20 e
  2026-09-21), `PLANO-NOVAS-IMPLEMENTACOES.md` (status atual 2026-09-21) e
  cópia do `ROTEIRO-TESTES.md`.
- **Prioridade da #1 reduzida** (decisão 2026-09-21): a "fantasma" é
  **cosmética** e é comportamento do **Intervals**, não do agente —
  label `priority: low` criado no repo e aplicado à issue; documentado em
  `docs/KNOWN_ISSUES.md`; #1 saiu do início da sessão de testes de 22/09.

## [0.0.14] - 2026-09-21

## [0.0.13] - 2026-09-21

### Adicionado

- **`docs/ROTEIRO-TESTES.md`** — roteiro de testes manual/semi-automático para a
  sessão de validação: baseline de regressão, onboarding, info/wellness, build e
  disponibilidade (`WEEKLY_HOURS`/`LONG_DAY`), reconcile, push/calendário,
  troca de objetivo, teste de FTP, timer diário, segurança, áreas de risco para
  caça a bugs e template de reporte.

### Corrigido

- **`test_treino_perdido_insere_recuperacao` dependente do dia da semana**:
  com `start=hoje-2` e `days=5`, o plano não tinha nenhum dia passado de
  segunda a sexta (só passava em sáb/dom). Fixture agora usa `start=hoje-7`,
  que garante dias de treino passados em qualquer dia da semana.

## [0.0.12] - 2026-09-20

### Corrigido

- **`test_reconcile_mix_realista_eventos` dependente do dia da semana**: o
  fixture usava `missed=past[1]` + `anchor=today-2`, então os destinos das duas
  recuperações coincidiam (e o reconcile deduplicava "recuperação já
  programada") em seg/ter/qua/dom — o teste só passava em qui/sex/sáb. Novo
  fixture é determinístico (`start=today-6`, perdido = treino passado mais
  antigo, extra ancorado em `today-2`), validado para os 7 dias da semana.

## [0.0.11] - 2026-09-20

### Adicionado

- **Disponibilidade semanal do atleta** (antes de criar/regenerar o plano, o
  agente pergunta): **quantos dias** por semana disponíveis, **quantas horas**
  por semana (`WEEKLY_HOURS` no `.env`) e **melhor dia para treinos longos**
  (`LONG_DAY` no `.env`). Se o atleta não tem tempo para treinos longos no fim
  de semana, o agente aceita e adapta o plano para o melhor dia informado.
  - `build` escala a duração dos treinos (mínimo 120s por esforço) para a semana
    caber nas horas disponíveis — o orçamento de TSS continua mandando
    (`plan.py::_volume_scale`/`_scale_duration`, fator 0.5x–1.5x);
  - `build` rotaciona o ciclo semanal para o treino longo/endurance cair no dia
    preferido (ou no dia de treino mais próximo, quando `LONG_DAY` não é dia de
    treino — `plan.py::_place_long_day`);
  - `parse_weekly_hours` (aceita `5`, `5.5`, `5h`, `300min`) e `parse_long_day`
    (nomes em pt/en) com fallback seguro sem ajuste de volume/posição;
  - 17 testes novos (122 no total).

## [0.0.10] - 2026-09-20

### Adicionado

- **Wellness implementado** (issue
  [#4](https://github.com/valdelin/Hermes-coach/issues/4)): o sync Garmin
  Connect → Intervals.icu já entrega RHR/sono reais; `info` agora exibe
  `Wellness:` — RHR atual + média 7d, sono (h), passos e HRV quando houver
  (`wellness_summary`/`format_wellness`). **Decisão HRV (FR935)**: sem HRV
  Status overnight (requer Elevate Gen 3+); monitorar via Oura/WHOOP ou novo
  relógio fica no backlog. 5 testes novos (105 no total).
- **Onboarding (primeiro uso)** no agente `cycling-coach`: ao montar o primeiro
  plano, o agente conduz a configuração no chat — pergunta se o atleta **já tem
  conta no Intervals.icu** (se não, orienta criar conta gratuita e conectar as
  plataformas via **Settings → Connections**; guia em
  `docs/SYNC-PLATAFORMAS.md`), coleta **Athlete ID + API Key** (Settings →
  Developer Settings, com alerta de segurança), pergunta `TRAINING_DAYS`,
  `CUE_LANG`, `FTP` e o objetivo, e só então gera o plano (conta nova: TSB
  zerado calibra em ~2 semanas).
- **Menu de objetivos (GOAL)** no agente: ao pedir o objetivo, apresenta os 7
  planos com a descrição de cada (`back-to-fitness`, `ftp-builder`,
  `gran-fondo`, `time-trial`, `climbing`, `active-off-season`, `race`).
- **Trocar objetivo no meio do plano**: o agente recebe a intenção em linguagem
  natural, mapeia para o `GOAL` (perguntando `RACE_DATE` quando `race`), atualiza
  o `.env`, roda `build` **preservando o treino de hoje**, explica o que muda e
  pede confirmação antes do `push`; trocar para objetivo não-`race` remove
  `RACE_DATE` do `.env`.
- **Correção Basic Auth** na documentação: o Intervals.icu usa HTTP Basic Auth
  com **username fixo `API_KEY` e senha = a sua API key** (antes constava
  "usuario = senha = API_KEY", impreciso).
- `SKILL.md` do cycling-coach passa a descrever o onboarding e a troca de
  objetivo no meio do plano (versão 2.5.0 → 2.6.0); `README.md`/`README.en.md`
  ganham a seção **Primeiro uso (onboarding)**.

## [0.0.9] - 2026-09-19

### Adicionado

- `docs/KNOWN_ISSUES.md`: rastreio de bugs conhecidos do projeto. Registrada a
  issue [#1](https://github.com/valdelin/Hermes-coach/issues/1) — o Intervals
  materializa o evento `hermes-plan*` como atividade MANUAL "fantasma" ao
  sincronizar o treino (sem endpoint de merge na API; proposta de limpeza
  automática registrada para o futuro).
- **TODO registrado** (issue
  [#2](https://github.com/valdelin/Hermes-coach/issues/2)): enviar resumo do
  treino por **e-mail, WhatsApp ou Telegram** (foco + TSB + TSS previsto/real +
  avisos do reconcile) — adicionado às **Direções futuras** do README.
- **TODO registrado** (issue
  [#3](https://github.com/valdelin/Hermes-coach/issues/3)): suporte a **treinos
  sem medidor de potência** (outdoor/FC) — detectar ausência de potência,
  `FTHR` no `.env`, carga por FC (`hrTSS`) e alvos %FTHR/RPE — adicionado às
  **Direções futuras** do README.
- `docs/ROADMAP.md`: plano consolidado das próximas implementações (fases
  0-4, issues #1-#3 + produto estilo Runna + multi-atleta); README agora
  aponta para o roadmap.
- **TODO registrado** (issue
  [#4](https://github.com/valdelin/Hermes-coach/issues/4)): **ativar sync de
  wellness** (Garmin Connect → Intervals.icu: RHR, sono, Body Battery;
  avaliar HRV para o futuro) — adicionado às **Direções futuras** do README e
  ao roadmap (Fase 0).
- `docs/SYNC-PLATAFORMAS.md`: guia de sincronização de **cada plataforma
  compatível** com o Intervals.icu (Garmin, Zwift, Wahoo, Strava, Polar,
  COROS, Suunto, Amazfit, Huawei, Dropbox, Oura/WHOOP, Apple Health) —
  atividades, wellness, treinos planejados e regras anti-duplicatas; link na
  seção Documentação do README.
- **TODO registrado** (issue
  [#5](https://github.com/valdelin/Hermes-coach/issues/5)): **tipos de plano
  de treino** (`GOAL` no `.env`): `back-to-fitness`, `ftp-builder`,
  `gran-fondo`, `time-trial`, `climbing`, `active-off-season` e `race` (com
  `RACE_DATE` + tapper) — muda a distribuição de focos no `build` conforme o
  tipo; **`race` sempre pergunta a data alvo (dia da prova)** antes de montar
  o plano (sem default/campo vazio); adicionado às **Direções futuras** do
  README e ao roadmap (Fase 2).
- **Tipos de plano implementados** (issue
  [#5](https://github.com/valdelin/Hermes-coach/issues/5), Fase 2):
  - `GOAL` no `.env` — `back-to-fitness`, `ftp-builder`, `gran-fondo`,
    `time-trial`, `climbing`, `active-off-season` e `race`; ausente/inválido
    mantém o comportamento padrão por TSB (fallback seguro);
  - `GOAL_TEMPLATES` (distribuição de focos por TSB e por tipo) e
    `GOAL_BUDGET_SCALE` (calibração de carga: off-season ~60% vs race ~120%);
  - **variedade de formato**: com `GOAL` ativo o `build` alterna estruturas
    do mesmo foco (séries curtas/longas, contínuos) — plano não monótono;
    sem `GOAL`, o template atual é preservado;
  - `race` **sempre pergunta a data alvo** (`RACE_DATE`, futura) antes de
    montar o plano e salva no `.env`; nos últimos 7 dias antes da prova os
    treinos viram **Taper (pre-prova)** (zona 2, TSS baixo);
  - `plan.json` guarda `goal`/`race_date` (formato `{"goal", "race_date",
    "workouts"}`); `load_plan` continua devolvendo a lista (compatível com o
    formato antigo);
  - 24 testes novos (88 no total); docs atualizadas (README, ROADMAP).
- **Janela de reteste do FTP segue o tipo de plano** (`ftp-check`): ao final
  de cada bloco — `ftp-builder`/`gran-fondo` **6 semanas**, `time-trial`/
  `climbing`/`race` **4 semanas**, `back-to-fitness`/`active-off-season`
  **8 semanas**; sem `GOAL` mantém 8 semanas. 5 testes novos (93 no total).
- **Preparação prévia do teste de FTP** (consenso dos treinadores: teste =
  "mini dia de prova", sem fadiga acumulada): `build --ftp-test YYYY-MM-DD`
  (ou `FTP_TEST_DATE` no `.env`) protege as **48h antes** — D-2 vira
  Recuperação, D-1 vira Spin fácil (<65% FTP), D0 recebe o evento
  `Ramp Test (FTP)` (mesmo fora da agenda, como lembrete) e D+1
  Recuperação pós-teste; dias de descanso natural não são tocados.
  `plan.json` guarda `ftp_test_date`. 7 testes novos (100 no total).

### Alterado

- **Intervals.icu (conta do atleta):** `indoor_ftp` **210 → 182W** via API
  (`PUT /sport-settings/{id}`), alinhando o FTP indoor ao ramp test de
  2026-09-10 (`.env` = 182). Motivo: pausa de ~2 anos sem treinar —
  o 210 era o FTP da época; o 182 reflete a condição atual. **Histórico
  preservado**: atividades antigas mantêm `icu_ftp=210` congelado (sem
  recálculo retroativo); o novo valor vale para rides virtuais a partir de
  2026-09-19.

## [0.0.8] - 2026-09-18

### Adicionado

- **Motor de carga fisiológica (Banister Impulse-Response)** — `src/impulse_response.py`,
  implementando o spec da seção 1 do `docs/ARQUITETURA.md`:
  - `ImpulseResponseEngine.calculate_tss(duration, avg_intensity, threshold)` — TSS padrão
    `IF² × horas × 100` (retorna 0 para threshold ≤ 0);
  - `ImpulseResponseEngine.compute_metrics(daily_tss_history, initial_ctl, initial_atl)` —
    suavização exponencial com constantes 42/7 dias (CTL/ATL/TSB);
  - `daily_tss_series(events)` — série diária de TSS dos eventos do Intervals
    (`tss`/`icu_training_load`), mesmo critério de carga do reconcile.
- CLI `python3 src/training_plan.py model`: métricas do motor local vs
  Intervals.icu (com diferença) e **projeção** do TSB ao seguir o `plan.json`.
- 14 testes novos (64 no total); docs atualizadas (README pt/en, `docs/ARQUITETURA.md`).

### Documentação (entrou após v0.0.7)

- `docs/ARQUITETURA.md`: conceito original do agente (motor
  Impulse-Response/Banister, schema de estado do atleta, system prompt de
  corrida) sincronizado com o vault do Obsidian, com a tabela de diferenças
  para a implementação atual e notas de design aproveitáveis (rampagem
  +10%, teto de TSB, periodização por fases).
- README pt/en: seções **Documentação** (link para o spec) e **Direções
  futuras** (multi-atleta, modo solo, IA vs biblioteca, deload, corrida).
- `.gitignore` ignora `.env.bak` / `.env.*.bak`.

## [0.0.7] - 2026-09-18

### Adicionado
- `build` e `reconcile` agora imprimem a agenda de treinos em uso
  (`Agenda: seg,ter,qua,qui,sex`) e avisam quando `TRAINING_DAYS` não está
  definido no `.env` (usa o padrão).

## [0.0.6] - 2026-09-18

### Corrigido
- `scripts/daily_reconcile.sh`: `set -e` era desativado dentro do bloco
  `{ ...; } || { ...; }` (contexto condicional) — uma falha no `reconcile`
  não parava o fluxo nem notificava. Cada passo agora roda via `step()`, que
  loga, emite `notify-send` no desktop e sai com código != 0 na primeira falha.

## [0.0.5] - 2026-09-18

### Corrigido
- `_reduce_next_hard` reduz o mesmo limite (ex.: Limiar) no máximo uma vez por
  `reconcile`: o guard `reduced_ids` é compartilhado entre treinos perdidos e
  treinos extras, evitando dupla-redução quando dois eventos caem na mesma
  janela.

## [0.0.4] - 2026-09-18

### Adicionado
- O `reconcile` detecta **treinos extras fora do plano** (eventos com
  `paired_activity_id` e `external_id` não-hermes) na janela dos últimos 7 dias.
  Se a soma da carga chegar a um treino cheio (`>= cap_diario`, via `tss` ou
  fallback `icu_training_load`), o próximo dia de treino vira recuperação e o
  próximo Limiar é reduzido 5%. Trabalho leve não altera o plano.
- Testes cobrindo a detecção de extras e a recuperação inserida.

## [0.0.3] - 2026-09-18

### Adicionado
- Agenda de treinos **configurável** via `TRAINING_DAYS` no `.env`
  (nomes em pt `seg,ter,...` ou en `mon,tue,...`; padrão seg-sex). O foco do
  dia segue a posição na agenda.
- Testes de agenda parcial e mensagens explicativas em ambos os idiomas.

## [0.0.2] - 2026-09-16

### Adicionado
- Arquivo `VERSION` (passa a gerar versões explícitas).
- **Mensagens explicativas** (`cue text` + intervalos flat) publicadas em cada
  treino no Intervals — o aquecimento explica a zona e cada intervalo recebe
  "Agora voce vai entrar em X minutos a Y por cento do seu FTP".
- `CUE_LANG` no `.env` (`pt`|`en`) controla o idioma das mensagens.

## [0.0.1] - 2026-09-15

### Adicionado
- Baseline do projeto (`zwift-coach` → **hermes-coach**): agente opencode
  `cycling-coach`, skill do Hermes, clientes `intervals_client.py`,
  `coach.py` (TSB → foco → carga) e CLI `training_plan.py`
  (`info`/`build`/`reconcile`/`push`/`all`).
- Plano semanal por TSB, orçamento de carga (TSS 7 dias ≤ `cap_diario × 7`),
  upsert por `external_id` (sem duplicar eventos), publicacao no calendário do
  Intervals.icu e README em pt/en.
- CI: GitHub Actions roda `unittest` (Python 3.12) em todo push e PR — 50
  testes, stdlib-only.

---

## Como manter

Ao criar uma nova versão (bump de `VERSION`):

1. Adicione a seção da versão sob **Unreleased**, ou mova o conteúdo de
   `## [Unreleased]` para a nova tag.
2. Crie a **tag** (`git tag v0.0.X`) e a **release** no GitHub
   (`gh release create v0.0.X`).
3. Linke a nova versão na seção de comparações ao final deste arquivo.

## Comparações (links)

- [v0.0.21…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.21...master)
- [v0.0.20…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.20...master)
- [v0.0.19…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.19...master)
- [v0.0.18…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.18...master)
- [v0.0.17…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.17...master)
- [v0.0.9…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.9...master)
- [v0.0.8…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.8...master)
- [v0.0.7…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.7...master)
- [v0.0.2…v0.0.7](https://github.com/valdelin/Hermes-coach/compare/v0.0.2...v0.0.7)

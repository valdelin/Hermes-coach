# Diagramas UML — Hermes Coach

Diagramas em [Mermaid](https://mermaid.js.org) do sistema real (v0.0.35).
Renderizam nativo no Obsidian (bloco ` ```mermaid `) e no GitHub. Os `.mmd`
fonte vivem em `docs/diagramas/` (geram os `.png` via mermaid-cli).

**Fonte canônica: este diretório no repo.** Os `.mmd` e `.png` são espelhados
em `01-Projetos/cycling-coach/` no vault do Obsidian para leitura; quando os dois
divergirem, o repo vence. Editar aqui e copiar — nunca editar os dois lados.
Os blocos `mermaid` deste `.md` são embutidos, não gerados: se um `.mmd` mudar,
atualizar o bloco correspondente aqui também.

Legenda rápida dos módulos:

| Módulo | Responsabilidade |
|---|---|
| `src/training_plan.py` | CLI: `info` / `ftp-check` / `ftp-scan` / `check` / `periodization` / `model` / `recovery` / `build` / `adherence` / `summary` / `reconcile` / `push` / `all` |
| `src/coach.py` | Métricas (TSB/CTL/ATL), foco do dia, prescrição (`WorkoutParams`), TSS estimado |
| `src/plan.py` | Plano semanal (`build_plan` + `PERIODIZATION`), ajuste por carga (`_fit_budget`), `reconcile`, texto do treino, `event_payload` |
| `src/impulse_response.py` | Motor Banister local (CTL/ATL/TSB) + séries diárias de TSS |
| `src/intervals_client.py` | Cliente da API do Intervals.icu (events, wellness, activities, streams, sport-settings) com retry/backoff |
| `src/ftp_scan.py` / `ftp_estimation.py` | Análise de treinos fora do plano → proposta de FTP (20min × 0,95) |
| `src/recovery.py` | Retorno a forma: PMC real ancorado (EWMA 42/7) + TSB real + prazo + rampa calibrada com deload (`estimate_return`/`ramp_schedule`/`calibrated_state`) |
| `src/readiness.py` | Prontidão do dia (`check`): sinais de wellness (RHR/HRV/sono) → proposta **REDUCE** (foco e zona preservados, dose reduzida), elegibilidade por estado da sessão, idempotência e alerta de início de doença (+ `COACH_WEBHOOK`) |
| `src/readiness_assessment.py` | Avaliação de prontidão do Passo A (`ReadinessAssessment`/`ReadinessLevel`). **Integração parcial**: chega ao fluxo por `check --apply`, não por `build` |
| `src/periodization.py` | Explicação dos 5 modelos de periodização (`periodization`): o que significam para o atleta + sugestão por GOAL/TSB (top/evitar) |
| `src/activity_summary.py` | Resumo dos treinos feitos por dia/semana/mês (`summary`) |
| `src/charts.py` | Gráficos em texto: PMC trailing 90d + carga semanal (TSS/ISO) |
| `src/report.py` | Relatório com gráficos SVG: HTML direto / PDF via chromium headless (`--export`) |
| `src/brand.py` | Identidade: 22 temas (Omarchy quattro) + tokens de cor por tema |
| `plan.json` | Estado local do plano (treinos + meta: goal, race_date, ftp_candidates) |
| `scripts/daily_reconcile.sh` | Timer systemd às **05:30**: `check --apply` (grava o plano, não publica) → `reconcile --show` → `push --start hoje` |

---

## 1. Diagrama de componentes (visão geral)

```mermaid
flowchart LR
    subgraph CLI["CLI — src/training_plan.py"]
        CMD["info | ftp-check | ftp-scan | check | periodization | model | recovery<br/>build | adherence | summary | reconcile | push | all"]
    end

    subgraph CORE["Motor de coaching"]
        COACH["coach.py<br/>métricas · foco · prescrição"]
        PLAN["plan.py<br/>build_plan · PERIODIZATION · reconcile · event_payload"]
        IR["impulse_response.py<br/>CTL/ATL/TSB local"]
        FTPS["ftp_scan.py + ftp_estimation.py<br/>proposta de FTP"]
        AS["activity_summary.py<br/>resumo por período · pareamento"]
        REC["recovery.py<br/>PMC real ancorado + TSB real + prazo + rampa calibrada"]
        RD["readiness.py<br/>prontidão: sinais wellness · sugestão de troca · alerta doença"]
        RDA["readiness_assessment.py<br/>7 eixos · ausência = campo None<br/>coverage = eixos observados / 7"]
        PER["periodization.py<br/>explica modelos · sugere por GOAL/TSB"]
    end

    subgraph REPORT["Relatório (#21)"]
        CH["charts.py<br/>PMC 90d + carga semanal (texto)"]
        RP["report.py<br/>HTML (SVG) / PDF"]
        BR["brand.py<br/>22 temas + tokens de cor"]
    end

    subgraph API["intervals_client.py"]
        CLIENT["IntervalsClient<br/>events · wellness · activities · streams · sport-settings<br/>(retry/backoff em falhas transitórias)"]
    end

    subgraph OFF["Fora da publicação (#58) — contratos testados, não chegam ao treino"]
        TP["training_phase.py<br/>fase do plano + estado"]
        TD["training_decision.py<br/>decisão por completude"]
        PROG["progression.py<br/>escada por família de estímulo"]
        VO2["vo2_generator.py<br/>gerador VO2max estruturado"]
        ZI["zone_intent.py<br/>intenção + dose por família"]
        ID["intensity_distribution.py<br/>minutos por zona"]
        CP["critical_power.py<br/>CP / W′ / POT/PMC"]
        AP["athlete_profile.py<br/>perfil · procedência do FTP"]
        AD["adaptation.py<br/>Adaptação · teto de carga"]
        PR["plan_run.py<br/>prescrição de corrida (%LTHR + RPE)"]
    end

    ENV[".env<br/>credenciais · FTP · agenda · GOAL · PERIODIZATION<br/>COACH_WEBHOOK (alerta doença)"]
    PLANFILE["plan.json<br/>plano + meta"]
    SH["scripts/daily_reconcile.sh<br/>(timer systemd 05:30)"]

    INTERVALS["Intervals.icu API"]
    APPS["Zwift / Garmin<br/>(atividades + .zwo)"]
    PDF["resumo.pdf<br/>(chromium headless)"]

    CMD --> COACH
    CMD --> PLAN
    CMD --> FTPS
    CMD --> AS
    CMD --> REC
    CMD --> RD
    CMD --> PER
    CMD --> CH
    CMD --> RP
    COACH --> IR
    CMD --> CLIENT
    PLAN --> PLANFILE
    COACH --> ENV
    PLAN --> ENV
    RD --> ENV
    AS --> CLIENT
    REC --> CLIENT
    RD --> CLIENT
    RD --> RDA
    CLIENT --> INTERVALS
    INTERVALS <--> APPS
    SH --> CMD
    RP --> CH
    RP --> BR
    RP --> PDF

    COACH -. "consome ZONE_BANDS" .-> ZI
    OFF -. "cada um com trava em tests/scientific/" .- TP
```

---

## 2. Sequência — fluxo diário automático (timer de 05:30)

```mermaid
sequenceDiagram
    participant T as systemd timer<br/>cycling-coach-daily<br/>(05:30)
    participant S as daily_reconcile.sh
    participant C as CLI<br/>training_plan.py
    participant I as Intervals.icu API
    participant P as plan.json

    T->>S: 05:30 (timer persistente)
    Note over T: 00:00 foi trocado por 05:30:<br/>o dispositivo quase nunca<br/>sincronizava a leitura antes<br/>da meia-noite
    S->>C: check --apply
    C->>I: GET /wellness (leitura do dia)
    I-->>C: RHR/HRV/sono
    C->>P: le plano de hoje
    C->>C: readiness_eligibility()<br/>concluida -> preservada<br/>estado desconhecido -> propoe, nao aplica
    C->>P: grava REDUCE no plan.json (nao publica)
    alt sem leitura do dia
        C-->>S: avisa: sem dado, segue para o reconcile
    end
    S->>C: reconcile --show
    C->>I: GET /events (janela)
    I-->>C: eventos + métricas
    C->>P: carrega plano atual
    C->>C: detecta perdidos/extras<br/>recuperação + limiar -5%
    C->>P: salva plano ajustado
    C-->>S: OK / erro
    alt erro no reconcile
        S->>S: notify-send (crítico) + exit 1
        S-->>T: falha (log em logs/)
    else sucesso
        S->>C: push --start hoje
        C->>I: GET /events (recentes)
        C->>C: calcula órfãos (hermes-plan*)
        C->>I: PUT /events/bulk-delete (órfãos)
        C->>I: POST /events/bulk?upsert=true (treinos)
        I-->>C: 200 OK
        C-->>S: calendário atualizado
        S-->>T: sucesso
    end
    Note over C,I: check --apply nunca publica.<br/>So o push toca o calendário.
```

---

## 3. Sequência — ciclo manual (build → reconcile → push)

```mermaid
sequenceDiagram
    participant U as Atleta
    participant C as CLI
    participant I as Intervals.icu API
    participant P as plan.json

    U->>C: build --days 60 --days-plan 14
    C->>I: GET /events (60d)
    I-->>C: histórico
    C->>C: latest_metrics → TSB
    C->>C: build_plan (GOAL + PERIODIZATION +<br/>WEEKLY_BY_TSB + WEEKLY_HOURS +<br/>LONG_DAY + budget TSS)
    Note over C: preserva treino de hoje<br/>do plano anterior
    C->>P: salva plan.json (treinos + meta)

    U->>C: check --apply (opcional, v0.0.27)
    C->>I: GET /wellness (janela)
    I-->>C: RHR · HRV · sono · readiness
    C->>C: assess_readiness → sinais
    alt possível início de doença
        C-->>U: ALERTA: RHR 2+ noites + HRV caindo
        C->>C: COACH_WEBHOOK (se configurado)
    end
    C->>C: sugere troca por recuperação Z2?
    Note over C: decisão é do atleta —<br/>nunca impõe
    C->>P: check --apply: substitui treino de hoje

    U->>C: reconcile --show
    C->>I: GET /events (janela)
    C->>P: carrega plano
    C->>C: treino perdido? → recuperação + limiar
    C->>P: salva ajustes
    C-->>U: agenda + ajustes

    U->>C: push --start YYYY-MM-DD
    C->>P: carrega plano
    C->>I: GET /events (recentes)
    C->>I: DELETE órfãos (se houver)
    C->>I: POST /events/bulk?upsert=true
    I-->>C: eventos publicados
    C-->>U: calendário atualizado
```

---

## 4. Diagrama de classes (entidades com contrato verificado)

```mermaid
classDiagram
    direction LR

    class WorkoutParams {
        +str focus
        +int repeats
        +int on_sec
        +int off_sec
        +float on_power
        +float off_power
        +int warmup_sec
        +float on_power_pct
    }
    class PlannedWorkout {
        +str day
        +str focus
        +int planned_duration
        +str name
        +dict params
        +float tss
        +str external_id
    }
    class TrainingPlanState {
        +str start
        +float ftp
        +list workouts
        +dict meta
    }
    class ReadinessEligibility {
        +dict workout
        +str state
        +bool eligible
        +str reason
    }
    class Metrics {
        +float tsb
        +float ctl
        +float atl
        +float tss
        +float ftp
        +str day
    }
    class FtpTestSuggestion {
        +bool due
        +str reason
        +str day
    }

    class ReadinessLevel {
        <<enumeration>>
        GREEN
        YELLOW
        RED
    }
    class ReadinessAssessment {
        +float hrv_score
        +float rhr_score
        +float sleep_score
        +float subjective_fatigue_score
        +float recent_load_score
        +float performance_score
        +float consistency_score
    }
    class ReadinessAction {
        <<enumeration>>
        NONE
        REDUCE
        REPLACE
    }
    class ReadinessDecision {
        +ReadinessAction action
        +str reason
        +ReadinessLevel level
        +float coverage
        +bool illness_alert
        +bool composite_low
        +tuple observations
        +str applies_to_day
    }
    class Readiness {
        +ReadinessDecision decision
        +ReadinessObservation observation
    }
    class ReadinessObservation {
        +float hrv
        +float rhr
        +float sleep
        +str read_at
    }

    class ImpulseResponseEngine {
        +compute()
        +ctl_atl()
    }
    class TrainingLoadComponents {
        +float ctl
        +float atl
        +float tsb
    }

    class IntervalsClient {
        +get_events()
        +get_wellness()
        +get_activity()
        +get_streams()
        +create_events()
        +get_sport_settings()
    }
    class IntervalsApiError {
        +int status
        +str detail
    }
    class RideFtpEstimate {
        +float ftp
        +float ci
        +str method
    }

    class StimulusFamily {
        <<enumeration>>
        sweet_spot
        threshold
        vo2max
        endurance
        anaerobic
    }
    class ProgressionStep {
        +int repeats
        +int work_sec
        +float intensity
        +int recovery_sec
    }
    class CompletionScore {
        +float adherence
        +float intensity_ok
        +float total
    }
    class VO2Family {
        <<enumeration>>
        long_intervals
        short_intervals
        variable_intervals
    }
    class ProgressionLever {
        <<enumeration>>
        interval_duration
        repetitions
        total_work_time
        intensity
    }
    class VO2Workout {
        +VO2Family family
        +int interval_duration
        +int repetitions
        +tuple work_power_range
        +int recovery_duration
        +int total_work_time
        +int progression_step
        +ProgressionLever lever
    }

    class AdaptationState {
        +float aerobic_base
        +float threshold
        +float vo2max
        +float muscular_endurance
        +float anaerobic
        +float neuromuscular
    }
    class CriticalPowerProfile {
        +float critical_power
        +float w_prime
        +CPProtocol protocol
        +CPConfidence confidence
        +tuple test_dates
    }
    class AthletePhysiologicalProfile {
        +int ftp
        +FtpSource ftp_source
        +float ftp_confidence
    }
    class FtpSource {
        <<enumeration>>
        user
        ftp20
        ftp60
        ramp
        cp_estimate
        performance_estimate
    }
    class TrainingPhase {
        <<enumeration>>
        base
        build
        specific
        peak
        recovery
        test
    }
    class PhaseState {
        +TrainingPhase phase
        +int week
    }
    class TrainingDecision {
        +str goal
        +str phase
        +str primary_adaptation
        +str workout_family
        +int progression_step
        +int planned_duration
    }
    class IntensityDistributionModel {
        +float z1_minutes
        +float z2_minutes
        +float z3_minutes
        +float z4_minutes
        +float z5_minutes
    }
    class FamilyProfile {
        +str family
        +tuple band
        +ZoneLever lever
    }
    class ZoneLever {
        <<enumeration>>
        duration
        total_volume
        repetitions
        recovery
    }

    PlannedWorkout --> WorkoutParams : params (dict, contrato persistido)
    TrainingPlanState --> PlannedWorkout : workouts
    TrainingPlanState --> ReadinessEligibility : elegibilidade por dia
    Metrics --> TrainingLoadComponents : TSB/CTL/ATL
    ImpulseResponseEngine ..> TrainingLoadComponents : produz
    IntervalsClient ..> IntervalsApiError : levanta

    Readiness --> ReadinessDecision : decision
    Readiness --> ReadinessObservation : observation
    ReadinessDecision --> ReadinessAction : action
    ReadinessDecision --> ReadinessLevel : level
    ReadinessDecision ..> ReadinessEligibility : is_adaptive + applies_to_day
    ReadinessDecision --> WorkoutParams : REDUCE preserva focus
    PlannedWorkout --> ReadinessAssessment : 7 eixos lidos do wellness

    ProgressionStep --> StimulusFamily : pertence a
    CompletionScore ..> ProgressionStep : avaliado contra
    VO2Workout --> VO2Family : family
    VO2Workout --> ProgressionLever : lever
    VO2Workout ..> WorkoutParams : 4x4 / 5x3 / 3x5

    TrainingDecision --> TrainingPhase : phase
    TrainingPhase --> PhaseState : state
    TrainingDecision --> FamilyProfile : workout_family
    FamilyProfile --> ZoneLever : lever
    TrainingDecision ..> ProgressionStep : progression_step
    TrainingDecision ..> AthletePhysiologicalProfile : FTP
    AdaptationState ..> TrainingDecision : adaptações
    CriticalPowerProfile ..> TrainingDecision : CP/W' (fora da publicação)
    IntensityDistributionModel ..> TrainingDecision : minutos por zona
```

---

## 5. Diagrama de atividades — build, check --apply e push

Fluxo do `build`: do histórico ao plano publicado.

```mermaid
flowchart TD
    subgraph BUILD["1. build — monta o plano (não lê wellness)"]
        direction TB
        A["GET /events (histórico)"] --> B["latest_metrics → TSB atual"]
        B --> C{"PERIODIZATION no .env?"}
        C -- "sim" --> D["PERIODIZATION_TEMPLATES[p]<br/>(polarized|pyramidal|undulating|linear|block)"]
        C -- "não" --> E{"GOAL no .env?"}
        E -- "não" --> F["WEEKLY_BY_TSB<br/>(padrão por TSB)"]
        E -- "sim" --> G["GOAL_TEMPLATES[goal]<br/>(ex.: race exige RACE_DATE)"]
        D --> H["escolhe template semanal<br/>pela faixa de TSB"]
        F --> H
        G --> H
        H --> I["preenche slots de TREINO<br/>(TRAINING_DAYS)"]
        I --> J{"WEEKLY_HOURS?"}
        J -- "sim" --> K["escala on_sec<br/>(0.5x–1.5x, min 120s)"]
        J -- "não" --> L["sem ajuste de volume"]
        K --> M{"LONG_DAY?"}
        L --> M
        M -- "sim" --> N["rotaciona ciclo → treino longo<br/>no dia preferido (ou mais próximo)"]
        M -- "não" --> O["posição natural do foco"]
        N --> P["_fit_budget: TSS 7d ≤ cap×7<br/>(encurta on_sec, depois on_power)"]
        O --> P
        P --> Q["grava plan.json<br/>(preserva treino de hoje + meta)"]
    end

    subgraph CHECK["2. check --apply — depois do build, antes do push"]
        direction TB
        RD["GET /wellness (janela 7d)<br/>+ sport-settings"]
        RD --> RA["readiness_assessment.py<br/>7 eixos · ausência = None<br/>coverage = observados / 7"]
        RA --> RL{"level()"}
        RL -- "GREEN" --> RN["NONE<br/>plano intacto"]
        RL -- "YELLOW" --> RU["REDUCE"]
        RL -- "RED" --> RP2["REDUCE<br/>(alerta de doença pode virar REPLACE)"]
        RU --> RE["_reduce_for_readiness<br/>preserva focus, tipo e ordem dos segmentos<br/>reduz volume ANTES de intensidade<br/>nunca abaixo do piso da zona"]
        RP2 --> RE
        RE --> RG{"sessão elegível?<br/>(foco + dia + leitura do dia)"}
        RG -- "não" --> RN2["nada adaptado<br/>motivo impresso no CLI"]
        RG -- "sim" --> RW["reescreve o dia no plan.json<br/>+ nota (prontidão dirigiu?)"]
    end

    Q -.-> RD
    RN -.-> PUB
    RN2 -.-> PUB
    RW --> PUB["3. push → POST /events/bulk?upsert=true<br/>(limpa órfãos antes)"]
```

---

## 6. Diagrama de estados — ciclo de vida de um evento de treino

```mermaid
stateDiagram-v2
    [*] --> Planejado : build + push (external_id hermes-plan-*)

    Planejado --> Feito : atividade pareada (paired_activity_id)
    Planejado --> Perdido : passa do dia + sem atividade

    Planejado --> NaoIniciado : horario planejado ainda nao passou
    Planejado --> EstadoDesconhecido : horario passou (START_TIME 07:30)<br/>e o Intervals nao confirma realizacao
    NaoIniciado --> Concluida : atividade pareada
    EstadoDesconhecido --> Concluida : realizacao confirmada depois

    Planejado --> Reduzido : check --apply, REDUCE<br/>foco e zona preservados, dose reduzida
    NaoIniciado --> Reduzido : check --apply, REDUCE
    Reduzido --> Concluida : treino executado

    Reduzido --> Trocado : REPLACE (readiness + sem TSB forcado)

    Perdido --> Ajustado : reconcile absorve pelo orçamento<br/>eleva Z2/SweetSpot até o teto<br/>sem trocar por recuperação
    Perdido --> Debito : falta de alta intensidade<br/>(Limiar/VO2) não se substitui<br/>com volume
    Debito --> Ajustado : build reprioriza intensidade<br/>pelo TSB real

    Planejado --> Extra : atividade fora do plano (não-hermes)
    Extra --> Leve : carga ok → plano mantido
    Extra --> Pesado : carga ≥ cap diário (7d)
    Pesado --> Ajustado : recuperação + limiar

    Ajustado --> Feito : treino executado
    Trocado --> Feito : treino executado

    Perdido --> [*] : fim da janela do plano
    Feito --> [*]
    Concluida --> [*]
```

---

## Notas

- Diagramas gerados a partir do código real (`src/*.py`, suíte 793 OK) — não são
  genéricos. Se o código mudar, atualize aqui junto.
- Fontes em `docs/diagramas/*.mmd`; os `.png` são regenerados com mermaid-cli
  (`npx @mermaid-js/mermaid-cli -i X.mmd -o X.png -b white -s 1`, com
  `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium`). Os blocos `mermaid` deste
  arquivo são gerados a partir dos `.mmd`, então o índice não diverge do fonte:
  edite o `.mmd`, regenere o PNG e sincronize o bloco.
- **O diagrama de classes é curado, não completo.** Entram só as entidades com
  contrato verificado por teste ou que vivem em formato persistido/externo
  (`plan.json`, payload do Intervals, `.env`). `src/` tem ~47 dataclasses; o
  critério está no cabeçalho de `classes.mmd`. **O diagrama de componentes marca
  os 10 módulos fora da publicação** (`OFF`), que `build`/`push` não importam —
  item 58 do `ROADMAP`, ainda aberto. Um diagrama que mostra só o que funciona
  é propaganda, não arquitetura.
- O `.zwo` **não é gerado localmente** (o Intervals monta no app a partir do
  texto de `description`).
- `plan.json` guarda a meta (goal, race_date, ftp_test_date, ftp_candidates)
  além dos treinos — o `reconcile` reescreve os dias sem mudar o tamanho do plano.
- A periodização (`PERIODIZATION`) é lida do `.env` no momento do `build` —
  não fica persistida na meta do `plan.json`.
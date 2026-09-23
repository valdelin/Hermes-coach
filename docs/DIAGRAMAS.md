# Diagramas UML — Hermes Coach

Diagramas em [Mermaid](https://mermaid.js.org) do sistema real (v0.0.20).
Renderizam nativo no Obsidian (bloco ` ```mermaid `) e no GitHub.

Legenda rápida dos módulos:

| Módulo | Responsabilidade |
|---|---|
| `src/training_plan.py` | CLI: `info` / `ftp-check` / `ftp-scan` / `model` / `build` / `reconcile` / `push` / `all` |
| `src/coach.py` | Métricas (TSB/CTL/ATL), foco do dia, prescrição (`WorkoutParams`), TSS estimado |
| `src/plan.py` | Plano semanal (`build_plan`), ajuste por carga (`_fit_budget`), `reconcile`, texto do treino, `event_payload` |
| `src/impulse_response.py` | Motor Banister local (CTL/ATL/TSB) + séries diárias de TSS |
| `src/intervals_client.py` | Cliente da API do Intervals.icu (events, wellness, activities, streams, sport-settings) |
| `src/ftp_scan.py` / `ftp_estimation.py` | Análise de treinos fora do plano → proposta de FTP (20min × 0,95) |
| `plan.json` | Estado local do plano (treinos + meta: goal, race_date, ftp_candidates) |
| `scripts/daily_reconcile.sh` | Timer systemd: reconcile + push à meia-noite |

---

## 1. Diagrama de componentes (visão geral)

```mermaid
flowchart LR
    subgraph CLI["CLI — src/training_plan.py"]
        CMD["info | ftp-check | ftp-scan | model<br/>build | reconcile | push | all"]
    end

    subgraph CORE["Motor de coaching"]
        COACH["coach.py<br/>métricas · foco · prescrição"]
        PLAN["plan.py<br/>build_plan · reconcile · event_payload"]
        IR["impulse_response.py<br/>CTL/ATL/TSB local"]
        FTPS["ftp_scan.py + ftp_estimation.py<br/>proposta de FTP"]
    end

    subgraph API["intervals_client.py"]
        CLIENT["IntervalsClient<br/>events · wellness · activities · streams · sport-settings"]
    end

    ENV[".env<br/>credenciais · FTP · agenda · GOAL"]
    PLANFILE["plan.json<br/>plano + meta"]
    SH["scripts/daily_reconcile.sh<br/>(timer systemd meia-noite)"]

    INTERVALS["Intervals.icu API"]
    APPS["Zwift / Garmin / Wahoo<br/>(atividades + .zwo)"]

    CMD --> COACH
    CMD --> PLAN
    CMD --> FTPS
    COACH --> IR
    CMD --> CLIENT
    PLAN --> PLANFILE
    COACH --> ENV
    PLAN --> ENV
    CLIENT --> INTERVALS
    INTERVALS <--> APPS
    SH --> CMD
```

---

## 2. Sequência — fluxo diário automático (timer de meia-noite)

```mermaid
sequenceDiagram
    participant T as systemd timer<br/>cycling-coach-daily
    participant S as daily_reconcile.sh
    participant C as CLI<br/>training_plan.py
    participant I as Intervals.icu API
    participant P as plan.json

    T->>S: meia-noite (daily)
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
        C->>I: DELETE /events/bulk-delete (órfãos)
        C->>I: POST /events/bulk?upsert=true (treinos)
        I-->>C: 200 OK
        C-->>S: calendário atualizado
        S-->>T: sucesso
    end
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
    C->>C: build_plan (GOAL + WEEKLY_BY_TSB +<br/>WEEKLY_HOURS + LONG_DAY + budget TSS)
    Note over C: preserva treino de hoje<br/>do plano anterior
    C->>P: salva plan.json (treinos + meta)

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

## 4. Diagrama de classes (entidades principais)

```mermaid
classDiagram
    class Metrics {
        +float tsb
        +float ctl
        +float atl
        +float tss
        +float ftp
        +str day
    }
    class WorkoutParams {
        +str focus
        +int warmup_sec = 600
        +int repeats
        +int on_sec
        +int off_sec
        +float on_power
        +float off_power
        +int cooldown_sec = 600
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
    class IntervalsClient {
        -str base
        -tuple auth
        +events(params)
        +wellness(params)
        +create_events(payloads, upsert)
        +delete_events(external_ids)
        +activity(activity_id)
        +activity_streams(activity_id, types)
        +sport_settings()
        +put_sport_settings(id, payload)
    }
    class ImpulseResponseEngine {
        +compute_metrics(tss_series)
    }
    class plan_build_plan {
        +build_plan(events, tsb, ftp, days, ...)
        +reconcile(plan, events, ftp, ...)
        +event_payload(workout, ftp, lang, prev, fthr)
        +orphan_external_ids(plan, events, start)
    }
    class FTPScan {
        +extra_activities(events)
        +skip_reason(activity, ftp)
        +estimate_ride(...)
        +best_candidate(candidates)
        +ride_settings(settings)
    }

    IntervalsClient --> Metrics : retorna eventos
    plan_build_plan --> PlannedWorkout : gera
    plan_build_plan --> WorkoutParams : usa templates
    ImpulseResponseEngine --> Metrics : computa local
    FTPScan --> IntervalsClient : streams + atividades
```

---

## 5. Diagrama de atividades — decisão de foco e geração do treino

Fluxo do `build`: do histórico ao plano publicado.

```mermaid
flowchart TD
    A["GET /events (histórico)"] --> B["latest_metrics → TSB atual"]
    B --> C{"GOAL no .env?"}
    C -- "não" --> D["WEEKLY_BY_TSB<br/>(padrão por TSB)"]
    C -- "sim" --> E["GOAL_TEMPLATES[goal]<br/>(ex.: race exige RACE_DATE)"]

    D --> F["escolhe template semanal<br/>pela faixa de TSB"]
    E --> F
    F --> G["preenche slots de TREINO<br/>(TRAINING_DAYS)"]
    G --> H{"WEEKLY_HOURS?"}
    H -- "sim" --> I["escala on_sec<br/>(0.5x–1.5x, min 120s)"]
    H -- "não" --> J["sem ajuste de volume"]
    I --> K{"LONG_DAY?"}
    J --> K
    K -- "sim" --> L["rotaciona ciclo → treino longo<br/>no dia preferido (ou mais próximo)"]
    K -- "não" --> M["posição natural do foco"]
    L --> N["_fit_budget: TSS 7d ≤ cap×7<br/>(encurta on_sec, depois on_power)"]
    M --> N
    N --> O["salva plan.json<br/>(preserva treino de hoje + meta)"]
    O --> P["push → POST /events/bulk?upsert=true<br/>(limpa órfãos antes)"]
```

---

## 6. Diagrama de estados — ciclo de vida de um evento de treino

```mermaid
stateDiagram-v2
    [*] --> Planejado : build + push (external_id hermes-plan-*)
    Planejado --> Feito : atividade pareada (paired_activity_id)
    Planejado --> Perdido : passa do dia + sem atividade
    Perdido --> Ajustado : reconcile insere recuperação<br/>e reduz próximo Limiar -5%
    Planejado --> Extra : atividade fora do plano (não-hermes)
    Extra --> Leve : carga ok → plano mantido
    Extra --> Pesado : carga ≥ cap diário (7d)
    Pesado --> Ajustado : recuperação + limiar
    Ajustado --> Feito : treino executado
    Perdido --> [*] : fim da janela do plano
    Feito --> [*]
```

---

## Notas

- Diagramas gerados a partir do código real (`src/*.py`, v0.0.20, 216 testes OK) —
  não são genéricos. Se o código mudar, atualize aqui junto.
- O `.zwo` **não é gerado localmente** (o Intervals monta no app a partir do
  texto de `description`).
- `plan.json` guarda a meta (goal, race_date, ftp_test_date, ftp_candidates)
  além dos treinos — o `reconcile` reescreve os dias sem mudar o tamanho do plano.
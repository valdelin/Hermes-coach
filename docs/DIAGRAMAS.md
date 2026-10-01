# Diagramas UML — Hermes Coach

Diagramas em [Mermaid](https://mermaid.js.org) do sistema real (v0.0.29).
Renderizam nativo no Obsidian (bloco ` ```mermaid `) e no GitHub. Os `.mmd`
fonte vivem em `docs/diagramas/` (geram os `.png` via mermaid-cli).

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
| `src/readiness.py` | Prontidão do dia (`check`): sinais de wellness (RHR/HRV/sono) → sugestão de troca por recuperação + alerta de início de doença (+ `COACH_WEBHOOK`) |
| `src/periodization.py` | Explicação dos 5 modelos de periodização (`periodization`): o que significam para o atleta + sugestão por GOAL/TSB (top/evitar) |
| `src/activity_summary.py` | Resumo dos treinos feitos por dia/semana/mês (`summary`) |
| `src/charts.py` | Gráficos em texto: PMC trailing 90d + carga semanal (TSS/ISO) |
| `src/report.py` | Relatório com gráficos SVG: HTML direto / PDF via chromium headless (`--export`) |
| `src/brand.py` | Identidade: 22 temas (Omarchy quattro) + tokens de cor por tema |
| `plan.json` | Estado local do plano (treinos + meta: goal, race_date, ftp_candidates) |
| `scripts/daily_reconcile.sh` | Timer systemd: reconcile + push à meia-noite |

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

    ENV[".env<br/>credenciais · FTP · agenda · GOAL · PERIODIZATION<br/>COACH_WEBHOOK (alerta doença)"]
    PLANFILE["plan.json<br/>plano + meta"]
    SH["scripts/daily_reconcile.sh<br/>(timer systemd meia-noite)"]

    INTERVALS["Intervals.icu API"]
    APPS["Zwift / Garmin / Wahoo<br/>(atividades + .zwo)"]
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
    CLIENT --> INTERVALS
    INTERVALS <--> APPS
    SH --> CMD
    RP --> CH
    RP --> BR
    RP --> PDF
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
    C->>C: detecta perdidos/extras<br/>perdido → absorve no orçamento<br/>extra pesado → recuperação
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
        +int warmup_cadence = 90
        +float warmup_power_low = 0.45
        +float warmup_power_high = 0.75
        +int repeats
        +int on_sec
        +int off_sec
        +float on_power
        +float off_power
        +int cadence = 90
        +int cadence_rest = 85
        +int cooldown_sec = 600
        +int cooldown_cadence = 85
        +float cooldown_power_low = 0.70
        +float cooldown_power_high = 0.45
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
    class Recovery {
        +fetch_full_history(client, ...)
        +actual_daily_load(events)
        +pmc_series(daily)
        +pmc_series_anchored(real_by_day, start, end)
        +state(rows, window_days)
        +calibrated_state(st, weekly_now)
        +weekly_volume(daily, days)
        +estimate_return(current_ctl, current_atl, target_ctl, weekly_now, ...)
        +ramp_schedule(target_ctl, weekly_now, ramp_pts, ...)
    }
    class Readiness {
        +dict signals
        +bool illness
        +str reason
        +bool has_data
        +assess_readiness(records, days)
        +suggest_swap(readiness, planned_today)
        +recovery_workout(day, ftp) -> PlannedWorkout
        +coach_alert_payload(atleta_id, readiness, today)
    }
    class Periodization {
        +list_models() -> list
        +describe(model) -> str
        +suggest_for_goal(goal, tsb) -> (top, avoid)
        +explain_current(goal, periodization, tsb) -> str
    }
    class SummaryAgg {
        +int sessions
        +float time_s
        +float distance_m
        +float elevation_m
        +float load
        +float avg_power
        +float np
        +int avg_hr
    }
    class ReportRenderer {
        +render_summary_html(title, start, end, agg, rows,<br/>pmc_rows, weeks, theme)
        +write(path, html)
        +export_pdf(path, html)
    }
    class ThemeKit {
        +str DEFAULT_THEME
        +dict THEMES
        +dict FORM_ZONE_COLORS
    }

    IntervalsClient --> Metrics : retorna eventos
    plan_build_plan --> PlannedWorkout : gera
    plan_build_plan --> WorkoutParams : usa templates
    ImpulseResponseEngine --> Metrics : computa local
    FTPScan --> IntervalsClient : streams + atividades
    Recovery --> IntervalsClient : eventos históricos
    Readiness --> IntervalsClient : wellness (RHR/HRV/sono)
    Readiness --> PlannedWorkout : recovery_workout (check --apply)
    Periodization --> Metrics : TSB atual (sugestao por GOAL)
    SummaryAgg <-- IntervalsClient : atividades pareadas
    ReportRenderer --> ThemeKit : 22 temas (CSS vars)
    ReportRenderer --> SummaryAgg : cards + tabela
    ReportRenderer --> Recovery : pmc_rows (PMC 90d)
```

---

## 5. Diagrama de atividades — decisão de foco e geração do treino

Fluxo do `build`: do histórico ao plano publicado.

```mermaid
flowchart TD
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
    P --> Q["salva plan.json<br/>(preserva treino de hoje + meta)"]
    Q --> R["push → POST /events/bulk?upsert=true<br/>(limpa órfãos antes)"]
```

---

## 6. Diagrama de estados — ciclo de vida de um evento de treino

```mermaid
stateDiagram-v2
    [*] --> Planejado : build + push (external_id hermes-plan-*)
    Planejado --> Feito : atividade pareada (paired_activity_id)
    Planejado --> Perdido : passa do dia + sem atividade
    Planejado --> Trocado : check --apply (prontidão abaixo)<br/>recuperação Z2 curta no lugar
    Perdido --> Ajustado : reconcile absorve pelo orçamento<br/>eleva Z2/SweetSpot até o teto<br/>sem trocar por recuperação
    Perdido --> Debito : falta de alta intensidade<br/>(Limiar/VO2) não se substitui<br/>com volume
    Debito --> Ajustado : build reprioriza intensidade<br/>pelo TSB real
    Planejado --> Extra : atividade fora do plano (não-hermes)
    Extra --> Leve : carga ok → plano mantido
    Extra --> Pesado : carga ≥ cap diário (7d)
    Pesado --> Ajustado : recuperação + limiar
    Ajustado --> Feito : treino executado
    Trocado --> Feito : recuperação executada
    Perdido --> [*] : fim da janela do plano
    Feito --> [*]
```

---

## Notas

- Diagramas gerados a partir do código real (`src/*.py`, v0.0.29, 374 testes OK) —
  não são genéricos. Se o código mudar, atualize aqui junto.
- Fontes em `docs/diagramas/*.mmd`; os `.png` são regenerados com mermaid-cli.
- O `.zwo` **não é gerado localmente** (o Intervals monta no app a partir do
  texto de `description`).
- `plan.json` guarda a meta (goal, race_date, ftp_test_date, ftp_candidates)
  além dos treinos — o `reconcile` reescreve os dias sem mudar o tamanho do plano.
- A periodização (`PERIODIZATION`) é lida do `.env` no momento do `build` —
  não fica persistida na meta do `plan.json`.
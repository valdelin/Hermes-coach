# Arquitetura — conceito original do Hermes (referência / direção futura)

> **Status: parcialmente implementado.** A seção 1 (motor Impulse-Response)
> foi implementada em `src/impulse_response.py` (v0.0.8, CLI `model`). O
> restante (schema de estado e system prompt de corrida) continua como
> **conceito/direção futura** multi-esporte (corrida) — consulte o
> [README](../README.md) para o que roda hoje.
>
> Mantido em sincronia com o vault do Obsidian
> (`01-Projetos/hermes-coach/hermes_coach_arquitetura_e_implementa_o.md`).
> Fica como referência de design e direção futura (multi-esporte/corrida).

---

## Diferenças para o código atual (v0.0.8)

| Conceito do spec                                   | Implementação atual                                    |
|----------------------------------------------------|--------------------------------------------------------|
| Motor local Impulse-Response (Banister) em Python  | **Implementado** em `src/impulse_response.py` (CLI `model`); o fluxo principal (build/reconcile/push) continua usando CTL/ATL/TSB do Intervals.icu |
| TSS padrão: `IF² × horas × 100`                    | Motor usa a fórmula padrão; **o `plan.py` segue** com a estimativa aproximada `seg × fração³ / 36` para orçar o plano |
| Schema JSON de estado do atleta (`HermesAthleteState`) | Estado vive em `.env` + `plan.json` (sem schema dedicado) — seção 2 não implementada |
| System prompt de corrida (vDOT, pace/km, FC)       | Agente opencode `cycling-coach` (`.opencode/agent/cycling-coach.md`), ciclismo indoor (FTP em watts) — seção 3 não implementada |

---

## 1. Motor de Carga Fisiológica (Banister Impulse-Response)

**Status: IMPLEMENTADO** em `src/impulse_response.py` (v0.0.8, comando
`python3 src/training_plan.py model`). A implementação segue o código abaixo
fielmente e adiciona `daily_tss_series(events)` para montar a série diária de
TSS a partir dos eventos do Intervals (campo `tss` ou `icu_training_load`).

Implementação em Python para o cálculo de TSS (Training Stress Score) e
atualização contínua de Fitness (CTL), Fadiga (ATL) e Forma (TSB).

```python
import math
from typing import List, Dict

class ImpulseResponseEngine:
    def __init__(self, ctl_time_constant: int = 42, atl_time_constant: int = 7):
        self.tc_ctl = ctl_time_constant
        self.tc_atl = atl_time_constant

    def calculate_tss(self, duration_sec: int, avg_intensity: float, threshold: float) -> float:
        """
        Calcula o Training Stress Score (TSS).
        avg_intensity / threshold representa o Intensity Factor (IF).
        """
        if threshold <= 0:
            return 0.0
        intensity_factor = avg_intensity / threshold
        tss = (duration_sec * (avg_intensity * intensity_factor)) / (threshold * 3600) * 100
        return round(tss, 2)

    def compute_metrics(self, daily_tss_history: List[float], initial_ctl: float = 0.0, initial_atl: float = 0.0) -> Dict[str, float]:
        """
        Aplica o modelo Impulse-Response sobre o histórico diário de TSS.
        """
        ctl = initial_ctl
        atl = initial_atl

        for tss in daily_tss_history:
            ctl = ctl + (tss - ctl) * (1 - math.exp(-1 / self.tc_ctl))
            atl = atl + (tss - atl) * (1 - math.exp(-1 / self.tc_atl))

        tsb = ctl - atl

        return {
            "ctl_fitness": round(ctl, 1),
            "atl_fatigue": round(atl, 1),
            "tsb_form": round(tsb, 1)
        }

if __name__ == "__main__":
    engine = ImpulseResponseEngine()

    # Exemplo: 60 min a 95% do limiar
    tss_exemplo = engine.calculate_tss(duration_sec=3600, avg_intensity=0.95, threshold=1.0)
    print(f"TSS do Treino: {tss_exemplo}")

    # Histórico de 14 dias de TSS
    tss_14_dias = [45, 60, 0, 80, 50, 90, 0, 40, 70, 0, 85, 60, 100, 0]
    metricas = engine.compute_metrics(tss_14_dias)
    print(f"Métricas Atuais: {metricas}")
```

---

## 2. Schema JSON de Estado do Atleta

Estrutura de dados para manter o estado do atleta e o plano de treino
persistido.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HermesAthleteState",
  "type": "object",
  "properties": {
    "athlete_id": { "type": "string" },
    "thresholds": {
      "type": "object",
      "properties": {
        "vDOT": { "type": "number" },
        "threshold_pace_sec_km": { "type": "integer" },
        "lthr_bpm": { "type": "integer" },
        "max_hr_bpm": { "type": "integer" }
      },
      "required": ["threshold_pace_sec_km", "lthr_bpm"]
    },
    "pacing_zones": {
      "type": "object",
      "properties": {
        "z1_recovery": { "type": "string" },
        "z2_aerobic": { "type": "string" },
        "z3_tempo": { "type": "string" },
        "z4_threshold": { "type": "string" },
        "z5_interval": { "type": "string" }
      }
    },
    "current_load": {
      "type": "object",
      "properties": {
        "ctl": { "type": "number" },
        "atl": { "type": "number" },
        "tsb": { "type": "number" },
        "last_updated": { "type": "string", "format": "date" }
      }
    },
    "active_plan": {
      "type": "object",
      "properties": {
        "goal_event": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "distance": { "type": "string" },
            "target_date": { "type": "string", "format": "date" }
          }
        },
        "current_phase": {
          "type": "string",
          "enum": ["Base", "Build", "Peak", "Taper", "Recovery"]
        },
        "max_weekly_ramp_rate": { "type": "number", "default": 1.10 }
      }
    }
  },
  "required": ["athlete_id", "thresholds", "current_load", "active_plan"]
}
```

---

## 3. System Prompt para o Agente de IA

```text
Você é o Hermes, um assistente especializado e treinador virtual de corrida de alto rendimento. Seu objetivo é prescrever, ajustar e analisar treinos combinando rigor fisiológico com comunicação motivadora e direta.

DIRETRIZES DE ATUAÇÃO E GUARDRAILS:
1. NUNCA invente ritmos ou zonas de intensidade sem consultar o perfil e os limiares atuais do atleta.
2. TODA alteração de plano deve respeitar a taxa de rampagem semanal (máximo de 10% de aumento de volume em relação à semana anterior).
3. Se a métrica TSB (Training Stress Balance) do atleta estiver abaixo de -30 (risco de overtraining) ou o feedback de dor muscular (rPE/Recovery) for superior a 7/10, REDUZA imediatamente a intensidade da sessão do dia para Z1 (Regenerativo) ou prescreva descanso total.
4. Prescreva treinos em estrutura clara e parsed pelo motor de treinos:
   - Aquecimento (Distância/Tempo + Zona)
   - Bloco Principal (Repetições x Distância/Tempo + Zona + Intervalo)
   - Desaquecimento (Distância/Tempo + Zona)

FERRAMENTAS DISPONÍVEIS:
- Use `get_athlete_metrics()` antes de sugerir ou modificar treinos.
- Use `recalculate_mesocycle()` caso o atleta perca mais de 3 dias seguidos de treino por doença ou viagem.
- Use `export_workout_file()` sempre que o atleta pedir o treino estruturado para dispositivo relógio/GPS.

Responda com precisão técnica, focado em consistência de longo prazo e prevenção de lesões.
```

---

## Notas de design aproveitáveis no núcleo de ciclismo

- A **rampagem semanal (max +10% de volume)** e o **guardrail de TSB < -30
  (overreaching)** do prompt acima são regras candidatas para o núcleo atual
  (hoje o orçamento semanal de TSS já limita a carga, mas não há teto explícito
  de TSB nem regra de rampagem de volume).
- As metas de prova/período (`Base → Build → Peak → Taper → Recovery`) e o
  `max_weekly_ramp_rate` do schema são o modelo de **periodização** que o
  plano semanal por TSB ainda não cobre (o ciclo atual decide só o foco da
  semana, sem fases).
# 🚴‍♂️ Guia Técnico & Análise de Código — Hermes Coach

**Data:** 25/09/2026  
**Repositório:** [valdelin/Hermes-coach](https://github.com/valdelin/Hermes-coach)  
**Objetivo:** Relatório de análise do projeto e o código-fonte refatorado com correções de segurança, tratamento de erros de rede e padronização de datas.

---

## ✅ Resoluções das Propostas (26/09/2026)

Veredito ponto a ponto após revisão do código atual (Hermes Coach v0.0.26):

| Proposta | Status | Motivo |
|---|---|---|
| **A. Segurança/Histórico do Git** | **Já resolvido** — não aplicado | O `.env` nunca foi commitado (só `.env.example` com placeholder `sua_api_key_aqui`); `.gitignore` cobre `.env`; verificado em 105 commits. **Não precisa revogar a chave.** |
| **B. Tratamento de erros de rede** | **APLICADO (v0.0.26)** | `IntervalsClient` ganhou retry/backoff exponencial (0.5s→1.0s→2.0s) para `ConnectionError`/`Timeout` e HTTP 429/5xx; `IntervalsApiError` com mensagem amigável na CLI. +15 testes. |
| **C. Comparação de Datas/Timezones** | **Já resolvido** — não aplicado | O código (e o `reconcile`) só comparam datas por `date.fromisoformat(str(...)[:10])` — nunca `datetime` naive vs aware. Sem `TypeError` possível. |
| **D. `print()` → `logging`** | **Não aplicado** (motivo técnico) | CLI é interativa e o timer diário já redireciona para `logs/daily_reconcile.log` com timestamp do shell + `notify-send` em falha. Trocar por `logging` não traria ganho — manteria a mesma saída. |
| **Parte 2 — `zwift_auto_adjust.py`** | **Não aplicado** (superado pela arquitetura atual) | Script monolítico antigo: FTP hardcoded (181), `BASE_URL` com markdown corrompido, envia `workout_doc`/`steps` (padrão atual: Intervals monta o treino pela `description`), agenda fixa Ter/Qui/Sáb (atual: `TRAINING_DAYS` + orçamento de TSS no `reconcile`). O fluxo `plan.json` → `build` → `reconcile` → `push` já cobre o objetivo. |

**Conclusão:** apenas **B** foi aplicado (commits `4ec6463`/`b471fdb`, release v0.0.26).
O arquivo abaixo mantém o relatório original para contexto.

---

## 📄 Parte 1: Relatório de Análise Técnica

### 🌟 1. Pontos Fortes
- **Modularização:** Boa evolução do script monolítico para classes reutilizáveis (`IntervalsClient`, `TrainerManager`, `NotificationManager`).
- **Uso de POO:** Encapsulamento correto da lógica da API do Intervals.icu, evitando código duplicado.
- **Segurança Inicial:** Adoção correta da biblioteca `python-dotenv` para leitura de credenciais a partir do ficheiro `.env`.

---

### 🚨 2. Pontos Críticos e Alertas

#### 🔑 A. Segurança e Histórico do Git
- **Risco:** Se a chave da API do Intervals.icu ou *tokens* de mensagens foram commitados no histórico do Git antes da migração para o `.env`, eles ainda estão acessíveis nos commits antigos.
- **Ação:** Revogar e gerar uma nova chave no painel do Intervals.icu.

#### ⚡ B. Tratamento de Erros e Resiliência
- **Risco:** O uso direto de `resp.raise_for_status()` sem blocos `try-except` faz com que falhas temporárias de rede interrompam totalmente a execução do script.
- **Ação:** Tratar exceções do `requests` e implementar estratégias de *retry* ou falha graciosa.

#### 🕒 C. Comparação de Datas e Timezones
- **Risco:** Strings ISO vindas da API do Intervals.icu podem conter *offset* de fuso horário (ex: `+00:00`), enquanto `datetime.now()` cria objetos *naive* (sem fuso horário definido).
- **Sintoma:** Gera o erro `TypeError: can't compare offset-naive and offset-aware datetimes`.
- **Ação:** Normalizar todas as comparações extraindo apenas a data (`.date()`) ou convertendo para `datetime.now(timezone.utc)`.

---

### 📋 3. Oportunidades de Melhoria

#### 📝 Substituição de `print()` por `logging`
Para scripts executados via *cron* ou em background, o uso da biblioteca nativa `logging` é superior por permitir:
- Gravação de logs em ficheiro (`hermes.log`).
- Formatação automática com carimbo de data/hora.
- Separação por níveis de severidade (`INFO`, `WARNING`, `ERROR`).

---

## 🛠️ Parte 2: Código Refatorado (`zwift_auto_adjust.py`)

Abaixo está o código do script com todas as correções aplicadas:
- Leitura segura de variáveis de ambiente (`dotenv`).
- Substituição de `print()` por `logging`.
- Tratamento de exceções HTTP.
- Normalização de datas para evitar erros de timezone.

```python
#!/usr/bin/env python3
"""
Auto-adjustment script for Intervals.icu training plan.
Monitors completed workouts, compares planned vs actual, and adjusts future workouts.
Run daily via cron or manually after rides.
"""

import os
import sys
import json
import base64
import logging
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()

# ========== CONFIGURAÇÃO DE LOGS ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("hermes.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ========== CONFIGURAÇÃO DE VARIÁVEIS ==========
ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID", "376319")
API_KEY = os.getenv("INTERVALS_API_KEY")

if not API_KEY:
    logging.critical("INTERVALS_API_KEY não foi encontrada nas variáveis de ambiente nem no ficheiro .env!")
    sys.exit(1)

FTP = int(os.getenv("ATHLETE_FTP", 181))
BASE_URL = f"[https://intervals.icu/api/v1/athlete/](https://intervals.icu/api/v1/athlete/){ATHLETE_ID}"

AUTH_STR = base64.b64encode(f"API_KEY:{API_KEY}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH_STR}", "Content-Type": "application/json"}

PLAN_STATE_FILE = os.path.expanduser("~/zwift_plan_state.json")

TYPE_NAMES = {
    "recovery": "Recovery",
    "endurance": "Endurance",
    "tempo": "Tempo",
    "sweet_spot": "SweetSpot",
    "vo2max": "VO2max",
    "threshold": "Threshold"
}

# ========== HELPERS ==========
def parse_date(date_str):
    """Extrai apenas a parte da data (YYYY-MM-DD) para evitar conflitos de fuso horário"""
    if "T" in date_str:
        date_str = date_str.split("T")[0]
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def load_state():
    if os.path.exists(PLAN_STATE_FILE):
        try:
            with open(PLAN_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Erro ao carregar o estado do ficheiro: {e}")
    return {"events": {}, "adjustments": []}

def save_state(state):
    try:
        with open(PLAN_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Erro ao guardar o estado no ficheiro: {e}")

def api_request(method, endpoint, params=None, data=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, headers=HEADERS, params=params, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição API [{method} {endpoint}]: {e}")
        return None

def api_get(endpoint, params=None):
    return api_request("GET", endpoint, params=params)

def api_put(endpoint, data):
    return api_request("PUT", endpoint, data=data)

def api_post(endpoint, data):
    return api_request("POST", endpoint, data=data)

def api_delete(endpoint):
    return api_request("DELETE", endpoint)

# ========== WORKOUT BUILDER ==========
def build_workout_doc(workout_type, duration_min, tss_target=None):
    if workout_type == "recovery":
        steps = [
            {"power": {"units": "%ftp", "value": 45}, "duration": 600},
            {"power": {"units": "%ftp", "value": 60}, "duration": (duration_min - 20) * 60},
            {"power": {"units": "%ftp", "value": 35}, "duration": 600}
        ]
    elif workout_type == "endurance":
        warmup = 15 if duration_min >= 90 else 10
        cooldown = 15 if duration_min >= 90 else 10
        main = duration_min - warmup - cooldown
        steps = [
            {"power": {"units": "%ftp", "value": 55}, "duration": warmup * 60},
            {"power": {"units": "%ftp", "value": 68 if duration_min < 90 else 70}, "duration": main * 60},
            {"power": {"units": "%ftp", "value": 40}, "duration": cooldown * 60}
        ]
    elif workout_type == "tempo":
        steps = [
            {"power": {"units": "%ftp", "value": 55}, "duration": 600},
            {"power": {"units": "%ftp", "value": 75}, "duration": 600},
            {"power": {"units": "%ftp", "value": 80}, "duration": 600},
            {"power": {"units": "%ftp", "value": 75}, "duration": 600},
            {"power": {"units": "%ftp", "value": 40}, "duration": 600}
        ]
    elif workout_type == "sweet_spot":
        steps = [
            {"power": {"units": "%ftp", "value": 60}, "duration": 600},
            {"power": {"units": "%ftp", "value": 88}, "duration": 900},
            {"power": {"units": "%ftp", "value": 55}, "duration": 300},
            {"power": {"units": "%ftp", "value": 88}, "duration": 900},
            {"power": {"units": "%ftp", "value": 40}, "duration": 600}
        ]
    elif workout_type == "vo2max":
        steps = [
            {"power": {"units": "%ftp", "value": 65}, "duration": 900},
            {"power": {"units": "%ftp", "value": 110}, "duration": 180},
            {"power": {"units": "%ftp", "value": 50}, "duration": 180},
            {"power": {"units": "%ftp", "value": 110}, "duration": 180},
            {"power": {"units": "%ftp", "value": 50}, "duration": 180},
            {"power": {"units": "%ftp", "value": 110}, "duration": 180},
            {"power": {"units": "%ftp", "value": 50}, "duration": 180},
            {"power": {"units": "%ftp", "value": 110}, "duration": 180},
            {"power": {"units": "%ftp", "value": 40}, "duration": 600}
        ]
    elif workout_type == "threshold":
        steps = [
            {"power": {"units": "%ftp", "value": 70}, "duration": 900},
            {"power": {"units": "%ftp", "value": 95}, "duration": 600},
            {"power": {"units": "%ftp", "value": 55}, "duration": 300},
            {"power": {"units": "%ftp", "value": 95}, "duration": 600},
            {"power": {"units": "%ftp", "value": 55}, "duration": 300},
            {"power": {"units": "%ftp", "value": 95}, "duration": 600},
            {"power": {"units": "%ftp", "value": 40}, "duration": 600}
        ]
    else:
        steps = [{"power": {"units": "%ftp", "value": 60}, "duration": duration_min * 60}]
    
    total_duration = sum(s["duration"] for s in steps)
    return {
        "steps": steps,
        "locales": [],
        "options": {},
        "distance": 0,
        "duration": total_duration,
        "description": f"Auto-adjusted {workout_type} workout",
        "zoneTimes": []
    }

def estimate_tss(workout_type, duration_min, intensity_factor=None):
    if_intensity = {
        "recovery": 0.55,
        "endurance": 0.68,
        "tempo": 0.77,
        "sweet_spot": 0.88,
        "threshold": 0.95,
        "vo2max": 1.05
    }
    if_val = intensity_factor or if_intensity.get(workout_type, 0.7)
    return round((duration_min / 60) * (if_val ** 2) * 100)

# ========== CORE LOGIC ==========
def fetch_recent_activities(days=14):
    end = datetime.now()
    start = end - timedelta(days=days)
    params = {
        "oldest": start.strftime("%Y-%m-%d"),
        "newest": end.strftime("%Y-%m-%d")
    }
    events = api_get("/events", params) or []
    completed = []
    for e in events:
        if (e.get("category") != "WORKOUT" and 
            e.get("type") in ["Ride", "VirtualRide"] and
            e.get("icu_training_load") and
            e.get("start_date_local")):
            completed.append({
                "id": e["id"],
                "date": e["start_date_local"][:10],
                "tss": e["icu_training_load"],
                "name": e.get("name", ""),
                "moving_time": e.get("moving_time", 0),
                "avg_watts": e.get("average_watts"),
                "np": e.get("normalized_power"),
                "intensity": e.get("intensity"),
                "completed": True
            })
    return completed

def fetch_planned_workouts(days_ahead=60):
    end = datetime.now() + timedelta(days=days_ahead)
    start = datetime.now()
    params = {
        "oldest": start.strftime("%Y-%m-%d"),
        "newest": end.strftime("%Y-%m-%d")
    }
    events = api_get("/events", params) or []
    planned = []
    for e in events:
        if e.get("category") == "WORKOUT":
            planned.append({
                "id": e["id"],
                "uid": e.get("uid"),
                "date": e["start_date_local"][:10],
                "name": e.get("name", ""),
                "tss": e.get("icu_training_load", 0),
                "duration": e.get("moving_time", 0) // 60,
                "workout_doc": e.get("workout_doc", {}),
                "completed": False
            })
    return sorted(planned, key=lambda x: x["date"])

def match_completed_to_planned(completed, planned, window_days=2):
    matches = []
    unmatched_completed = []
    matched_planned_ids = set()
    now = datetime.now()
    
    today = now.date()
    missed_cutoff = today
    if now.hour >= 20:
        missed_cutoff = today + timedelta(days=1)
    
    for comp in completed:
        comp_date = parse_date(comp["date"])
        best_match = None
        best_diff = window_days + 1
        
        for plan in planned:
            if plan["id"] in matched_planned_ids:
                continue
            plan_date = parse_date(plan["date"])
            diff = abs((comp_date - plan_date).days)
            if diff <= window_days and diff < best_diff:
                best_diff = diff
                best_match = plan
        
        if best_match:
            matches.append({
                "planned": best_match,
                "completed": comp,
                "tss_diff": comp["tss"] - best_match["tss"],
                "date_diff": best_diff
            })
            matched_planned_ids.add(best_match["id"])
        else:
            unmatched_completed.append(comp)
    
    missed = [p for p in planned if p["id"] not in matched_planned_ids 
              and parse_date(p["date"]) < missed_cutoff]
    
    return matches, missed, unmatched_completed

def analyze_adherence(matches, missed):
    if not matches and not missed:
        return {"status": "no_data", "adherence_pct": 100.0, "missed_count": 0, "tss_deficit": 0, "avg_intensity_ratio": 1.0, "recommendation": "on_track"}
    
    total_planned_tss = sum(m["planned"]["tss"] for m in matches) + sum(m["tss"] for m in missed)
    total_actual_tss = sum(m["completed"]["tss"] for m in matches)
    adherence = total_actual_tss / total_planned_tss if total_planned_tss > 0 else 0
    
    missed_count = len(missed)
    tss_deficit = sum(m["tss"] for m in missed)
    
    avg_if_ratio = 1.0
    if matches:
        if_ratios = []
        for m in matches:
            planned_if = (m["planned"]["tss"] / (m["planned"]["duration"] / 60) / 100) ** 0.5 if m["planned"]["duration"] > 0 else 0.7
            actual_if = m["completed"].get("intensity", planned_if)
            if planned_if > 0:
                if_ratios.append(actual_if / planned_if)
        avg_if_ratio = sum(if_ratios) / len(if_ratios) if if_ratios else 1.0
    
    return {
        "status": "ok",
        "adherence_pct": round(adherence * 100, 1),
        "missed_count": missed_count,
        "tss_deficit": tss_deficit,
        "avg_intensity_ratio": round(avg_if_ratio, 2),
        "recommendation": get_recommendation(adherence, missed_count, avg_if_ratio)
    }

def get_recommendation(adherence, missed_count, intensity_ratio):
    if adherence >= 95 and missed_count == 0:
        return "on_track"
    elif adherence >= 80 and missed_count <= 1:
        return "minor_adjust"
    elif adherence >= 60 or missed_count <= 2:
        return "moderate_adjust"
    elif intensity_ratio > 1.15:
        return "reduce_intensity"
    else:
        return "major_adjust"

def apply_adjustments(analysis, planned_future):
    adjustments = []
    rec = analysis["recommendation"]
    
    if rec == "on_track":
        return adjustments
    
    if rec == "minor_adjust":
        tss_factor = 0.95
    elif rec == "moderate_adjust":
        tss_factor = 0.85
    elif rec == "reduce_intensity":
        tss_factor = 0.9
    else:
        tss_factor = 0.75
    
    cutoff = datetime.now().date() + timedelta(days=7)
    for plan in planned_future:
        plan_date = parse_date(plan["date"])
        if plan_date > cutoff:
            break
        
        wtype = "endurance"
        for key in TYPE_NAMES:
            if key in plan["name"].lower():
                wtype = key
                break
        
        new_duration = max(30, int(plan["duration"] * tss_factor))
        new_tss = estimate_tss(wtype, new_duration)
        
        new_doc = build_workout_doc(wtype, new_duration)
        new_name = f"{TYPE_NAMES[wtype]} {plan['date']}"
        
        update_data = {
            "name": new_name,
            "moving_time": new_duration * 60,
            "elapsed_time": new_duration * 60,
            "icu_training_load": new_tss,
            "workout_doc": new_doc
        }
        
        res = api_put(f"/events/{plan['id']}", update_data)
        if res:
            adjustments.append({
                "date": plan["date"],
                "old_name": plan["name"],
                "new_name": new_name,
                "old_tss": plan["tss"],
                "new_tss": new_tss,
                "old_duration": plan["duration"],
                "new_duration": new_duration,
                "reason": rec
            })
            logging.info(f"Ajustado: {plan['date']} {plan['name']} -> {new_name} ({plan['tss']}->{new_tss} TSS)")
        else:
            logging.error(f"Falha ao ajustar o treino {plan['name']}")
    
    return adjustments

def reschedule_missed(missed, planned_future):
    if not missed:
        return
    
    planned_dates = {p["date"] for p in planned_future}
    today = datetime.now().date()
    
    for missed_w in missed:
        for offset in range(1, 14):
            candidate = today + timedelta(days=offset)
            cand_str = candidate.strftime("%Y-%m-%d")
            if cand_str not in planned_dates and candidate.weekday() in [1, 3, 5]:
                wtype = "endurance"
                for key in TYPE_NAMES:
                    if key in missed_w["name"].lower():
                        wtype = key
                        break
                
                new_event = {
                    "start_date_local": f"{cand_str}T07:00:00",
                    "end_date_local": f"{cand_str}T08:00:00",
                    "name": f"{TYPE_NAMES[wtype]} {cand_str} (rescheduled)",
                    "type": "Ride",
                    "category": "WORKOUT",
                    "description": f"Rescheduled from {missed_w['date']}: {missed_w['name']}",
                    "icu_training_load": missed_w["tss"],
                    "moving_time": missed_w["duration"] * 60,
                    "elapsed_time": missed_w["duration"] * 60,
                    "indoor": True,
                    "workout_doc": build_workout_doc(wtype, missed_w["duration"])
                }
                result = api_post("/events", new_event)
                if result:
                    logging.info(f"Reagendado: {missed_w['name']} ({missed_w['date']}) -> {cand_str}")
                    planned_dates.add(cand_str)
                    break
                else:
                    logging.error(f"Falha ao reagendar {missed_w['name']}")

# ========== MAIN ==========
def main():
    logging.info("=== Zwift Plan Auto-Adjust Iniciado ===")
    
    state = load_state()
    
    completed = fetch_recent_activities(14)
    logging.info(f"Encontrados {len(completed)} treinos realizados")
    
    planned = fetch_planned_workouts(60)
    logging.info(f"Encontrados {len(planned)} treinos planeados")
    
    matches, missed, unmatched = match_completed_to_planned(completed, planned)
    logging.info(f"Correspondências: {len(matches)} | Faltas: {len(missed)} | Treinos Extra: {len(unmatched)}")
    
    analysis = analyze_adherence(matches, missed)
    logging.info(f"Aderência: {analysis.get('adherence_pct', 'N/A')}%")
    logging.info(f"Recomendação: {analysis.get('recommendation', 'N/A')}")
    
    today = datetime.now().date()
    future_planned = [p for p in planned if parse_date(p["date"]) > today]
    
    adjustments = apply_adjustments(analysis, future_planned)
    
    if missed:
        reschedule_missed(missed, future_planned)
    
    state["last_run"] = datetime.now().isoformat()
    state["last_analysis"] = analysis
    state["adjustments"].extend(adjustments)
    state["adjustments"] = state["adjustments"][-50:]
    save_state(state)
    
    logging.info("=== Execução Concluída ===")

if __name__ == "__main__":
    main()
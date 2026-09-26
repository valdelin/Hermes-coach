# 🚀 Hermes Coach — Product Roadmap & Vision

**Status Atual:** CLI Script / Automação Python (Single-tenant)  
**Objetivo Alvo:** Plataforma SaaS (*Software as a Service*) multi-tenant para autorregulação e prescrição inteligente de treinos baseada em fisiologia do exercício.

---

## 📌 Visão do Produto

O **Hermes Coach** foi concebido para automatizar a gestão de carga de treino para ciclistas e triatletas que utilizam o **Intervals.icu** e plataformas de treino virtual (como o Zwift). 

Em vez de aplicar planos rígidos, o algoritmo atua como um assistente técnico virtual: ele monitoriza o cumprimento diário (TSS e IF), analisa a aderência real vs. planeada e autorregula os treinos futuros para prevenir o *overreaching* e otimizar a evolução do atleta.

---

## 🏗️ Arquitetura Alvo (Evolução de Script para SaaS)

A versão atual do projeto evoluirá de um script local baseado em ficheiros (`.json` / `.env`) para uma infraestrutura na nuvem escalável e distribuída:

```text
[ Atleta (Dashboard Web / WhatsApp) ]
                 │
                 ▼
     [ Frontend Next.js / Bot ]
                 │
                 ▼
   [ API Backend (FastAPI / REST) ] <---> [ PostgreSQL (Dados & API Keys AES-256) ]
                 │
                 ▼
   [ Redis + Celery / Temporal ] (Workers Agendados para Processamento Diário)
                 │
                 ▼
    [ API do Intervals.icu ]
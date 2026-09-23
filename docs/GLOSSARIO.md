# Glossário — Hermes Coach

Vocabulário de acrônimos e métricas do projeto. Serve de dicionário para o
agente, para novos leitores do código e para o pitch/produto.

**Legenda de status:**

- **no motor** — termo usado na implementação atual (src/, CLI, `plan.json`).
- **contexto** — termo do domínio/mercado que aparece em docs e análises, mas
  ainda não é dependência do código.

---

## Fisiologia e prescrição de treino

| Acrônimo | Significado (EN) | Detalhe no projeto | Status |
|---|---|---|---|
| FTP | Functional Threshold Power | Potência sustentável ~1h; default **182 W** no `.env` (``FTP``). Base do orçamento de TSS e da prescrição por potência. | no motor |
| FTHR | Functional Threshold Heart Rate | FC no limiar; configura **bpm** no `.env` (``FTHR``) para o modo sem medidor de potência (`build --no-power`, v0.0.16). | no motor |
| IF | Intensity Factor | Intensidade do treino = potência/FC média ÷ limiar (FTP ou FTHR). | no motor |
| TSS | Training Stress Score | Carga de um treino: `IF² × horas × 100` (qdo com potência) ou o `icu_training_load` do Intervals (modo FC). | no motor |
| CTL | Chronic Training Load | "Fitness" — carga crônica, suavização exponencial com **tc 42 dias**. | no motor |
| ATL | Acute Training Load | "Fadiga" — carga aguda, suavização exponencial com **tc 7 dias**. | no motor |
| TSB | Training Stress Balance | "Forma" = **CTL − ATL**. Alarme do sistema quando ≤ **−10**. | no motor |
| PMC | Performance Management Chart | Gráfico CTL/ATL/TSB (modelo de Banister). **Expected PMC** = projeção futura misturando real + plano (v0.0.18). | no motor |
| RPE | Rating of Perceived Exertion | Escala subjetiva 1–10; usada como âncora de esforço no modo FC (ex.: "RPE 5-6"). | no motor |
| bpm | beats per minute | Unidade de FC; alvo em `hr_target_bpm` (FTHR × %). | no motor |
| TRIMP | TRaining IMPulse | Carga estimada por FC (alternativa ao TSS). Referência, não implementada. | contexto |
| NP | Normalized Power | Potência normalizada (média ponderada de intensidade). Do WKO/GC. | contexto |
| CP | Critical Power | Potência crítica — assíntota da curva potência×duração; par (CP, **W'**) modela a capacidade anaeróbia. Candidata a métrica futura (ex.: limiar mais fino que o FTP fixo). | contexto |
| W′ / W'bal | Anaerobic Work Capacity / balance | Trabalho anaeróbio disponível acima do CP; `W'bal` de Skiba estima o saldo durante/ao fim do treino. Usada pelo GC/WKO. | contexto |
| VO2 (VO₂max) | maximal oxygen uptake | Capacidade aeróbia máxima; nomeia a zona/foco de treino `FOCUS_VO2`. | no motor |
| Z1–Z5 | Power/HR zones | Faixas de intensidade (Z2 = endurance, Z3 = sweet spot, Z4 = limiar, Z5 = VO2). | no motor |
| HR | Heart Rate | Frequência cardíaca. `HRV` = variabilidade da FC (wellness, Garmin). | no motor |
| RHR | Resting Heart Rate | FC de repouso; campo `restingHR` do wellness (issue #4). | no motor |

## Wellness (issue #4)

| Acrônimo | Significado | Detalhe no projeto |
|---|---|---|
| HRV | Heart Rate Variability | Variabilidade da FC (`hrv` / `hrvSDNN`); sinal de recuperação, vindo do Intervals/Garmin. |
| RHR | Resting Heart Rate | `restingHR` — FC de repouso diário. |
| sleepScore / readiness | — | Métricas do Garmin sincronizadas via `/wellness` (`sleepSecs`, `steps`, `stress`). |

## Formatos e conectividade

| Acrônimo | Significado | Detalhe no projeto |
|---|---|---|
| FIT | Flexible and Interoperable Data Transfer | Formato binário de arquivos de atividade (Garmin/ANT). Parser no GC; libs Python `fitparse`/`fitdecode` (MIT) candidatas para ingestão própria futura. |
| ERG | ERG mode | Modo de rolo inteligente que controla a potência; também arquivo de treino `.erg`/`.mrc`. Formato de prescrição no GC/WKO. |
| .zwo | Zwift Workout | Formato de treino do Zwift. Não usado hoje (o Intervals entrega o treino). |
| ANT+/BTLE | ANT+/Bluetooth Low Energy | Protocolos de comunicação com sensores e rolos. |
| GPX / TCX | — | Formatos de rota/atividade. Intercâmbio compatível com GC. |

## Plataformas e ferramentas

| Acrônimo | Significado | Detalhe no projeto |
|---|---|---|
| ICU / Intervals.icu | intervals.icu | Plataforma de calendário/análise usada como repositório de treinos e atividades (API REST confiável, OAuth para multi-atleta no portal). |
| GC | GoldenCheetah | Analisador local open-source (GPL-2.0); referência de algoritmos (CP/W′, PMC) e oráculo de testes para parsing. Não substitui o Intervals. |
| TP | TrainingPeaks | Plataforma de coaching (API por aprovação, sem uso pessoal); 2º provedor planejado (Fase 2) atrás do mesmo seam. |
| WKO | WKO5 | Software de análise (peca treinador do TrainingPeaks); popularizou CP/W′ e PMC. |
| OCI | Oracle Cloud Infrastructure | Alvo do deploy free tier (`A1.Flex`, ARM64) — ver `dev/DEPLOY.md`. |
| VPS | Virtual Private Server | Servidor sempre-ligado que roda o container (supercronic + timer). |
| VERSION | — | Arquivo `VERSION` do repo (semver) usado nas tags. |

## Tecnologia do produto (portal e dev)

| Acrônimo | Significado | Detalhe no projeto |
|---|---|---|
| CLI | Command Line Interface | Interface atual do motor (`build`, `reconcile`, `push`, `model`, `adherence`, …). |
| API | Application Programming Interface | Contrato REST dos provedores (Intervals.icu) e da futura API do portal (Fase 1). |
| OAuth | Open Authorization | Fluxo de delegação de acesso (Intervals.icu no portal; OAuth + refresh). |
| RBAC | Role-Based Access Control | Papéis do portal: admin / coach / atleta (Fase 0+). |
| SPA | Single-Page Application | Front do portal (React + Vite + Tailwind). |
| SQLite | — | Banco local do portal (Fase 0: `AthleteContext`/`DbContext`). |
| TZ | Time Zone | `TZ=America/Sao_Paulo` no container (job de meia-noite). |
| SSH / deploy key | — | Acesso à VPS; deploy key read-only para o clone (`ssh -A`). |
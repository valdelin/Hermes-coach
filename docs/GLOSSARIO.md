# Glossário — Hermes Coach

> [!info] Dono deste documento
> Fonte canônica: `docs/GLOSSARIO.md` **no repo** (o mesmo arquivo do vault é
> cópia). Quando divergirem, o repo vence. Editar no repo e copiar.
> Espelho: `~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/GLOSSARIO.md`.

Vocabulário de acrônimos e métricas do projeto. Serve de dicionário para o
agente, para novos leitores do código e para o pitch/produto.

**Legenda de status:**

- **no motor** — termo usado na implementação atual (src/, CLI, `plan.json`).
- **contexto** — termo do domínio/mercado que aparece em docs e análises, mas
  ainda não é dependência do código.

**Convenção de identificação.** Acrônimos e siglas do domínio vivem nas tabelas
abaixo, com a coluna `Status` restrita à legenda acima. Termos que **não** são
acrônimos — métricas derivadas, séries observadas, policies e contratos de
leitura — estão em tabelas próprias, com `Item` (ID do backlog) e `Camada`
(camada do sistema: derivação, observado, policy, contrato). Um termo nunca
aparece nas duas formas, e cada termo tem uma única entrada principal.

**Convenção de `Referência`.** Aponta para o melhor ponto canônico para
entender ou localizar o conceito: símbolo em `src/` quando existe uma
implementação clara; documento em `docs/` quando o contrato vive na
documentação do item, ou quando não há símbolo único. Não é obrigatória
uniformidade — a referência serve, não a estética.

**Observado ≠ heurística.** Uma entrada descreve apenas o que é medido. A
interpretação de um sinal observado (limiar, tendência, regra de decisão) é
heurística e pertence à camada correspondente, não à definição do sinal.

---

## Fisiologia e prescrição de treino

| Acrônimo | Significado (EN) | Detalhe no projeto | Status |
|---|---|---|---|
| FTP | Functional Threshold Power | Potência sustentável ~1h; default **182 W** no `.env` (``FTP``). Base do orçamento de TSS e da prescrição por potência. | no motor |
| FTHR | Functional Threshold Heart Rate | FC no limiar; configura **bpm** no `.env` (``FTHR``) para o modo sem medidor de potência (`build --no-power`, v0.0.16). | no motor |
| IF | Intensity Factor | Intensidade do treino = potência/FC média ÷ limiar (FTP ou FTHR). | no motor |
| TSS | Training Stress Score | Carga de um treino. Com potência: `IF² × horas × 100`. Sem potência: valor `icu_training_load` do Intervals, que cobre o treino por FC mas é **opaco** — o motor não sabe se o Intervals usou TRIMP, rTSS ou outra fórmula. | no motor |
| CTL | Chronic Training Load | "Fitness" — carga crônica, suavização exponencial com **tc 42 dias**. | no motor |
| ATL | Acute Training Load | "Fadiga" — carga aguda, suavização exponencial com **tc 7 dias**. | no motor |
| TSB | Training Stress Balance | "Forma" = **CTL − ATL**. Alarme do sistema quando ≤ **−10**. | no motor |
| PMC | Performance Management Chart | Gráfico CTL/ATL/TSB (modelo de Banister). **Expected PMC** = projeção futura misturando real + plano (v0.0.18). | no motor |
| RPE | Rating of Perceived Exertion | Escala subjetiva 1–10; usada como âncora de esforço no modo FC (ex.: "RPE 5-6"). | no motor |
| bpm | beats per minute | Unidade de FC; alvo em `hr_target_bpm` (FTHR × %). | no motor |
| TRIMP | TRaining IMPulse | Carga de treino por FC (~FC × minutos × zona). **Não implementada.** O motor obtém carga por FC do provider (`icu_training_load`), que é um valor opaco — não é TRIMP nem qualquer fórmula derivada de FC. | contexto |
| NP | Normalized Power | Potência normalizada (média ponderada de intensidade). Do WKO/GC. | contexto |
| CP | Critical Power | Potência crítica — assíntota da curva potência×duração; par (CP, **W'**) é referência analítica opcional. Não substitui FTP nem tem uso prescritivo planejado. | contexto |
| W′ / W'bal | Anaerobic Work Capacity / balance | Trabalho acima de CP e saldo estimado por modelos de reconstituição. `W'bal` é heurístico/experimental, sem uso produtivo ou ativação planejada. | contexto |
| VO2 (VO₂max) | maximal oxygen uptake | Capacidade aeróbia máxima; nomeia a zona/foco de treino `FOCUS_VO2`. | no motor |
| Z1–Z5 | Power/HR zones | Faixas de intensidade (Z2 = endurance, Z3 = sweet spot, Z4 = limiar, Z5 = VO2). | no motor |
| HR | Heart Rate | Frequência cardíaca. | no motor |

## Métricas derivadas, séries observadas, policies e contratos

Não são acrônimos: são métricas calculadas, séries observadas, policies e
contratos de leitura, cada um com ID de backlog. Ficam fora das tabelas de
acrônimos, cuja coluna `Status` é restrita à legenda `no motor` / `contexto`.
A separação por camada segue a distinção usada pelo sistema: **derivação**
(calculado do observado), **observado** (provider), **policy** (interpretação
operacional) e **contrato** (forma de leitura, sem advice).

| Termo | Item | Camada | Significado | Detalhe no projeto | Referência |
|---|---|---|---|---|---|
| CTL ramp rate | HR-1 | derivação | Rampa semanal da carga crônica | **CTL(D) − CTL(D−7)**, em pontos de CTL por 7 dias, usando dois valores observados exatos. Ausente se houver gap; não interpola nem recalcula CTL. Limite advisory é opt-in/configurável, sem default fisiológico. | `ui_state.derive_ctl_ramp_rate` |
| HeartRateTrendView | HR-3 | derivação | HRV/RHR observados + baseline individual + delta | Leitura observacional local: por sinal, valor observado, baseline (média da janela), delta absoluto e percentual e nº de observações. Ausência é `None`, nunca zero; zero observado é inválido. HRV não mistura `hrv` com `hrv_sdnn` e declara qual usou. Freshness é reportado e não bloqueia. Não contém policy, advice nem prescrição. | `docs/HR-3-HRV-RHR-TRENDS.md` |
| ObservedWellnessView | HR-4 | observado | Wellness do provider por conceito + contexto derivado | Leitura observacional local: por conceito (`sleep_duration`, `sleep_score`, `stress`, `soreness`, `motivation`, `fatigue`, `provider_readiness`), valor observado, baseline (média da janela), delta, delta percentual, nº de observações, unidade e escala. Ausência é `None`, nunca zero. Escala sem contrato documentado fica `unknown` e **nenhuma** métrica carrega direção. `soreness`/`motivation`/`fatigue` não existem no provider: voltam `unsupported_field`. Sem score composto, policy ou prescrição. | `docs/HR-4-SUBJECTIVE-WELLNESS.md` |
| `unsupported_field` | HR-3/HR-4 | contrato de leitura | Conceito sem chave real no boundary | Resultado explícito de que o provider não expõe o campo. Registrar a lacuna é preferível a fabricar alias ou campo vazio; o consumidor distingue "não existe" de "existe e está ausente" (`missing_current`). | `ui_state` |
| Form relativo (`form_pct`) | PMC-1 | derivação | Forma como % do form absoluto | **TSB / CTL × 100**, em % do form absoluto. Derivação local do Hermes (view-only): `None` se CTL/TSB ausentes ou CTL ≤ 0. Não é limiar de deload nem regra fisiológica — interpretar é policy (POL-1). | `ui_state.derive_form_pct` |
| Pw:HR / aerobic decoupling | HR-2 | derivação | Desacoplamento entre potência e FC | Hermes-specific com fórmula TrainingPeaks-style: `((EF1 - EF2) / EF1) * 100`, `EF = Normalized Power / FC média` por metade. Positivo = EF caiu; negativo = EF subiu. `computable` não confirma esforço steady/aeróbico: `methodological_context` fica `unverified`. | `pw_hr_decoupling.PwHrDecouplingView` |
| Activity stream normalizado | STREAM-1 | observado | Série temporal de atividade | Série temporal observada de atividade, com offset desde o início e valores opcionais de potência/FC. O boundary preserva ausência/zero e diagnóstico de alinhamento, sem interpolar. | `provider.ActivityStream` |
| Temporal sample | STREAM-1/2 | observado | Amostra imutável de um stream | Amostra imutável `elapsed_seconds`, `power`, `heart_rate`; `elapsed_seconds` é offset, não timestamp absoluto. FC vem de `heartrate` quando o comprimento coincide com `time`. | `provider.ActivityStreamPoint` |
| Heart-rate stream | STREAM-2 | observado | Stream de FC do Intervals | `heartrate` é stream armazenado do Intervals; `fixed_heartrate` é variante corrigida e não alias. Três amostras reais sustentam bpm e alinhamento por índice; mismatch é rejeitado. | `docs/STREAM-2-HEART-RATE-STREAM.md` |
| Form advisory policy | POL-1 | policy | Interpretação operacional do form relativo | Interpreta `form_pct <= threshold` (default operacional configurável: **−30%**) como advisory `high_negative_form`. Não é diagnóstico nem prescrição; não muda treino. | `form_advisory.evaluate_form_advisory` |
| ReadinessView | RDY-1 | contrato de leitura | Visão local de readiness (wellness + PMC + heurística) | Contrato de leitura local: separa wellness observado, PMC/form relativo derivado e classificação heurística existente. Não contém policy, advice ou prescrição. | `docs/RDY-1-READINESS-VIEW.md` |

`ReadinessView` **não** é um sinal de wellness: é o contrato que reúne o
wellness observado (tabela de acrônimos abaixo) ao PMC/form derivado e à
heurística de classificação já existente. `Form advisory policy` **não** é dado
fisiológico observado: é interpretação operacional de uma derivação.

## Wellness (issue #4)

| Acrônimo | Significado | Detalhe no projeto |
|---|---|---|
| HRV | Heart Rate Variability | Variabilidade da FC em repouso; sinal fisiológico de recuperação. Observado como `hrv` (ou `hrvSDNN` quando presente), vindo do Intervals/Garmin via `/wellness`. |
| RHR | Resting Heart Rate | Frequência cardíaca de repouso, medida durante o sono. Observada como `restingHR`. **Também chamada FCR em PT-BR** ("frequência cardíaca de repouso") — é o mesmo sinal, não uma métrica separada; por isso não tem entrada própria. Não confundir com *heart-rate recovery* (queda da FC pós-esforço), que é outro conceito e está fora do escopo. |
| sleepScore / readiness | — | Métricas do Garmin sincronizadas via `/wellness` (`sleepSecs`, `steps`, `stress`). |

Os três acima são **dados observados**. A interpretação deles é heurística e
não faz parte destas definições: `hrv_low` (último valor abaixo de 80% da
média) e `rhr_rising` (último acima da média + 3 bpm) são sinais calculados
pelo motor, não medições.

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
| CLI | Command Line Interface | Interface atual do motor (`info`, `check`, `periodization`, `ftp-check`, `ftp-scan`, `model`, `recovery`, `build`, `adherence`, `summary`, `reconcile`, `push`, `all`). |
| API | Application Programming Interface | Contrato REST dos provedores (Intervals.icu) e da futura API do portal (Fase 1). |
| OAuth | Open Authorization | Fluxo de delegação de acesso (Intervals.icu no portal; OAuth + refresh). |
| RBAC | Role-Based Access Control | Papéis do portal: admin / coach / atleta (Fase 0+). |
| SPA | Single-Page Application | Front do portal (React + Vite + Tailwind). |
| SQLite | — | Banco local do portal (Fase 0: `AthleteContext`/`DbContext`). |
| TZ | Time Zone | `TZ=America/Sao_Paulo` no container (job de meia-noite). |
| SSH / deploy key | — | Acesso à VPS; deploy key read-only para o clone (`ssh -A`). |

# Hermes Engineering Prompt Archive

- Repository: `valdelin/Hermes-coach`
- Canonical branch: `master`
- Archive generated from master: `243ad1a82e980e11458dd2e94a9fab5cfa916e63`
- Hermes version: `0.0.36`
- M2: **CLOSED / PUBLISHED / CI GREEN**
- Archive generation date: 2026-10-20 (2026-10-20T16:21:17-03:00, -03)

## About This Archive

Este arquivo consolida os prompts de engenharia **recuperaveis** do projeto
Hermes Coach. Ele nao e um historico narrativo do projeto nem substitui
`docs/ROADMAP.md`, `docs/SPEC-*`, `AGENTS.md` ou os testes: essas fontes
continuam sendo a autoridade sobre decisoes vigentes.

O arquivo existe para tornar rastreavel **o que foi pedido** em cada gate,
separando o que foi de fato preservado do que apenas pode ser inferido por
metadados. Onde o texto integral nao existe, isso e declarado — nao
reconstruido.

## Provenance Rules

| Classificacao | Significado |
|---|---|
| `VERBATIM` | Texto integral recuperado de fonte local confiavel e copiado sem edicao. |
| `RECONSTRUCTED_METADATA_ONLY` | Existencia e metadados (SHA/CI/status) comprovados; texto integral indisponivel. Nao ha texto de prompt aqui. |
| `VERBATIM_NOT_AVAILABLE` | Prompt conhecido apenas por referencia parcial; nem o texto nem metadados completos existem. |
| `SUPERSEDED` | Prompt/execucao associados a implementacao posteriormente substituida. |

Regras aplicadas na geracao:

- nenhum prompt historico foi escrito a partir de memoria, diff, commit,
  relatorio ou intencao inferida;
- Git foi usado para **metadados** (SHA, data de commit, escopo), nunca como
  prova do texto de um prompt;
- resumos sob `Recoverable intent` descrevem o objetivo evidenciado e **nao**
  sao rotulados como prompt;
- relatorios nao foram copiados como prompts;
- onde nao ha evidencia de que um prompt separado existiu, o item nao foi criado.

## Status Legend

`DONE` · `PUBLISHED` · `CI_GREEN` · `CLOSED` · `APPROVED` · `CHANGES_REQUIRED` ·
`SUPERSEDED` · `BLOCKED` · `PARTIAL` · `PENDING` · `PLANNED` · `FUTURE` · `OPEN`

`Result` registra o desfecho conhecido do gate, inclusive quando uma auditoria
encontrou problema. `Commit date` e sempre a data do commit — nunca a data
presumida do prompt.

## Source Coverage Summary

Total indexed prompt records: 70

VERBATIM: 14

RECONSTRUCTED_METADATA_ONLY: 50

VERBATIM_NOT_AVAILABLE: 6

SUPERSEDED references: 4

Contagens acima cobrem apenas os registros deste indice. Referencias
`SUPERSEDED` sao commits substituidos, nao prompts.

## Master Index

| ID | Area | Gate | Type | Availability | Commit | CI | Status | Section |
|---|---|---|---|---|---|---|---|---|
| `SCI-001` | Scientific / Training Domain | P0-01 | IMPLEMENTATION | VERBATIM | `2e6c232` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-002` | Scientific / Training Domain | P0-02 | DESIGN | VERBATIM | `896e84d` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-003` | Scientific / Training Domain | P0-03 | IMPLEMENTATION | VERBATIM | `212b361` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-004` | Scientific / Training Domain | P1-01 | IMPLEMENTATION | VERBATIM | `0094cf1` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-005` | Scientific / Training Domain | P1-02 | IMPLEMENTATION | VERBATIM | `da815c5` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-006` | Scientific / Training Domain | P1-03 | IMPLEMENTATION | VERBATIM | `10e0300` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-007` | Scientific / Training Domain | P1-04 | IMPLEMENTATION | VERBATIM | `0a3e970` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-008` | Scientific / Training Domain | P1-05 | IMPLEMENTATION | VERBATIM | `989182f` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-009` | Scientific / Training Domain | P2-01 | IMPLEMENTATION | VERBATIM | `f18a698` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-010` | Scientific / Training Domain | P2-02 | IMPLEMENTATION | VERBATIM | `ea7e036` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-011` | Scientific / Training Domain | P2-03 | IMPLEMENTATION | VERBATIM | `f9550ea` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-012` | Scientific / Training Domain | P2-04 | IMPLEMENTATION | VERBATIM | `6473b97` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `SCI-013` | Scientific / Training Domain | P3-01 | IMPLEMENTATION | VERBATIM | `0f71f8a` | `NONE` | DONE | [Scientific / Training Domain](#scientific--training-domain) |
| `PROG-001` | Progression | P0-04 | IMPLEMENTATION | VERBATIM | `3011a5f` | `NONE` | DONE | [Progression](#progression) |
| `ARCH-001` | Architecture / Foundation | UI-1..UI-5 | IMPLEMENTATION | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | DONE | [Architecture / Foundation](#architecture--foundation) |
| `ARCH-002` | Architecture / Foundation | Vault sync tooling (PROMPT 30) | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `c92509b` | `NONE` | DONE | [Architecture / Foundation](#architecture--foundation) |
| `ARCH-003` | Architecture / Foundation | PROMPT 27-29 (HR-3 / vault) | SCIENCE_REVIEW | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | DONE | [Architecture / Foundation](#architecture--foundation) |
| `AGENT-001` | Hermes Agent | AGENT-0 (PROMPT 66) | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `338d254` | `NONE` | DONE | [Hermes Agent](#hermes-agent) |
| `AGENT-002` | Hermes Agent | AGENT-0 review (#61) | AUDIT | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | OPEN | [Hermes Agent](#hermes-agent) |
| `AGENT-003` | Hermes Agent | AGENT-1 | DESIGN | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | READY_FOR_PROTOTYPE | [Hermes Agent](#hermes-agent) |
| `AGENT-004` | Hermes Agent | AGENT-2..AGENT-5 | DESIGN | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | FUTURE | [Hermes Agent](#hermes-agent) |
| `FTP-H1-IMPLEMENT` | FTP | FTP-H1 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | DONE | [FTP](#ftp) |
| `FTP-H2-IMPLEMENT` | FTP | FTP-H2 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `9ce364f` | `NONE` | DONE | [FTP](#ftp) |
| `FTP-H3-DESIGN` | FTP | FTP-H3 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `325c1d9` | `NONE` | DONE | [FTP](#ftp) |
| `FTP-H4-IMPLEMENT` | FTP | FTP-H4 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | PENDING | [FTP](#ftp) |
| `FTP-H5-DESIGN` | FTP | FTP-H5 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | PARTIAL | [FTP](#ftp) |
| `FTP-H6-DESIGN` | FTP | FTP-H6 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | PARTIAL | [FTP](#ftp) |
| `FTP-H7-IMPLEMENT` | FTP | FTP-H7 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | BLOCKED | [FTP](#ftp) |
| `FTP-H8-DESIGN` | FTP | FTP-H8 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `211ba29` | `NONE` | PLANNED | [FTP](#ftp) |
| `FTP-057-RESEARCH` | FTP | PROMPT 57 | SCIENCE_REVIEW | VERBATIM_NOT_AVAILABLE | `UNKNOWN` | `NONE` | DONE | [FTP](#ftp) |
| `PROG-1-CONTRACT` | Progression | PROG-1 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | DONE | [Progression](#progression) |
| `PROG-2-GUARDRAILS` | Progression | PROG-2 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | BLOCKED | [Progression](#progression) |
| `PROG-3-EVIDENCE` | Progression | PROG-3 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | FUTURE | [Progression](#progression) |
| `PROG-4-STIMULUS` | Progression | PROG-4 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | FUTURE | [Progression](#progression) |
| `PROG-5-MUTATION` | Progression | PROG-5 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | FUTURE | [Progression](#progression) |
| `PROG-6-BACKTEST` | Progression | PROG-6 | DESIGN | RECONSTRUCTED_METADATA_ONLY | `UNKNOWN` | `NONE` | FUTURE | [Progression](#progression) |
| `M1-001-CONTRACT` | Insight M1 | M1 v2 contract | DESIGN | RECONSTRUCTED_METADATA_ONLY | `87b687b` | `NONE` | APPROVED | [Insight M1](#insight-m1) |
| `M1-002-IMPLEMENT` | Insight M1 | M1 v2 implementation | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `5ac8452` | `NONE` | DONE | [Insight M1](#insight-m1) |
| `M1-003-FIX` | Insight M1 | M1 v2 hardening fixes | FIX | RECONSTRUCTED_METADATA_ONLY | `36c27d8` | `NONE` | DONE | [Insight M1](#insight-m1) |
| `M1-004-PUBLISH` | Insight M1 | M1 v2 publication | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `6b4a979` | `38578649393` | PUBLISHED | [Insight M1](#insight-m1) |
| `M1.1-001-PLAN` | Insight M1.1 | M1.1 planning | DESIGN | RECONSTRUCTED_METADATA_ONLY | `9dd4d72` | `NONE` | DONE | [Insight M1.1](#insight-m11) |
| `M1.1-002-A` | Insight M1.1 | M1.1-A SIZE_LIMITS | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `07f7529` | `38801992928` | PUBLISHED | [Insight M1.1](#insight-m11) |
| `M1.1-003-B` | Insight M1.1 | M1.1-B REQUEST_PROVENANCE | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `02fe2ce` | `38806075695` | PUBLISHED | [Insight M1.1](#insight-m11) |
| `M1.1-004-CLOSURE` | Insight M1.1 | M1.1 closure | CLOSURE | RECONSTRUCTED_METADATA_ONLY | `19ad50b` | `NONE` | CLOSED | [Insight M1.1](#insight-m11) |
| `M2-0-IMPLEMENT` | Insight M2 | M2-0 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `61a520b` | `38841007669` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-0-PUBLISH` | Insight M2 | M2-0 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `61a520b` | `38841007669` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-1-IMPLEMENT` | Insight M2 | M2-1 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `419290e` | `38842621182` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-1-PUBLISH` | Insight M2 | M2-1 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `419290e` | `38842621182` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-2-IMPLEMENT` | Insight M2 | M2-2 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `1c869c6` | `38847852079` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-2-PUBLISH` | Insight M2 | M2-2 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `1c869c6` | `38847852079` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-3-IMPLEMENT` | Insight M2 | M2-3 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `1d478f0` | `38915257810` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-3-PUBLISH` | Insight M2 | M2-3 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `1d478f0` | `38915257810` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-4-IMPLEMENT` | Insight M2 | M2-4 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `8e14824` | `38922504778` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-4-PUBLISH` | Insight M2 | M2-4 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `8e14824` | `38922504778` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-5-IMPLEMENT` | Insight M2 | M2-5 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `d4dbb06` | `38935882413` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-5-PUBLISH` | Insight M2 | M2-5 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `d4dbb06` | `38935882413` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-6-IMPLEMENT` | Insight M2 | M2-6 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `062431c` | `39312837865` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-6-PUBLISH` | Insight M2 | M2-6 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `062431c` | `39312837865` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-7-IMPLEMENT` | Insight M2 | M2-7 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `7e494af` | `39451275264` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-7-PUBLISH` | Insight M2 | M2-7 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `7e494af` | `39451275264` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-8-IMPLEMENT` | Insight M2 | M2-8 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `8701d85` | `39461160953` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-8-PUBLISH` | Insight M2 | M2-8 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `8701d85` | `39461160953` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-9-IMPLEMENT` | Insight M2 | M2-9 | IMPLEMENTATION | RECONSTRUCTED_METADATA_ONLY | `243ad1a` | `39479246606` | PUBLISHED | [Insight M2](#insight-m2) |
| `M2-9-PUBLISH` | Insight M2 | M2-9 | PUBLICATION | RECONSTRUCTED_METADATA_ONLY | `243ad1a` | `39479246606` | CI_GREEN | [Insight M2](#insight-m2) |
| `M2-6-AUDIT` | Insight M2 | M2-6 | AUDIT | RECONSTRUCTED_METADATA_ONLY | `062431c` | `39312837865` | CHANGES_REQUIRED | [Insight M2](#insight-m2) |
| `M2-6-REAUDIT` | Insight M2 | M2-6 | REAUDIT | RECONSTRUCTED_METADATA_ONLY | `062431c` | `39312837865` | APPROVED | [Insight M2](#insight-m2) |
| `M2-7-AUDIT` | Insight M2 | M2-7 | AUDIT | RECONSTRUCTED_METADATA_ONLY | `7e494af` | `39451275264` | APPROVED | [Insight M2](#insight-m2) |
| `M2-8-AUDIT` | Insight M2 | M2-8 | AUDIT | RECONSTRUCTED_METADATA_ONLY | `8701d85` | `39461160953` | APPROVED | [Insight M2](#insight-m2) |
| `M2-9-AUDIT` | Insight M2 | M2-9 | AUDIT | RECONSTRUCTED_METADATA_ONLY | `243ad1a` | `39479246606` | CHANGES_REQUIRED | [Insight M2](#insight-m2) |
| `M2-9-CLOSURE` | Insight M2 | M2-9 | CLOSURE | RECONSTRUCTED_METADATA_ONLY | `243ad1a` | `39479246606` | PUBLISHED | [Insight M2](#insight-m2) |

IDs de implementacao e publicacao apontam para o mesmo commit quando o gate foi
publicado em um unico push. Isso nao significa prompt identico: sao registros
distintos do mesmo gate.

## Architecture / Foundation

Gates de fundacao (UI Foundation, tooling de vault, orquestrador local).
Nenhum prompt integral destes gates foi preservado no repositorio.

### ARCH-001 — UI-1..UI-5

Metadata:

- Area: Architecture / Foundation
- Gate: UI-1..UI-5
- Type: IMPLEMENTATION
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/UI-2-LIFECYCLE.md, docs/UI-3-PROVIDER-BOUNDARY.md, docs/UI-4-COMPLETION-SNAPSHOT.md, docs/UI-5-APPLICATION-STATE.md, docs/ROADMAP.md (UI Foundation)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: DONE
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

UI Foundation: Application seam, lifecycle, provider boundary, completion/snapshot, ApplicationState/PlanView. Os docs por gate existem; os prompts originais nao foram preservados localmente.

### ARCH-002 — Vault sync tooling (PROMPT 30)

Metadata:

- Area: Architecture / Foundation
- Gate: Vault sync tooling (PROMPT 30)
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: scripts/sync_vault_docs.py (docstring), docs/VAULT-SYNC.md, AGENTS.md
- Related SHA: `c92509b`
- CI: `NONE`
- Commit date: 2026-10-08T22:34:18-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Substituir copia manual repo->vault por ferramenta idempotente com ownership preservado, apos o incidente de duplicacao de quatro espelhos.

### ARCH-003 — PROMPT 27-29 (HR-3 / vault)

Metadata:

- Area: Architecture / Foundation
- Gate: PROMPT 27-29 (HR-3 / vault)
- Type: SCIENCE_REVIEW
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/VAULT-SYNC.md, docs/HR-3-HRV-RHR-TRENDS.md
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: DONE
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

Correcao de baseline HRV/RHR e decisoes de backlog na trilha HR-3. Apenas referencias parciais.

## Scientific / Training Domain

Trilha P0-P3 do motor de treino. Estes sao os unicos prompts com texto integral
preservado: os arquivos em `prompts/opencode/` foram arquivados no commit
`3df407b` (`docs(prompts): archive delivered training-engine prompts`) e o
`prompts/README.md` declara que sao preservados sem reescrita.

O SHA em `Candidate commit` foi associado por correspondencia de assunto entre
o prompt e a mensagem do commit. Essa associacao e **inferida**, nao comprovada
por artefato de sessao; trate-a como pista de rastreio.

### SCI-001 — P0-01

Metadata:

- Area: Scientific / Training Domain
- Gate: P0-01
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/01-P0-01-training-load-tss.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `2e6c232`
- Commit date: 2026-10-01T12:14:32-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P0-01 — Training Load / TSS

Audite e corrija o cálculo de carga do Hermes Coach.

## Objetivo
Separar claramente `power_training_load`, `estimated_tss`, `external_load` e `internal_load`, preservando compatibilidade com CTL, ATL e TSB.

## Implementação
- Quando houver NP: `IF = NP / FTP` e `TSS ≈ duração_em_horas × IF² × 100`.
- Não fabrique NP para treinos curtos ou apenas planejados.
- Diferencie TSS estimado do treino planejado de TSS calculado após execução.
- Documente as limitações de TSS/IF para HIIT curto.

## Testes
1h@100%=100 TSS; 1h@70%=49; 1h@75%=56,25; 2h@70%=98. Teste também treino variável, HIIT curto, FTP inválido/ausente, duração zero e potência zero.

## Documentação
Atualize `EMBASAMENTO-CIENTIFICO.md` sobre IF, NP, TSS, CTL, ATL e TSB. Diferencie metodologia operacional de evidência científica.

## Referências
TrainingPeaks/Coggan para a definição operacional de IF/NP/TSS; Galán-Rioja et al. (2023) para contexto de carga e periodização.
```

### SCI-002 — P0-02

Metadata:

- Area: Scientific / Training Domain
- Gate: P0-02
- Type: DESIGN
- Availability: VERBATIM
- Source: `prompts/opencode/02-P0-02-periodizacao-vs-tsb.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `896e84d`
- Commit date: 2026-10-01T12:28:45-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P0-02 — Separar Periodização de TSB

Implemente uma separação arquitetural entre periodização e autoregulação diária.

## Estado
Criar `TrainingPlanState` com:
- goal
- phase
- week_in_phase
- cycle_week
- planned_load
- current_load
- tsb
- readiness

## Fluxo
`GOAL → TRAINING PHASE → PHASE OBJECTIVES → WEEK TARGET → TSB/READINESS → SESSION MODIFICATION`.

TSB deve modificar a sessão, não determinar sozinho a fase do macrociclo.

## Testes
- Alterar TSB não pode mudar automaticamente a fase.
- TSB baixo pode reduzir/adaptar a sessão.
- TSB adequado permite executar a sessão planejada.

Documente a distinção entre periodização e autoregulação e cite Galán-Rioja et al. (2023).
```

### SCI-003 — P0-03

Metadata:

- Area: Scientific / Training Domain
- Gate: P0-03
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/03-P0-03-training-phase.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `212b361`
- Commit date: 2026-10-01T12:41:32-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P0-03 — TrainingPhase

Crie uma abstração explícita de fase de treinamento.

## Enum
`BASE`, `BUILD`, `SPECIFIC`, `PEAK`, `RECOVERY`, `TEST`.

Crie `TrainingPhaseEngine`.

Cada fase deve possuir:
- objective
- duration
- priority_stimuli
- secondary_stimuli
- load_limits
- progression_criteria
- deload_criteria
- exit_criteria

As durações devem ser configuráveis, sem codificar uma duração universal.

Crie testes de criação, permanência, transição, deload, recovery e test.

Na documentação, deixe claro que a arquitetura é inspirada em princípios de periodização e não representa uma sequência fisiológica universal.
```

### SCI-004 — P1-01

Metadata:

- Area: Scientific / Training Domain
- Gate: P1-01
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/05-P1-01-intensity-distribution.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `0094cf1`
- Commit date: 2026-10-01T12:48:37-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P1-01 — IntensityDistribution

Separe `PeriodizationModel` de `IntensityDistributionModel`.

## Modelos
`POLARIZED`, `PYRAMIDAL`, `THRESHOLD_HEAVY`, `CUSTOM`.

Calcule a distribuição por tempo efetivo de treinamento, não pelo número de sessões.

Relatório semanal:
- minutos baixa intensidade;
- minutos moderada;
- minutos alta;
- percentual de cada.

Não assuma que polarizado = 80/20 universal.

Teste soma de minutos, soma dos percentuais, sessões mistas, volumes diferentes e CUSTOM.

Referencie Galán-Rioja et al. (2023) e a revisão/meta-análise de 2025, PMID 39788807.
```

### SCI-005 — P1-02

Metadata:

- Area: Scientific / Training Domain
- Gate: P1-02
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/06-P1-02-athlete-physiological-profile.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `da815c5`
- Commit date: 2026-10-01T12:50:28-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P1-02 — AthletePhysiologicalProfile

Crie um modelo fisiológico explícito.

## Campos
`ftp`, `ftp_source`, `ftp_confidence`, `critical_power`, `w_prime`, `vo2max`, `max_hr`, `threshold_hr`, `resting_hr`, `hrv_baseline`, `weekly_training_hours`, `training_days`, `training_age`, `preferred_long_day`.

`ftp_source`: USER, FTP20, FTP60, RAMP, CP_ESTIMATE, PERFORMANCE_ESTIMATE.

`ftp_confidence`: LOW, MEDIUM, HIGH.

Não trate FTP como sinônimo de MLSS, LT, CP ou RCP. CP/W' e VO2max são opcionais. Preserve atletas que possuem somente FTP.

Documente as limitações de intercambialidade entre FTP e marcadores fisiológicos.
```

### SCI-006 — P1-03

Metadata:

- Area: Scientific / Training Domain
- Gate: P1-03
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/07-P1-03-adaptation-state.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `10e0300`
- Commit date: 2026-10-01T12:52:06-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P1-03 — AdaptationState

Crie estado computacional de adaptação nos domínios:
- aerobic_base
- threshold
- vo2max
- muscular_endurance
- anaerobic
- neuromuscular

Valores de 0 a 1. Cada sessão deve possuir vetor de contribuição, com atualização, decaimento temporal e saturação.

Exemplo conceitual:
Z2 → aerobic_base +++;
Threshold → threshold +++;
VO2 → vo2max +++;
Sprint → neuromuscular +++.

Importante: esses valores são heurísticas computacionais, não medições fisiológicas.

Teste atualização, decaimento, saturação, sessões neutras e combinação de estímulos.
```

### SCI-007 — P1-04

Metadata:

- Area: Scientific / Training Domain
- Gate: P1-04
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/08-P1-04-training-decision-engine.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `0a3e970`
- Commit date: 2026-10-01T12:53:13-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P1-04 — TrainingDecisionEngine

Crie o motor central de decisão adaptativa.

## Fluxo
`GOAL → PHASE → LIMITATIONS/ADAPTATION PRIORITIES → RECENT LOAD → READINESS → DESIRED STIMULUS → DOSE → PROGRESSION STEP → SAFETY ADJUSTMENTS → WORKOUT`.

## TrainingDecision
- goal
- phase
- primary_adaptation
- secondary_adaptation
- selected_zone
- workout_family
- progression_step
- planned_duration
- planned_load
- readiness_modifier
- rationale
- confidence

A decisão deve responder “por que este estímulo agora?” e considerar objetivo, fase, adaptações, carga, readiness, progressão e segurança.

Evite regras baseadas somente em zona ou TSB.
```

### SCI-008 — P1-05

Metadata:

- Area: Scientific / Training Domain
- Gate: P1-05
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/09-P1-05-readiness.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `989182f`
- Commit date: 2026-10-01T12:54:56-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P1-05 — ReadinessAssessment

Crie avaliação multimodal de prontidão.

Campos:
`hrv_score`, `rhr_score`, `sleep_score`, `subjective_fatigue_score`, `recent_load_score`, `performance_score` opcional, `consistency_score`, `overall_readiness`, `confidence`.

Use HRV contra baseline individual e RHR como tendência. Contextualize sono, fadiga e carga.

Não use regras universais como HRV <80% ou RHR +3 como decisão isolada.

GREEN/YELLOW/RED representa adequação ao treinamento, não diagnóstico.

Um único sinal isolado não deve cancelar automaticamente uma sessão intensa.

Permita ajuste de intensidade, volume, intervalos e recuperação.

Referências: Düking et al. (2021), PMID 34489178; Granero-Gallegos et al. (2020), PMID 33143175; literatura HRV-guided e revisão de 2026.
```

### SCI-009 — P2-01

Metadata:

- Area: Scientific / Training Domain
- Gate: P2-01
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/10-P2-01-critical-power-wprime.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `f18a698`
- Commit date: 2026-10-01T13:25:04-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P2-01 — Critical Power / W'

Adicione CP e W' como métricas complementares ao FTP.

Crie `CriticalPowerProfile`:
- critical_power
- w_prime
- protocol
- confidence
- test_dates

Funções:
`estimate_cp()`, `estimate_w_prime()`, `work_above_cp()`, `w_prime_balance()`, `w_prime_reconstitution()`.

Só calcule quando houver dados suficientes.

Use CP/W' para esforços acima do limiar, Z6, HIIT e análise power-duration. Não substitua FTP automaticamente por CP e nunca trate os dois como equivalentes.

Referência principal: revisão sobre Critical Power/W', W' e reconstituição, PMID 32899777.
```

### SCI-010 — P2-02

Metadata:

- Area: Scientific / Training Domain
- Gate: P2-02
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/11-P2-02-vo2-generator.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `ea7e036`
- Commit date: 2026-10-01T13:40:31-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P2-02 — VO2WorkoutGenerator

Crie gerador estruturado de treinos VO2max.

Modelo:
- interval_duration
- repetitions
- work_power_range
- recovery_duration
- recovery_power
- total_work_time
- progression_step

Use faixa configurável inicialmente em torno de 106–120% FTP, sem fixar 115% universalmente.

Permita progressão por duração, tempo total, repetições e intensidade, sem aumentar tudo simultaneamente.

Famílias:
`LONG_INTERVALS`, `SHORT_INTERVALS`, `VARIABLE_INTERVALS`.

Templates: 4x4, 5x3, 3x5. Não trate como protocolos universais.

Avalie intensidade + duração + recuperação + trabalho acumulado.

Referências: meta-análise/revisão de 2026 sobre HIIT/VO2max, PMID 42237396; network meta-analysis, PMID 42482078.
```

### SCI-011 — P2-03

Metadata:

- Area: Scientific / Training Domain
- Gate: P2-03
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/12-P2-03-z2-sweetspot-threshold.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `f9550ea`
- Commit date: 2026-10-01T13:45:30-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P2-03 — Refinar Z2, Sweet Spot e Threshold

Diferencie ENDURANCE, SWEET_SPOT e THRESHOLD pela intenção e dose, não somente pela %FTP.

## Z2
Suporte blocos contínuos, treinos longos e progressões; evite intervalos artificiais sem finalidade.

## Sweet Spot
Trate como faixa de intensidade de treinamento, não como zona fisiológica universal. Permita progressão de volume/duração.

Não afirme que Sweet Spot = limiar fisiológico.

## Threshold
Permita progressão de duração, repetições e recuperação.

Não afirme que 95% FTP = MLSS.

Referências: FTP20 scoping review PMID 34304689; FTP vs lactato PMID 31269000; FTP95 vs MLSS PMID 31689684; FTP vs RCP PMID 33728842.

Crie testes garantindo que as famílias tenham intenções diferentes mesmo quando as faixas de potência se sobrepõem.
```

### SCI-012 — P2-04

Metadata:

- Area: Scientific / Training Domain
- Gate: P2-04
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/13-P2-04-embasamento-cientifico.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `6473b97`
- Commit date: 2026-10-01T13:51:20-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P2-04 — Consolidar EMBASAMENTO-CIENTIFICO.md

Reestruture a documentação científica.

## Estrutura
1. Princípios
2. FTP
3. Critical Power / W'
4. Zonas
5. Periodização
6. Distribuição de intensidade
7. Training Load
8. CTL / ATL / TSB
9. Readiness
10. Adaptation State
11. Progression Engine
12. VO2max
13. Recovery / Deload
14. Limitações
15. Referências

Classifique cada conteúdo como:
- EVIDÊNCIA CIENTÍFICA
- HEURÍSTICA DO SISTEMA
- MODELO COMPUTACIONAL

Toda afirmação fisiológica relevante deve possuir fonte. Nunca invente autor, DOI, PMID ou resultado.

Evite “melhor” sem base comparativa. Prefira “evidências sugerem”, “o estudo encontrou” ou “não há evidência suficiente”.

Inclua, no mínimo:
- Galán-Rioja et al. (2023), PMID 36640771;
- meta-análise 2025, PMID 39788807;
- FTP20, PMID 34304689;
- estudos FTP vs lactato/CP/MLSS/RCP;
- Critical Power/W', PMID 32899777;
- HRV-guided training, PMID 34489178 e PMID 33143175;
- HIIT/VO2 2026, PMID 42237396 e 42482078;
- documentação operacional de TSS/IF/NP, claramente identificada como metodologia de indústria.
```

### SCI-013 — P3-01

Metadata:

- Area: Scientific / Training Domain
- Gate: P3-01
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/14-P3-01-scientific-regression-tests.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `0f71f8a`
- Commit date: 2026-10-01T14:07:44-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P3-01 — Scientific Regression Tests

Crie `tests/scientific/` com:
- `test_training_load.py`
- `test_periodization.py`
- `test_progression.py`
- `test_readiness.py`
- `test_adaptation.py`
- `test_ftp.py`
- `test_critical_power.py`
- `test_vo2.py`
- `test_intensity_distribution.py`

Teste propriedades/invariantes, não apenas execução.

Cobrir:
- TSS;
- CTL;
- ATL;
- TSB;
- progressão;
- deload;
- transição de fases;
- distribuição;
- readiness;
- adaptação;
- confiança do FTP;
- CP/W';
- VO2;
- recuperação.

Preserve os testes existentes, adicione casos-limite e execute a suíte completa.

O objetivo é impedir que futuras mudanças transformem heurísticas documentadas em regras fisiológicas rígidas sem justificativa.
```

## FTP

Trilha FTP-H. Preserva a distincao entre FTP canonico, evidencia, advice,
confirmacao e contexto de prescricao. Nenhum prompt integral foi preservado.

### FTP-H1-IMPLEMENT — FTP-H1

Metadata:

- Area: FTP
- Gate: FTP-H1
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (linha FTP-H1)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Integrar AthletePhysiologicalProfile com FtpHistory.resolve_ftp_at; sem DEFAULT_FTP nem .env como fonte fisiologica.

### FTP-H2-IMPLEMENT — FTP-H2

Metadata:

- Area: FTP
- Gate: FTP-H2
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H2), src/ftp_evidence.py
- Related SHA: `9ce364f`
- CI: `NONE`
- Commit date: 2026-10-08T22:05:58-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

FtpEvidence -> Advice -> confirmacao explicita -> FtpReference; nenhuma promocao automatica.

### FTP-H3-DESIGN — FTP-H3

Metadata:

- Area: FTP
- Gate: FTP-H3
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-ftp-h3-block-context.md, docs/ROADMAP.md (FTP-H3)
- Related SHA: `325c1d9`
- CI: `NONE`
- Commit date: 2026-10-09T09:01:14-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

BlockContext v1 persistido em plan.json; nao seleciona fase, FTP ou prescricao.

### FTP-H4-IMPLEMENT — FTP-H4

Metadata:

- Area: FTP
- Gate: FTP-H4
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H4)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: PENDING
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

RETEST_RECOMMENDED como Advice quando FTP canonico e UNKNOWN no inicio de bloco; depende de FTP-H3.

### FTP-H5-DESIGN — FTP-H5

Metadata:

- Area: FTP
- Gate: FTP-H5
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H5), docs/ROTEIRO-TREINADOR.md 1.7
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: PARTIAL
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Sessao de teste de FTP como Prescription; aguarda TRAINER SAFETY CONTRACT.

### FTP-H6-DESIGN — FTP-H6

Metadata:

- Area: FTP
- Gate: FTP-H6
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H6), ADR-006
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: PARTIAL
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Build/prescricao consumirem FTP canonico em vez de .env; ownership dos watts resolvido, decisoes tecnicas pendentes.

### FTP-H7-IMPLEMENT — FTP-H7

Metadata:

- Area: FTP
- Gate: FTP-H7
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H7)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: BLOCKED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Reabrir FTP temporal para ObservedIntensityDistribution; limitado a periodos cobertos por FtpHistory.

### FTP-H8-DESIGN — FTP-H8

Metadata:

- Area: FTP
- Gate: FTP-H8
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (FTP-H8), docs/FTP-H8 (registro de follow-up)
- Related SHA: `211ba29`
- CI: `NONE`
- Commit date: 2026-10-15T17:39:33-03:00
- Result: PLANNED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Deteccao protocolar e ciclo de reteste, sem inferir teste pelo nome da atividade.

### FTP-057-RESEARCH — PROMPT 57

Metadata:

- Area: FTP
- Gate: PROMPT 57
- Type: SCIENCE_REVIEW
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/research/PROMPT-57-FTP-EFTP-INTERVALS.md (relatorio preservado)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: DONE
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

Relatorio sobre eFTP do Intervals.icu e fronteira estimate/evidence/reference. O arquivo e relatorio, nao prompt.

## Progression

Trilha de progressao. O prompt do motor de progressao (P0-04) tem texto
preservado; o contrato PROG-1..PROG-6 nao tem. Decisoes ainda pendentes do
treinador permanecem registradas como pendentes — nao foram promovidas a
decisoes finalizadas.

### PROG-001 — P0-04

Metadata:

- Area: Progression
- Gate: P0-04
- Type: IMPLEMENTATION
- Availability: VERBATIM
- Source: `prompts/opencode/04-P0-04-progression-engine.md`
- Prompt date: UNKNOWN
- Candidate commit (subject correspondence, unverified): `3011a5f`
- Commit date: 2026-10-01T12:46:51-03:00
- CI: NONE
- Final result: DONE
- Superseded: NO

#### Prompt

```markdown
# P0-04 — ProgressionEngine

Crie um motor de progressão por família de estímulo.

## Famílias
`SWEET_SPOT`, `THRESHOLD`, `VO2MAX`, `ENDURANCE`, `ANAEROBIC`.

Modele progressão por duração, repetições, intensidade ou redução de recuperação. Não aumente todas simultaneamente.

Exemplos de templates:
- Sweet Spot: 3x8 → 3x10 → 3x12 → deload → 2x15 → 3x15.
- Threshold: 3x8 → 3x10 → 3x12 → 2x15 → 3x15.
- VO2: 4x3 → 5x3 → 4x4 → 5x4.

Crie `CompletionScore` usando potência-alvo, tempo completado, RPE, FC e interrupções/falhas.

Classifique `COMPLETED`, `PARTIAL`, `FAILED`, `EASY`.

Só progrida após sucesso. Em PARTIAL/FAILED, repita, reduza ou ajuste.

Documente as sequências como heurísticas do sistema, não protocolos universais.
```

### PROG-1-CONTRACT — PROG-1

Metadata:

- Area: Progression
- Gate: PROG-1
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-progression.md, docs/ROADMAP.md (PROG-1)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Contrato ProgressionEvidence -> ProgressionDecision; documentacao concluida, implementacao nao iniciada.

### PROG-2-GUARDRAILS — PROG-2

Metadata:

- Area: Progression
- Gate: PROG-2
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (PROG-2), docs/ROTEIRO-TREINADOR.md 1.8
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: BLOCKED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Guardrails e matriz normativa de progressao; bloqueado por decisoes Q1-Q4 do treinador.

### PROG-3-EVIDENCE — PROG-3

Metadata:

- Area: Progression
- Gate: PROG-3
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (PROG-3)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: FUTURE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Integracao de evidencia (adherence, WorkoutExecutionView, readiness, phase, ramp, seams).

### PROG-4-STIMULUS — PROG-4

Metadata:

- Area: Progression
- Gate: PROG-4
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (PROG-4)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: FUTURE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Progressao de estimulo a partir da biblioteca SEQUENCES.

### PROG-5-MUTATION — PROG-5

Metadata:

- Area: Progression
- Gate: PROG-5
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (PROG-5)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: FUTURE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

PrescriptionProgression como use-case separado; permanece por ultimo.

### PROG-6-BACKTEST — PROG-6

Metadata:

- Area: Progression
- Gate: PROG-6
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (PROG-6)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: FUTURE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Validacao historica/backtest dependente de historico observado.

## Hermes Agent

### AGENT-001 — AGENT-0 (PROMPT 66)

Metadata:

- Area: Hermes Agent
- Gate: AGENT-0 (PROMPT 66)
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/HOWTO-HERMES-AGENT.md, docs/ROADMAP.md item #61/AGENT-0, scripts/hermes_agent.py
- Related SHA: `338d254`
- CI: `NONE`
- Commit date: 2026-10-08T22:13:18-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Orquestrador local deterministico como facade sobre o CLI, com confirmacao antes de mutacoes e sem LLM.

### AGENT-002 — AGENT-0 review (#61)

Metadata:

- Area: Hermes Agent
- Gate: AGENT-0 review (#61)
- Type: AUDIT
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/ROADMAP.md item #61
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: OPEN
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

Code review do orquestrador entregue no PROMPT 66: seguranca, paridade de flags, confirmacoes, modo interativo e robustez dos testes.

### AGENT-003 — AGENT-1

Metadata:

- Area: Hermes Agent
- Gate: AGENT-1
- Type: DESIGN
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/ROADMAP.md (AGENT-1)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: READY_FOR_PROTOTYPE
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

Prototipo read-only de gateway expondo apenas Views da Application, zero mutacao, somente com aprovacao explicita.

### AGENT-004 — AGENT-2..AGENT-5

Metadata:

- Area: Hermes Agent
- Gate: AGENT-2..AGENT-5
- Type: DESIGN
- Availability: VERBATIM_NOT_AVAILABLE
- Evidence: docs/ROADMAP.md (AGENT-2..AGENT-5)
- Related SHA: `UNKNOWN`
- CI: `NONE`
- Commit date: UNKNOWN
- Result: FUTURE
- Superseded: NO

#### Historical prompt text

VERBATIM_NOT_AVAILABLE

#### Recoverable intent

Notificacao, Q&A read-only, proposta de mutacao que reentra no fluxo de aprovacao e hub multi-atleta.

## Insight M1

Camada LLM read-only de apresentacao. Gates INSIGHT-1..6, integrados em
`master` via `FAST_FORWARD_ONLY`. Sem release implicado.

### M1-001-CONTRACT — M1 v2 contract

Metadata:

- Area: Insight M1
- Gate: M1 v2 contract
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1-v2.md
- Related SHA: `87b687b`
- CI: `NONE`
- Commit date: 2026-10-13T16:11:14-03:00
- Result: APPROVED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Contrato read-only da camada LLM de apresentacao (INSIGHT-1..6).

### M1-002-IMPLEMENT — M1 v2 implementation

Metadata:

- Area: Insight M1
- Gate: M1 v2 implementation
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1-v2.md, git history 5ac8452..6b4a979
- Related SHA: `5ac8452`
- CI: `NONE`
- Commit date: 2026-10-13T16:17:12-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Contrato read-only, renderer grounded, boundary de provider, harness offline, view seam e CLI segura.

### M1-003-FIX — M1 v2 hardening fixes

Metadata:

- Area: Insight M1
- Gate: M1 v2 hardening fixes
- Type: FIX
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: git history 02738bc, 36c27d8, 36aedcb
- Related SHA: `36c27d8`
- CI: `NONE`
- Commit date: 2026-10-13T16:47:52-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Endurecimento de grounding de fatos e invariantes do harness offline.

### M1-004-PUBLISH — M1 v2 publication

Metadata:

- Area: Insight M1
- Gate: M1 v2 publication
- Type: PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (INSIGHT M1 v2), docs/SPEC-insight-m1-v2.md
- Related SHA: `6b4a979`
- CI: `38578649393`
- Commit date: 2026-10-14T01:54:32-03:00
- Result: PUBLISHED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Integracao em master via FAST_FORWARD_ONLY com CI de master verde; sem release.

## Insight M1.1

Hardening contract: `M1.1-A SIZE_LIMITS` e `M1.1-B REQUEST_PROVENANCE`,
ambos publicados e fechados antes de M2.

### M1.1-001-PLAN — M1.1 planning

Metadata:

- Area: Insight M1.1
- Gate: M1.1 planning
- Type: DESIGN
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1.1.md, docs/ROADMAP.md
- Related SHA: `9dd4d72`
- CI: `NONE`
- Commit date: 2026-10-14T11:32:39-03:00
- Result: DONE
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Planejamento do hardening e do milestone online seguinte.

### M1.1-002-A — M1.1-A SIZE_LIMITS

Metadata:

- Area: Insight M1.1
- Gate: M1.1-A SIZE_LIMITS
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1.1.md, docs/ROADMAP.md (INSIGHT2-AUD-03)
- Related SHA: `07f7529`
- CI: `38801992928`
- Commit date: 2026-10-14T12:16:45-03:00
- Result: PUBLISHED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Limites explicitos de tamanho com falha fechada e status observavel; follow-up de invariancia em fb18b18.

### M1.1-003-B — M1.1-B REQUEST_PROVENANCE

Metadata:

- Area: Insight M1.1
- Gate: M1.1-B REQUEST_PROVENANCE
- Type: IMPLEMENTATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1.1.md, docs/ROADMAP.md (INSIGHT3-AUD-01)
- Related SHA: `02fe2ce`
- CI: `38806075695`
- Commit date: 2026-10-15T17:47:26-03:00
- Result: PUBLISHED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Fonte unica por invocation para request e provenance; mismatch falha fechado.

### M1.1-004-CLOSURE — M1.1 closure

Metadata:

- Area: Insight M1.1
- Gate: M1.1 closure
- Type: CLOSURE
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/SPEC-insight-m1.1.md
- Related SHA: `19ad50b`
- CI: `NONE`
- Commit date: 2026-10-15T18:01:55-03:00
- Result: CLOSED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Fechamento documental do M1.1 apos os dois sub-gates publicados.

## Insight M2

Runtime online de explicacao, implementado em gates atomicos M2-0..M2-9.
Estado final: **CLOSED / PUBLISHED / CI GREEN**. Nenhum prompt de gate foi
preservado localmente; os registros abaixo sao metadados.

Provider `openai`, modelo `gpt-5.4-nano-2026-03-17` (ADR-007). Ambas as flags
`HERMES_INSIGHT_ENABLED` e `HERMES_INSIGHT_ONLINE_ENABLED` permanecem OFF por
default. Sem release, tag ou GA.

### M2-4 — cadeia de commits

M2-4 nao foi dois gates. A cadeia foi:

```text
e1dd7c7  docs(insight): select initial provider and model
8e14824  docs(insight): fix trailing whitespace in ADR-007
```

O CI publicado (`38922504778`) pertence ao push do head final `8e14824`, que
inclui `e1dd7c7`. **Nao existe CI isolado para `e1dd7c7`** e nenhum foi
inventado aqui.

### M2-0 — SPEC e decisoes de design

Metadata:

- Area: Insight M2
- Gate: M2-0
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `61a520b`
- CI: `38841007669`
- Commit date: 2026-10-15T23:29:21-03:00
- Result: PUBLISHED / CI_GREEN — Contract READY
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-0: spec e decisoes de design. Publicado em `61a520b` com CI `38841007669` verde.

### M2-1 — Prompt/request puro

Metadata:

- Area: Insight M2
- Gate: M2-1
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `419290e`
- CI: `38842621182`
- Commit date: 2026-10-15T23:43:48-03:00
- Result: PUBLISHED / CI_GREEN — Deterministic model requests
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-1: prompt/request puro. Publicado em `419290e` com CI `38842621182` verde.

### M2-2 — Decoder e validators

Metadata:

- Area: Insight M2
- Gate: M2-2
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `1c869c6`
- CI: `38847852079`
- Commit date: 2026-10-16T00:44:50-03:00
- Result: PUBLISHED / CI_GREEN — Model response templates
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-2: decoder e validators. Publicado em `1c869c6` com CI `38847852079` verde.

### M2-3 — Runtime provider-neutral

Metadata:

- Area: Insight M2
- Gate: M2-3
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `1d478f0`
- CI: `38915257810`
- Commit date: 2026-10-16T01:13:11-03:00
- Result: PUBLISHED / CI_GREEN — Provider-neutral runtime
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-3: runtime provider-neutral. Publicado em `1d478f0` com CI `38915257810` verde.

### M2-4 — Decisao provider/model (chain e1dd7c7 -> 8e14824)

Metadata:

- Area: Insight M2
- Gate: M2-4
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `8e14824`
- CI: `38922504778`
- Commit date: 2026-10-16T12:15:25-03:00
- Result: PUBLISHED / CI_GREEN — ADR-007: openai / gpt-5.4-nano-2026-03-17
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-4: decisao provider/model (chain e1dd7c7 -> 8e14824). Publicado em `8e14824` com CI `38922504778` verde.

### M2-5 — Adapter concreto

Metadata:

- Area: Insight M2
- Gate: M2-5
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `d4dbb06`
- CI: `38935882413`
- Commit date: 2026-10-16T13:34:50-03:00
- Result: PUBLISHED / CI_GREEN — OpenAI provider adapter
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-5: adapter concreto. Publicado em `d4dbb06` com CI `38935882413` verde.

### M2-6 — Telemetria/custo

Metadata:

- Area: Insight M2
- Gate: M2-6
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `062431c`
- CI: `39312837865`
- Commit date: 2026-10-16T14:44:43-03:00
- Result: PUBLISHED / CI_GREEN — Safe runtime telemetry
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-6: telemetria/custo. Publicado em `062431c` com CI `39312837865` verde.

### M2-7 — Eval online

Metadata:

- Area: Insight M2
- Gate: M2-7
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `7e494af`
- CI: `39451275264`
- Commit date: 2026-10-19T17:06:46-03:00
- Result: PUBLISHED / CI_GREEN — Online evaluation workflow (manual-only)
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-7: eval online. Publicado em `7e494af` com CI `39451275264` verde.

### M2-8 — CLI e rollout

Metadata:

- Area: Insight M2
- Gate: M2-8
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `8701d85`
- CI: `39461160953`
- Commit date: 2026-10-20T13:14:36-03:00
- Result: PUBLISHED / CI_GREEN — Safe online rollout (two flags)
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Gate M2-8: cli e rollout. Publicado em `8701d85` com CI `39461160953` verde.

### M2-9 — Closure documental

Metadata:

- Area: Insight M2
- Gate: M2-9
- Type: IMPLEMENTATION / PUBLICATION
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md (tabela M2), docs/SPEC-insight-m2.md, git history
- Related SHA: `243ad1a`
- CI: `39479246606`
- Commit date: 2026-10-20T15:27:49-03:00
- Result: PUBLISHED / CI_GREEN — Docs closure published and green
- Superseded: NO

M2-9 e o gate de closure: o commit `243ad1a` foi publicado em `master` e o
run `39479246606` (`tests`/`unittest`) concluiu com sucesso. A auditoria
tecnica final passou; a unica pendencia era documental e foi resolvida por
este commit.

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Auditoria final: veredito `CHANGES_REQUIRED` apenas porque a documentacao
de closure estava desatualizada (P2=1); nada tecnico em aberto (P0=0,
P1=0). Nenhum smoke test real ao provider foi exigido.

### M2-6 — fluxo de auditoria (registro)

O M2-6 preservou a sequencia historica, que nao deve ser achatada:

```text
implementation -> audit CHANGES_REQUIRED -> 2 P2 fixes -> re-audit APPROVED -> publication
```

| P2 encontrado na auditoria inicial | Estado final |
|---|---|
| cached input pricing | CLOSED |
| usage subclass leakage | CLOSED |

O primeiro commit (`efd0a342`) esta na secao de referencias substituidas e
**nao** e o commit final.

### M2-7 — isolamento da eval online

Caracteristicas historicas preservadas:

- `workflow_dispatch` only (manual);
- core CI permanece offline;
- nenhuma chamada real ao provider durante implementacao, auditoria ou publicacao;
- sem LLM judge;
- no maximo uma inferencia por caso;
- artefato sanitizado.

### M2-8 — rollout

Caracteristicas historicas preservadas:

- duas flags (`HERMES_INSIGHT_ENABLED` **e** `HERMES_INSIGHT_ONLINE_ENABLED`),
  default OFF, autorizacao por AND;
- `FALLBACK_DISABLED`, `FALLBACK_CONFIG`, `FALLBACK_PROVIDER`,
  `FALLBACK_INVALID_RESPONSE`;
- invariancia de Prescription;
- zero egress offline.

### Registros de auditoria e closure (M2-6..M2-9)

Registros separados para os gates em que a sequencia auditoria/correcao e
parte do resultado historico. Onde a auditoria encontrou problema, isso esta
registrado — nao foi omitido.

### M2-6-AUDIT — M2-6

Metadata:

- Area: Insight M2
- Gate: M2-6
- Type: AUDIT
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `062431c`
- CI: `39312837865`
- Commit date: 2026-10-16T14:44:43-03:00
- Result: CHANGES_REQUIRED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Auditoria inicial encontrou dois P2: cached input pricing e usage subclass leakage. Nenhum P0/P1.

### M2-6-REAUDIT — M2-6

Metadata:

- Area: Insight M2
- Gate: M2-6
- Type: REAUDIT
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `062431c`
- CI: `39312837865`
- Commit date: 2026-10-16T14:44:43-03:00
- Result: APPROVED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Re-auditoria apos os dois fixes: APPROVE_FOR_MASTER_PUSH.

### M2-7-AUDIT — M2-7

Metadata:

- Area: Insight M2
- Gate: M2-7
- Type: AUDIT
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `7e494af`
- CI: `39451275264`
- Commit date: 2026-10-19T17:06:46-03:00
- Result: APPROVED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Auditoria da eval online: workflow_dispatch only, core offline, sem chamada real e sem LLM judge.

### M2-8-AUDIT — M2-8

Metadata:

- Area: Insight M2
- Gate: M2-8
- Type: AUDIT
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `8701d85`
- CI: `39461160953`
- Commit date: 2026-10-20T13:14:36-03:00
- Result: APPROVED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Auditoria do rollout: duas flags, default OFF, AND, fallbacks distintos, invariancia de Prescription, zero egress offline.

### M2-9-AUDIT — M2-9

Metadata:

- Area: Insight M2
- Gate: M2-9
- Type: AUDIT
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `243ad1a`
- CI: `39479246606`
- Commit date: 2026-10-20T15:27:49-03:00
- Result: CHANGES_REQUIRED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Auditoria final: technical readiness YES, P0=0, P1=0; unico P2 era documentacao de closure desatualizada.

### M2-9-CLOSURE — M2-9

Metadata:

- Area: Insight M2
- Gate: M2-9
- Type: CLOSURE
- Availability: RECONSTRUCTED_METADATA_ONLY
- Evidence: docs/ROADMAP.md, docs/SPEC-insight-m2.md, registro de auditoria do gate
- Related SHA: `243ad1a`
- CI: `39479246606`
- Commit date: 2026-10-20T15:27:49-03:00
- Result: PUBLISHED
- Superseded: NO

#### Historical prompt text

RECONSTRUCTED_METADATA_ONLY

#### Recoverable intent

Commit documental de closure (ROADMAP + SPEC) publicado em master com CI verde; sem release/tag/versao.

## Historical / Superseded References

Commits abaixo **nao** sao versoes canonicas. Estao listados apenas para
impedir que reaparecam como evidencia valida.

| Gate | Reference | Classification | Note |
|---|---|---|---|
| M2-0 | `26a45bc` | SUPERSEDED | Commit local de M2-0 posteriormente substituido pelo canonico 61a520b. |
| M2-4 | `e49a8b` | INVALID / DOES NOT EXIST | Prefixo de commit citado em contexto anterior; fabricado/inexistente. NUNCA tratar como commit valido; nao existe no historico. |
| M2-2 | `a90af0b` | SUPERSEDED | Substituido pelo canonico 1c869c6. |
| M2-6 | `efd0a342` | SUPERSEDED | Substituido pelo canonico 062431c apos fixes de P2. |

`e49a8b` nao e um commit valido deste repositorio. Nenhuma afirmacao deste
arquivo depende dele.

## Open Non-Blocking Engineering Debt

P3 abertos no fechamento do M2. Todos **OPEN_NON_BLOCKING**; nenhum foi
corrigido por este gate.

| # | Item | Status |
|---|---|---|
| 1 | placeholder grammar duplication | OPEN_NON_BLOCKING |
| 2 | public M1 renderer seam | OPEN_NON_BLOCKING |
| 3 | adapter _extract_text heuristic | OPEN_NON_BLOCKING |
| 4 | BadRequest/error-taxonomy clarity | OPEN_NON_BLOCKING |
| 5 | temporary/prunable worktree hygiene | OPEN_NON_BLOCKING |
| 6 | direct scripts/hermes_agent.py invocation | OPEN_NON_BLOCKING |
| 7 | model config vs pricing registry drift risk | OPEN_NON_BLOCKING |
| 8 | API-key surrounding-whitespace preservation | OPEN_NON_BLOCKING |
| 9 | stale local master ref hygiene | OPEN_NON_BLOCKING |
| 10 | adapter api_key=None env fallback boundary | OPEN_NON_BLOCKING |

Descricoes operacionais:

1. **placeholder grammar duplication** — Gramatica de placeholder duplicada entre modulos.
2. **public M1 renderer seam** — Seam publico do renderer M1 exposto alem do necessario.
3. **adapter _extract_text heuristic** — Heuristica `_extract_text` no adapter.
4. **BadRequest/error-taxonomy clarity** — Clareza da taxonomia BadRequest -> FALLBACK_PROVIDER.
5. **temporary/prunable worktree hygiene** — Worktrees temporarios acumulando estado prunable.
6. **direct scripts/hermes_agent.py invocation** — Invocacao direta do script falha (ModuleNotFoundError: src); `-m` funciona.
7. **model config vs pricing registry drift risk** — Risco de drift entre config de modelo e registro de preco.
8. **API-key surrounding-whitespace preservation** — Preservacao de whitespace ao redor da API key.
9. **stale local master ref hygiene** — Ref local de master obsoleta em relacao ao remoto.
10. **adapter api_key=None env fallback boundary** — Adapter aceita api_key=None e cai em os.environ.

## Known Archive Gaps

Lacunas declaradas em vez de reconstruidas. `VERBATIM_NOT_AVAILABLE` significa
que o prompt existiu, mas nao ha texto integral local.

| Tema | Lacuna |
|---|---|
| Prompts de gate do Insight M1, M1.1 e M2-0..M2-9 | Entregues em sessao de chat; nenhum arquivo local preservado. Apenas metadados (SHA/CI/status) sao recuperaveis. |
| PROMPT 27, 28, 29 | Citados em docs/VAULT-SYNC.md e docs/HR-3-HRV-RHR-TRENDS.md sem texto integral. |
| PROMPT 35, 36, 41, 68 | Citados em ROTEIRO-TREINADOR-TALLY e ROADMAP; texto integral indisponivel. |
| PROMPT 57 | O arquivo preservado e um relatorio de pesquisa, nao o prompt. Texto do prompt indisponivel. |
| PROMPT 66, 67 | Citados com resultado (AGENT-0, auditoria de progressao); texto integral indisponivel. |
| Auditorias de M2-0, M2-1, M2-2, M2-3, M2-4, M2-5 | Nao ha evidencia local suficiente para afirmar um prompt de auditoria separado por gate. |
| Prompts de FTP-H1..H8 e PROG-1..PROG-6 | Sem texto preservado; estados recuperados do ROADMAP e specs. |

Registros de auditoria de M2-0..M2-5 nao foram criados como itens separados
porque nao ha evidencia local suficiente de que cada um tenha tido um prompt
proprio. Criar esses itens seria inferencia, nao arquivo.

## Archive Maintenance Rules

1. Um prompt so entra neste arquivo se o texto integral estiver disponivel em
   fonte local confiavel (`VERBATIM`) ou se os metadados forem comprovaveis
   (`RECONSTRUCTED_METADATA_ONLY`).
2. Nunca substituir um prompt `VERBATIM` por uma versao "melhorada",
   resumida, traduzida ou corrigida.
3. Novos gates devem ser adicionados com SHA, CI e status reais; se o texto
   nao existir, declarar `VERBATIM_NOT_AVAILABLE`.
4. Relatorios, diffs e mensagens de commit nunca viram texto de prompt.
5. Segredos nao entram: se um prompt contiver credencial real, o valor deve
   ser removido e marcado como `REDACTED_SECRET`.
6. Este arquivo e historico. Decisoes vigentes vivem em `AGENTS.md`,
   `docs/ROADMAP.md`, `docs/SPEC-*` e nos testes.

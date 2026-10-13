# Estado do Setup OpenCode

**Snapshot histórico reconciliado:** 2026-10-02 (a partir de `git tag` / `git log` / `VERSION`, **não** da memória da sessão).
**Estado oficial atual:** `master` e `VERSION`; release atual `0.0.36`. Confirme com `git rev-parse HEAD`, `git describe --tags --always` e `cat VERSION`.
**Escopo deste arquivo:** os detalhes abaixo são um snapshot de setup de 2026-10-02, não a fonte da versão corrente nem do backlog atual. Para o estado de trabalho, consulte `master`, `VERSION` e `docs/ROADMAP.md`.

> **Como este arquivo é mantido.** Cada afirmação aqui é verificável por comando e foi
> conferida contra o repositório nesta data. Nenhuma linha depende do que "a sessão
> anterior lembrava". Se algo divergir, o `git` ganha — corrija o arquivo, não a memória.
> Foi exatamente a ausência dessa regra que deixou este arquivo afirmar
> `model=openai/gpt-5.6-terra` e "provider único: OpenAI" quando nenhum dos dois era
> verdade (ver *Trilha de Correção*).

## Setup Concluído

Configuração do agente, verificada por leitura dos arquivos:

| item | valor real | onde |
|---|---|---|
| `model` | `opencode/gpt-5.6-sol` | `opencode.json` |
| `small_model` | `openai/gpt-5.6-luna` | `opencode.json` |
| `enabled_providers` | `openai`, `opencode`, `google` | `opencode.json` |
| permissão | `edit: allow`, `bash: ask` | `opencode.json` |
| credenciais | `openai` via **OAuth**; `google` via API key | `~/.local/share/opencode/auth.json` |
| prompts importados | 14 | `prompts/opencode/` |
| Python | 3.14.7 | `python3 -V` |
| dependência | `requests>=2.31` | `requirements.txt` |
| CI | `python3 -m unittest discover -s tests -v` | `.github/workflows/test.yml:21`, idêntico ao `AGENTS.md` |
| suíte | **788** testes (222 científicos) | `unittest discover -s tests` |

**OpenAI não tem API key configurada** — é OAuth. Não existe `.env` em
`~/.config/opencode/` nem em `~/`.

## Os 14 Prompts: Todos Entregues

Este era o erro central do arquivo. A versão anterior dizia *"aguarda instrução
para P0-03"*, mas **P0-03 e mais dez módulos já estão commitados e publicados**.
Seguir aquela instrução reconstruiria trabalho entregue.

| # | prompt | entregável | primeira tag |
|---|---|---|---|
| 01 | P0-01 Training Load / TSS | `power_training_load`, `estimated_tss`, `TrainingLoadComponents` | v0.0.32 (`2e6c232`) |
| 02 | P0-02 Periodização vs TSB | `TrainingPlanState` separa fase de autoregulação | v0.0.33 (`896e84d`, `b4a9548`) |
| 03 | P0-03 TrainingPhase | `src/training_phase.py` | v0.0.34 |
| 04 | P0-04 ProgressionEngine | `src/progression.py` | v0.0.34 |
| 05 | P1-01 IntensityDistribution | `src/intensity_distribution.py` | v0.0.34 |
| 06 | P1-02 AthletePhysiologicalProfile | `src/athlete_profile.py` | v0.0.34 |
| 07 | P1-03 AdaptationState | `src/adaptation.py` | v0.0.34 |
| 08 | P1-04 TrainingDecisionEngine | `src/training_decision.py` | v0.0.34 |
| 09 | P1-05 ReadinessAssessment | `src/readiness_assessment.py` | v0.0.34 |
| 10 | P2-01 Critical Power / W' | `src/critical_power.py` | v0.0.34 |
| 11 | P2-02 VO2WorkoutGenerator | `src/vo2_generator.py` | v0.0.35 |
| 12 | P2-03 Refinar Z2, Sweet Spot e Threshold | `src/zone_intent.py` (`f9550ea`) | v0.0.35 |
| 13 | P2-04 Consolidar EMBASAMENTO | 17 seções em `docs/EMBASAMENTO-CIENTIFICO.md` (`6473b97`) | v0.0.35 |
| 14 | P3-01 Scientific Regression Tests | 222 testes em `tests/scientific/` (`0f71f8a`) | v0.0.35 |

Como reexecutar a verificação:

```bash
for m in training_phase progression intensity_distribution athlete_profile \
         adaptation training_decision readiness_assessment critical_power \
         vo2_generator zone_intent; do
  c=$(git log --format=%H --reverse -- src/$m.py | head -1)
  printf '%-22s %s\n' "$m" \
    "$(git tag --contains "$c" | grep -oE 'v[0-9.]+' | sort -V | head -1)"
done
```

## Trabalho Aberto

Nada aqui é "o próximo prompt da fila" — é o que continua **aberto** no ROADMAP.

| item | tipo | o que é |
|---|---|---|
| **58** | decisão de escopo | **O problema real.** Nove dos dez módulos de P0–P3 (`training_phase`, `progression`, `intensity_distribution`, `athlete_profile`, `adaptation`, `training_decision`, `critical_power`, `vo2_generator`, `zone_intent`) ainda não são importados por `src/plan.py` nem `src/training_plan.py`. São computação correta e testada que **não chega ao treino**. Integrar muda `plan.json` e valores de `focus` publicados no Intervals — por isso é decisão, não refatoração. |
| **59** | decisão de escopo | Quatro limites de implementação documentados em §14 da SPEC, com trava de teste, nenhum corrigido: `SEQUENCES` × regra de dimensão única (§11); `INTENSITY` inerte na faixa padrão (§12); `decay()` sem teto superior (§10); `estimate_cp` enviesado (§3). Cada um muda prescrição. |
| **40** | refactor | `reconcile` não é idempotente: `absorbed_ids` é reconstruído a cada execução, então o mesmo treino perdido pode ser absorvido repetidamente, elevando `on_sec` a cada run até o teto. |
| **41** | limpeza | `by_id` é montado e populado em `_absorb_missed_into_budget()` e nunca consultado (dead code). Remover junto do #40 — ambos tocam a mesma função. |
| 13, 23, 35 | produto / validação | Assistentes de IA padrão Tredict; portal + teste real com 2º atleta; consistência com dados de outros atletas. |

### Ressalva sobre o item 58

O ROADMAP lista `readiness_assessment` entre os dez módulos isolados. Isso **mudou
parcialmente**: `src/readiness.py` importa `ReadinessAssessment`, e
`src/training_plan.py:439,727` chama `assess_readiness_assessment()`. Desde o
Passo A (§15) o modelo de 7 eixos chega ao plano por `check --apply`, executado no
script diário antes do `push`. `build` continua sem importá-lo — são caminhos
distintos. Os outros **nove** seguem de fato isolados.

## Estado do Repositório

Worktree com trabalho **não commitado** (verificar com `git status` antes de agir):

Arquivos do setup, ainda sem commit:

- `opencode.json`
- `AGENTS.md`
- `.opencode/agent/cycling-coach.md`
- `.opencode/command/retomar.md`
- `prompts/opencode/` (14 arquivos)
- `docs/OPENCODE-SETUP-STATE.md` (este arquivo)

Trabalho do Passo A / issue #58, ainda sem commit — **conjunto separado**, não
misturar com o cluster acima:

- `src/plan.py`, `src/readiness.py`, `src/training_plan.py`
- `scripts/daily_reconcile.sh`
- `tests/test_readiness_step_a.py`, `tests/test_readiness_today.py`, `tests/test_periodization_state.py`
- `docs/SPEC-passo-A-readiness.md`, `docs/EMBASAMENTO-CIENTIFICO.md`, `docs/ROADMAP.md`, `docs/ROTEIRO-TESTES.md`
- `CHANGELOG.md`, `README.md`

`relatorio-mes.html` é artefato gerado (60 K, relatório do mês). **Já estava não
rastreado antes do setup** — mtime 2026-09-29, anterior ao setup de 2026-10-01.
Preservar; não faz parte de nenhum dos dois trabalhos.

## `.opencode/command/retomar.md`

O comando manda ler este arquivo e executar "exclusivamente o próximo trabalho
registrado". A próxima entrada deixou de ser um prompt e passou a ser *Trabalho
Aberto*. **Nunca usar `/retomar` para reexecutar prompts da fila** — todos estão
entregues. Para retomar trabalho do Passo A, leia
`docs/SPEC-passo-A-readiness.md`; a issue #58 continua **aberta**.

## Limites Conhecidos Deste Arquivo

1. **Não substitui o `git`.** Se este arquivo e `git tag` divergirem, o `git` vence.
2. **Os números de suíte envelhecem.** 788 é o valor em 2026-10-02, já sob o
   `[Unreleased]` do CHANGELOG. Reconfirme antes de citar.
3. **A política do agente está desatualizada.** `.opencode/agent/cycling-coach.md`
   carrega "política vigente v0.0.31"; a versão publicada é v0.0.35.

## Trilha de Correção

O que esta reconciliação encontrou, para que o próximo não reabra as mesmas
questões. Duas afirmações da versão de 2026-10-01 eram **falsas**:

| afirmação anterior | real |
|---|---|
| `model=openai/gpt-5.6-terra` | `opencode/gpt-5.6-sol` |
| "Provider único: OpenAI" | três providers habilitados, e há credencial `google` |

E três estavam **obsoletas**: política `v0.0.31` (publicada: v0.0.35), baseline de
395 testes (atual: 788) e a fila de prompts (todos entregues).

O que **conferiu** e foi mantido: os três commits citados (`2e6c232`, `896e84d`,
`b4a9548`) existem com os subjects exatos; 14 prompts com os nomes certos; Python
3.14.7; comando de CI idêntico ao do repositório; OpenAI autenticado por OAuth sem
API key em lugar nenhum; e o DOI `10.1123/ijspp.2022-0302` citado no P0-01 é real
— Galán-Rioja, González-Ravé, González-Mohíno & Seiler, *IJSPP* 2023;18(2):112-122,
PMID 36640771.
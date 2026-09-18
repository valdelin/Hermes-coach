# Changelog

Todas as mudanças relevantes do **Hermes Coach**. O formato segue
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o versionamento,
[SemVer](https://semver.org/lang/pt-BR/).

As versões aqui correspondem às **tags** do repositório (git tag) e aos
[releases publicados no GitHub](https://github.com/valdelin/Hermes-coach/releases).
As versões intermediárias (v0.0.3–v0.0.6) foram bumpados no `VERSION` sem tag
própria — foram agrupadas na tag/release v0.0.7.

## [Unreleased]

### Adicionado

- `docs/KNOWN_ISSUES.md`: rastreio de bugs conhecidos do projeto. Registrada a
  issue [#1](https://github.com/valdelin/Hermes-coach/issues/1) — o Intervals
  materializa o evento `hermes-plan*` como atividade MANUAL "fantasma" ao
  sincronizar o treino (sem endpoint de merge na API; proposta de limpeza
  automática registrada para o futuro).
- **TODO registrado** (issue
  [#2](https://github.com/valdelin/Hermes-coach/issues/2)): enviar resumo do
  treino por **e-mail, WhatsApp ou Telegram** (foco + TSB + TSS previsto/real +
  avisos do reconcile) — adicionado às **Direções futuras** do README.
- **TODO registrado** (issue
  [#3](https://github.com/valdelin/Hermes-coach/issues/3)): suporte a **treinos
  sem medidor de potência** (outdoor/FC) — detectar ausência de potência,
  `FTHR` no `.env`, carga por FC (`hrTSS`) e alvos %FTHR/RPE — adicionado às
  **Direções futuras** do README.
- `docs/ROADMAP.md`: plano consolidado das próximas implementações (fases
  0-4, issues #1-#3 + produto estilo Runna + multi-atleta); README agora
  aponta para o roadmap.
- **TODO registrado** (issue
  [#4](https://github.com/valdelin/Hermes-coach/issues/4)): **ativar sync de
  wellness** (Garmin Connect → Intervals.icu: RHR, sono, Body Battery;
  avaliar HRV para o futuro) — adicionado às **Direções futuras** do README e
  ao roadmap (Fase 0).

## [0.0.8] - 2026-09-18

### Adicionado

- **Motor de carga fisiológica (Banister Impulse-Response)** — `src/impulse_response.py`,
  implementando o spec da seção 1 do `docs/ARQUITETURA.md`:
  - `ImpulseResponseEngine.calculate_tss(duration, avg_intensity, threshold)` — TSS padrão
    `IF² × horas × 100` (retorna 0 para threshold ≤ 0);
  - `ImpulseResponseEngine.compute_metrics(daily_tss_history, initial_ctl, initial_atl)` —
    suavização exponencial com constantes 42/7 dias (CTL/ATL/TSB);
  - `daily_tss_series(events)` — série diária de TSS dos eventos do Intervals
    (`tss`/`icu_training_load`), mesmo critério de carga do reconcile.
- CLI `python3 src/training_plan.py model`: métricas do motor local vs
  Intervals.icu (com diferença) e **projeção** do TSB ao seguir o `plan.json`.
- 14 testes novos (64 no total); docs atualizadas (README pt/en, `docs/ARQUITETURA.md`).

### Documentação (entrou após v0.0.7)

- `docs/ARQUITETURA.md`: conceito original do agente (motor
  Impulse-Response/Banister, schema de estado do atleta, system prompt de
  corrida) sincronizado com o vault do Obsidian, com a tabela de diferenças
  para a implementação atual e notas de design aproveitáveis (rampagem
  +10%, teto de TSB, periodização por fases).
- README pt/en: seções **Documentação** (link para o spec) e **Direções
  futuras** (multi-atleta, modo solo, IA vs biblioteca, deload, corrida).
- `.gitignore` ignora `.env.bak` / `.env.*.bak`.

## [0.0.7] - 2026-09-18

### Adicionado
- `build` e `reconcile` agora imprimem a agenda de treinos em uso
  (`Agenda: seg,ter,qua,qui,sex`) e avisam quando `TRAINING_DAYS` não está
  definido no `.env` (usa o padrão).

## [0.0.6] - 2026-09-18

### Corrigido
- `scripts/daily_reconcile.sh`: `set -e` era desativado dentro do bloco
  `{ ...; } || { ...; }` (contexto condicional) — uma falha no `reconcile`
  não parava o fluxo nem notificava. Cada passo agora roda via `step()`, que
  loga, emite `notify-send` no desktop e sai com código != 0 na primeira falha.

## [0.0.5] - 2026-09-18

### Corrigido
- `_reduce_next_hard` reduz o mesmo limite (ex.: Limiar) no máximo uma vez por
  `reconcile`: o guard `reduced_ids` é compartilhado entre treinos perdidos e
  treinos extras, evitando dupla-redução quando dois eventos caem na mesma
  janela.

## [0.0.4] - 2026-09-18

### Adicionado
- O `reconcile` detecta **treinos extras fora do plano** (eventos com
  `paired_activity_id` e `external_id` não-hermes) na janela dos últimos 7 dias.
  Se a soma da carga chegar a um treino cheio (`>= cap_diario`, via `tss` ou
  fallback `icu_training_load`), o próximo dia de treino vira recuperação e o
  próximo Limiar é reduzido 5%. Trabalho leve não altera o plano.
- Testes cobrindo a detecção de extras e a recuperação inserida.

## [0.0.3] - 2026-09-18

### Adicionado
- Agenda de treinos **configurável** via `TRAINING_DAYS` no `.env`
  (nomes em pt `seg,ter,...` ou en `mon,tue,...`; padrão seg-sex). O foco do
  dia segue a posição na agenda.
- Testes de agenda parcial e mensagens explicativas em ambos os idiomas.

## [0.0.2] - 2026-09-16

### Adicionado
- Arquivo `VERSION` (passa a gerar versões explícitas).
- **Mensagens explicativas** (`cue text` + intervalos flat) publicadas em cada
  treino no Intervals — o aquecimento explica a zona e cada intervalo recebe
  "Agora voce vai entrar em X minutos a Y por cento do seu FTP".
- `CUE_LANG` no `.env` (`pt`|`en`) controla o idioma das mensagens.

## [0.0.1] - 2026-09-15

### Adicionado
- Baseline do projeto (`zwift-coach` → **hermes-coach**): agente opencode
  `cycling-coach`, skill do Hermes, clientes `intervals_client.py`,
  `coach.py` (TSB → foco → carga) e CLI `training_plan.py`
  (`info`/`build`/`reconcile`/`push`/`all`).
- Plano semanal por TSB, orçamento de carga (TSS 7 dias ≤ `cap_diario × 7`),
  upsert por `external_id` (sem duplicar eventos), publicacao no calendário do
  Intervals.icu e README em pt/en.
- CI: GitHub Actions roda `unittest` (Python 3.12) em todo push e PR — 50
  testes, stdlib-only.

---

## Como manter

Ao criar uma nova versão (bump de `VERSION`):

1. Adicione a seção da versão sob **Unreleased**, ou mova o conteúdo de
   `## [Unreleased]` para a nova tag.
2. Crie a **tag** (`git tag v0.0.X`) e a **release** no GitHub
   (`gh release create v0.0.X`).
3. Linke a nova versão na seção de comparações ao final deste arquivo.

## Comparações (links)

- [v0.0.8…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.8...master)
- [v0.0.7…master](https://github.com/valdelin/Hermes-coach/compare/v0.0.7...master)
- [v0.0.2…v0.0.7](https://github.com/valdelin/Hermes-coach/compare/v0.0.2...v0.0.7)
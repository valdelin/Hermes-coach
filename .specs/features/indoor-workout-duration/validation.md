# Validation: Configuração de duração de treino indoor — PASS

**Date**: 2026-10-23
**Spec**: `.specs/features/indoor-workout-duration/spec.md`
**Diff range**: uncommitted working tree; verifier scope: `.env.example`, `src/plan.py`, `src/application.py`, `src/training_plan.py`, `src/athlete_profile.py`, `tests/test_plan.py`, `tests/test_training_plan.py`
**Verifier**: independent sub-agent (author ≠ verifier)

## Verdict

PASS. O fixture de DUR-01 agora produz uma sessão de 300 min quando o cap é removido ou adulterado; os três mutantes relevantes foram mortos em cópias temporárias. Nenhum arquivo da árvore real foi alterado pelo sensor.

## Spec-anchored acceptance criteria

| Requirement | Expected outcome | Evidence | Result |
|---|---|---|---|
| DUR-01 | Configuração ausente usa teto de 180 min. | `src/training_plan.py:197-205` devolve 10.800 s; `src/plan.py:300-306,1057-1059,1177-1178` normaliza e aplica o teto. `tests/test_plan.py:1407-1421` usa carga concluída suficiente e afirma duração >120 min e ≤180 min para cap ausente. | ✅ PASS |
| DUR-02 | Valor entre 30–180 min chega ao reader e limita sessão futura. | `src/plan.py:121-132`, `src/training_plan.py:197-205,791-798`, `src/plan.py:1177-1178`; `tests/test_training_plan.py:40-45` afirma 45 min no reader e `tests/test_plan.py:1394-1402` afirma aplicação de cap. | ✅ PASS |
| DUR-03 | Valor inválido avisa e mantém 180 min. | `src/training_plan.py:201-205` emite aviso e retorna 10.800 s; `src/plan.py:300-306` normaliza inválido ao default; `tests/test_training_plan.py:32-38` cobre inválido e `tests/test_plan.py:1413-1421` cobre 29/181 no build. | ✅ PASS |
| DUR-04 | Compactação deixa duração ≤ teto sem alterar potência ou foco. | `src/plan.py:267-297,1177-1178`; `tests/test_plan.py:1423-1436` afirma duração, `on_power` e `focus` para Threshold/VO2. | ✅ PASS |
| DUR-05 | Compactação mantém warm-up/cooldown ≥5 min e work/recovery ≥1 min. | `src/plan.py:274-280,292-296`; `tests/test_plan.py:1432-1435`. | ✅ PASS |
| DUR-06 | Sessão de hoje existente não recebe teto novo. | `src/plan.py:1066-1106`; `tests/test_plan.py:70-83` passa cap de 30 min e preserva duração existente de 240 min. | ✅ PASS |

## Gate check

- **Focused:** `python3 -m unittest tests.test_plan.MaxWorkoutDurationTest tests.test_plan.BuildPlanTest.test_build_preserva_treino_de_hoje_do_plano_atual tests.test_training_plan.MaxWorkoutDurationConfigTest -v`
- **Result:** 8 passed, 0 failed.
- **Diff hygiene:** `git diff --check` passed.

## Discrimination sensor

Mutantes foram aplicados exclusivamente a uma cópia temporária de `src/` em `/tmp/opencode`. O `git status --porcelain` da árvore real foi idêntico antes e depois.

| Mutation | File:line | Result |
|---|---|---|
| Desabilitar `_cap_workout_duration`, retornando os parâmetros originais | `src/plan.py:267` | ✅ Killed: `tests/test_plan.py:1420` falhou (18.000 s > 10.800 s), além do teste de qualidade. |
| Trocar default ausente por 300 min | `src/plan.py:302-303` | ✅ Killed: `tests/test_plan.py:1420` falhou (18.000 s > 10.800 s). |
| Forçar `on_power=0.50` na compactação | `src/plan.py:290-296` | ✅ Killed: `tests/test_plan.py:1431` falhou (`0.5 != 0.98`). |

**Sensor result:** 3/3 killed — **PASS**.

## Diff status

- Arquivos de implementação e testes do escopo permanecem modificados e não commitados.
- Há modificações e arquivos não rastreados fora do escopo; não foram alterados por esta verificação.
- Este relatório é o único arquivo alterado pelo verificador.

## Verificação independente — preferência individual de 60 min

**Verdict: PASS.** Com `MIN_REGULAR_DURATION_MINUTES=60` propagado como
`min_regular_duration_sec=3600`, uma sessão de qualidade que permanece abaixo
de 60 min após as proteções é substituída por recuperação ativa Z2 de 60 min.
Sem a preferência, o mesmo cenário mantém os focos e as durações globais.

| Cenário determinístico | Resultado observado |
|---|---|
| `tsb=0`, `ftp=195`, `start=2026-10-26`, agenda seg/qua/sex, `goal=ftp-builder`, preferência de 60 min | Os três slots curtos foram publicados como `zone2`, `on_power=0.60`, nome `Recuperacao ativa (Z2)` e `planned_duration=3600`: 26/10, 28/10 e 30/10. |
| Mesmas entradas, sem `min_regular_duration_sec` | Permaneceram `sweetspot`/`threshold`/`sweetspot`, com 3000/3060/3320 s, sem nome de recuperação. |

**Evidência de código:** `src/plan.py:1182-1204` primeiro tenta estender a
sessão dentro das proteções e, se a qualidade ainda ficar abaixo do mínimo,
constrói recuperação Z2 e troca `focus`/nome; `src/plan.py:1541-1567` mantém
o caminho sem efeito quando a preferência é `None`. A constante de 60 min é
`MIN_REGULAR_DURATION_SEC = 3600` em `src/plan.py:196`; a leitura e propagação
do valor configurado passam por `src/training_plan.py:214-222,753-795`.

**Gate focado:**

```text
python3 -m unittest tests.test_availability.MinimumRegularDurationTest \
  tests.test_plan.MaxWorkoutDurationTest \
  tests.test_application.ReadinessUseCaseTest.test_check_rebuild_propagates_minimum_regular_duration \
  tests.test_application.ReadinessUseCaseTest.test_check_default_minimum_duration_preserves_legacy_build_arguments \
  tests.test_training_plan.CheckAdapterTest.test_cmd_check_encaminha_minimum_duration_do_build -v
```

Resultado: **12 passed, 0 failed**.

**Suite CI-equivalente:** `python3 -m unittest discover -s tests -v` —
**1558 passed, 0 failed**.

### Discrimination sensor (cópia temporária)

Executado em uma cópia de `src/` sob `/tmp/opencode`; a árvore real não foi
alterada pelo sensor.

| Mutation | Oráculo independente | Result |
|---|---|---|
| Desabilitar o bloco de substituição em `src/plan.py:1192-1204` | O cenário com preferência deve produzir três Z2 de 3600 s. | ✅ Killed: permaneceram Sweet Spot/Limiar curtos. |
| Fazer o bloco aplicar `60 min` quando `min_regular_duration_sec` está ausente | O cenário sem preferência deve manter `sweetspot`/`threshold`/`sweetspot` e 3000/3060/3320 s. | ✅ Killed: os slots viraram Z2 de 3600 s. |

**Sensor result:** 2/2 killed — **PASS**.

**Cobertura observada:** `tests/test_plan.py:1438-1449` cobre a preferência,
mas só exige que exista algum Z2 com duração mínima. O oráculo independente
acima foi necessário para afirmar explicitamente a substituição de toda a
qualidade curta e a invariância quando a preferência está ausente.

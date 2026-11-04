# Validação — Ações operacionais na TUI

Verificador independente (HEAD: `fd41e4c`). Revisão contra `spec.md`, `context.md`, `design.md`, `tasks.md`.

## Gates

| Gate | Comando | Resultado |
|---|---|---|
| Quick | `python3 -m unittest tests.test_ui_operations -v` | PASS (13/13) |
| Build | `python3 -m unittest discover -s tests -v` | OK (1601 testes; falha não relacionada a UI: `tests.test_cli_training_plan.TestCLIBuild.test_build_rejects_past_ftp_test_date` — data futura/padrão de ambiente) |

## Checagem ancorada em UIOPS-01..UIOPS-07 (com evidência `arquivo:linha`)

| Req | Evidência | Status |
|---|---|---|
| UIOPS-01 | `src/ui/operations.py:54-71` (previews consultivas: build `--dry-run`, check `--dry-run`, reconcile `--show`, push `--dry-run`, sem `--yes`). `tests/test_ui_operations.py:15-26` cobre. `src/ui/screens/operation.py:49-84` renderiza comando/exit code/saída. | PASS |
| UIOPS-02 | `src/ui/operations.py:54-71` (apply só com `--yes` em catálogo fechado). `src/ui/operations.py:127-150` (`apply()` só permite após `FIRST_CONFIRM`). `src/ui/screens/operation.py:89-116` não inicia apply sem confirmação. `tests/test_ui_operations.py:27-40,80-92,135-149,177-186` cobrem. | PASS |
| UIOPS-03 | `src/ui/operations.py:151-153` cancela sem apply se não em `APPLYING`. `src/ui/screens/operation.py:91-107` bloqueia cancelamento durante `APPLYING`/preview em execução; `tests/test_ui_operations.py:177-186` confirma cancelamento não chama apply. Prévia com falha não habilita apply (`src/ui/operations.py:123-126`, `tests/test_ui_operations.py:93-102`). | PASS |
| UIOPS-04 | `src/ui/operations.py:66-71` push preview `push --dry-run`. `src/ui/operations.py:127-141` fluxo vai para `TYPED_CONFIRM` se houver `typed_confirmation`. `tests/test_ui_operations.py:135-149` cobre ordem dry-run→continuação→texto→apply com `--yes`. | PASS |
| UIOPS-05 | `src/ui/operations.py:134-140` `confirm_typed` exige valor exato `PUBLICAR`. `src/ui/screens/operation.py:108-120` mostra input só em `TYPED_CONFIRM`, habilita apply só após confirmação correta. `tests/test_ui_operations.py:135-149` cobre "publicar" falha, "PUBLICAR" sucesso. | PASS |
| UIOPS-06 | `src/ui/operations.py:114-150` máquina de estados serializa: preview→confirma→apply; apply só em `FIRST_CONFIRM`. `src/ui/screens/operation.py:53-60,89-116` usa worker exclusivo/thread, desabilita ações durante execução; `tests/test_ui_operations.py:74-102` cobre transições. | PASS |
| UIOPS-07 | `src/ui/operations.py:81-108` runner usa lista argv `[sys.executable, FACADE, *argv]`, `shell=False`, `cwd=root`, captura stdout/stderr/exit code; converte `OSError` em `OperationResult` com returncode!=0 (`tests/test_ui_operations.py:41-72`). `src/ui/screens/operation.py:80-84` mostra comando lógico e exit code. `src/ui/screens/dashboard.py:110-126` e `src/ui/screens/readiness.py:199-203` conectam ações via modal com callback de reload. `tests/test_ui_operations.py:110-134,160-176` cobrem. | PASS |

## Discrimination sensor (mutações comportamentais em cópia/estado isolado)

Executado em cópia isolada (`/tmp/uiops-mutate-*`), sem `git stash`, sem alterar árvore real.

| Mutação | Comportamento esperado | Resultado |
|---|---|---|
| Remover `--yes` do apply de `BUILD` no catálogo (cópia) | `OperationCatalogTest` falha (apply deixa de ter `--yes`) | Detectado (teste falha conforme esperado) |
| Permitir apply sem prévia (remover checagem em `OperationFlow.apply`) | `test_previa_com_sucesso_habilita_apply_normal_so_apos_confirmar` falha (permite apply direto) | Detectado |
| Aceitar qualquer texto para push (ignorar `typed_confirmation`) | `test_push_exige_texto_exato_antes_de_apply` falha ("publicar" aceito / apply não bloqueado) | Detectado |
| Usar `shell=True` no runner (cópia) | `FacadeRunnerTest.test_executa_lista_na_raiz_e_captura_todas_as_saidas` falha (kwargs `shell` errado / construção de comando) | Detectado |
| Chamar apply em cancelamento (fluxo modificado) | `test_cancelamento_nunca_chama_apply` falha (apply executado) | Detectado |

## Gaps / Observações

- Nenhum gap bloqueante identificado frente aos requisitos mapeados. Os testes existentes cobrem catálogo, runner, fluxo, entradas de tela, refresh, formatação de saída e caminhos de falha/cancelamento.
- Falha única na suíte completa é pré-existente/ambiental (`tests.test_cli_training_plan.TestCLIBuild.test_build_rejects_past_ftp_test_date`) e não relacionada à feature UI.

## Veredito

**PASS** — Coberto e gates verdes (UI operations 13/13). Todos UIOPS-01..UIOPS-07 verificados com evidência arquivo:linha; mutações comportamentais são detectadas pelos testes.

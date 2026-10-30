# Ações operacionais na TUI — Specification

## Problem Statement

O dashboard da TUI mostra botões para gerar, verificar prontidão, reconciliar e
publicar, mas eles ainda não executam o fluxo operacional. O atleta precisa
revisar uma prévia e confirmar explicitamente qualquer mutação, sem que a TUI
duplique regras do motor ou contorne a facade de segurança.

## Goals

- [ ] Executar `build`, `check`, `reconcile` e `push` exclusivamente pela facade.
- [ ] Exigir prévia e confirmação antes de mudanças locais ou externas.
- [ ] Exigir duas confirmações para publicar no calendário do Intervals.icu.
- [ ] Mostrar saída, falha e cancelamento de cada operação na TUI.

## Out of Scope

| Feature | Reason |
|---|---|
| Chamar `src/training_plan.py` diretamente | Violaria a fronteira de segurança da facade. |
| Executar `daily`, `all`, `raw`, FTP scan ou vault sync | São workflows distintos e ficam fora desta entrega. |
| Criar ou editar treino manualmente na TUI | A UI não se torna motor prescritivo. |
| Persistir histórico de logs de operação | Não é necessário para a operação local inicial. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|---|---|---|---|
| Prévia de reconcile | `hermes_agent.py reconcile --show` | É o modo consultivo existente; `reconcile` sem `--show` grava `plan.json`. | y |
| Aplicação após prévia | TUI executa a facade com `--yes` somente depois da confirmação visual | A facade continua sendo o único executor; a TUI substitui o stdin interativo apenas após consentimento explícito. | y |
| Dupla confirmação de push | Botão de continuidade e digitação literal `PUBLICAR` | Torna a escrita externa deliberada e auditável na interação. | y |
| Atualização após sucesso | Recarregar a tela de origem | Reflete plano/calendário alterado sem manter estado local falso. | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Prévia e aplicação de alterações locais ⭐ MVP

**User Story**: Como atleta, quero simular gerar plano, checar prontidão ou
reconciliar antes de aplicar a alteração para revisar o efeito em segurança.

**Why P1**: O plano local é contrato persistido; a TUI só pode alterar após
mostrar o resultado consultivo e obter confirmação.

**Acceptance Criteria**:

1. WHEN o atleta iniciar `build`, THEN a TUI SHALL executar `scripts/hermes_agent.py build --dry-run` sem `--yes` e mostrar stdout, stderr e exit code.
2. WHEN o atleta iniciar `check`, THEN a TUI SHALL executar `scripts/hermes_agent.py check --dry-run` sem `--yes` e mostrar stdout, stderr e exit code.
3. WHEN o atleta iniciar `reconcile`, THEN a TUI SHALL executar `scripts/hermes_agent.py reconcile --show` sem `--yes` e mostrar stdout, stderr e exit code.
4. WHEN uma prévia retornar exit code zero, THEN a TUI SHALL oferecer a ação `Aplicar` correspondente sem executá-la automaticamente.
5. WHEN o atleta confirmar `Aplicar`, THEN a TUI SHALL executar somente `scripts/hermes_agent.py <ação> --yes` com os argumentos mutáveis definidos para a ação.
6. IF o atleta cancelar a confirmação, THEN a TUI SHALL não iniciar subprocesso mutável nem enviar `--yes`.
7. IF uma prévia ou aplicação retornar exit code não zero, THEN a TUI SHALL mostrar a saída capturada, marcar a operação como falha e não oferecer confirmação de aplicação para aquela prévia.

**Independent Test**: Um runner falso registra argv e resultados; cada ação
produz a prévia correta e só executa argv mutável após confirmação.

---

### P1: Publicação externa protegida

**User Story**: Como atleta, quero revisar a simulação de publicação e confirmar
duas vezes antes de escrever no calendário do Intervals.icu.

**Why P1**: `push` é escrita externa e pode alterar eventos no calendário.

**Acceptance Criteria**:

1. WHEN o atleta iniciar publicação, THEN a TUI SHALL executar `scripts/hermes_agent.py publicar --dry-run` sem `--yes` e mostrar a saída.
2. WHEN o dry-run de publicação retornar exit code zero, THEN a TUI SHALL exigir uma confirmação de continuidade antes de exibir a confirmação textual final.
3. WHEN o atleta informar exatamente `PUBLICAR` na segunda confirmação, THEN a TUI SHALL executar `scripts/hermes_agent.py publicar --yes`.
4. IF a confirmação textual for diferente de `PUBLICAR` ou for cancelada, THEN a TUI SHALL não executar publicação nem enviar `--yes`.
5. IF o dry-run ou a publicação retornar exit code não zero, THEN a TUI SHALL mostrar a saída capturada e SHALL não tentar nova operação automaticamente.

**Independent Test**: Um runner falso comprova a ordem dry-run → primeira
confirmação → texto `PUBLICAR` → push com `--yes`, e comprova ausência de push
nos demais caminhos.

---

### P2: Execução observável e serializada

**User Story**: Como atleta, quero acompanhar uma operação em execução e evitar
que duas operações concorrentes alterem o mesmo plano ou calendário.

**Why P2**: O CLI/facade é síncrono e seus efeitos devem acontecer em ordem.

**Acceptance Criteria**:

1. WHILE uma operação estiver em execução, THEN a TUI SHALL desabilitar novas ações operacionais e indicar que a operação está em andamento.
2. WHEN uma operação terminar com sucesso, THEN a TUI SHALL atualizar a tela de origem antes de habilitar novas ações.
3. The TUI SHALL executar subprocessos com lista de argumentos e diretório raiz do repositório, sem shell arbitrário.
4. The TUI SHALL registrar na visualização o comando lógico, stdout, stderr e exit code da última operação, sem expor credenciais.

**Independent Test**: Um runner bloqueável demonstra exclusão mútua; testes de
argv confirmam execução sem shell e sem dados secretos.

---

## Edge Cases

- IF `scripts/hermes_agent.py` não puder ser iniciado, THEN a TUI SHALL mostrar
  uma falha de infraestrutura sem executar fallback direto ao motor.
- IF a saída do subprocesso estiver vazia, THEN a TUI SHALL mostrar o exit code
  e uma mensagem de saída vazia.
- IF a tela for fechada enquanto a operação estiver em andamento, THEN a TUI
  SHALL manter a operação observável até terminar ou informar que o encerramento
  foi recusado durante execução.

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
|---|---|---|---|
| UIOPS-01 | P1: alterações locais | Execute | Implementing |
| UIOPS-02 | P1: alterações locais | Execute | Implementing |
| UIOPS-03 | P1: alterações locais | Execute | Implementing |
| UIOPS-04 | P1: publicação | Execute | Implementing |
| UIOPS-05 | P1: publicação | Execute | Implementing |
| UIOPS-06 | P2: execução | Execute | Implementing |
| UIOPS-07 | P2: execução | Execute | Implementing |

**Coverage:** 7 total, 0 mapped to tasks, 7 unmapped ⚠️

## Success Criteria

- [ ] Nenhuma ação mutável é iniciada sem prévia e confirmação aplicável.
- [ ] Nenhum caminho da TUI executa o motor diretamente.
- [ ] O atleta consegue explicar o resultado ou a falha da última operação sem
  precisar sair da TUI.

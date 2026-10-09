# SPEC - FTP-H3: Block Context Persistido

Status: implementado como boundary v1. Esta especificacao nao implementa FTP-H4,
FTP-H5, FTP-H6, periodizacao, fase ou mutacao de prescricao.

## Contrato

`BlockContext` e a identidade canônica do bloco ativo persistida em `plan.json`:

```json
{
  "schema_version": 1,
  "id": "block-2026-10",
  "started_on": "2026-10-08",
  "goal": "ftp-builder"
}
```

- `id` e identificador opaco, não vazio, fornecido explicitamente pelo chamador.
- `started_on` e data ISO (`YYYY-MM-DD`) injetada pelo chamador; nunca e derivada de
  `datetime.now()` dentro do domínio.
- `goal` e snapshot opcional do objetivo no começo do bloco; não substitui a metadata
  corrente do plano nem seleciona fase.
- `schema_version` e obrigatório. Payload inválido ou versão desconhecida falha fechada.
- Plano legado, sem `block_context`, continua válido e devolve `None`.

## Boundary

`Application.start_training_block()` e o único use-case v1 para gravar o contexto.
Ele não altera workouts, FTP, fase, TSS, calendário ou provider. Substituir um contexto
ativo exige `replace=True`; a policy que decide quando abrir/fechar/substituir blocos
continua fora do escopo.

Escritas locais que preservam metadata (`_save_with_meta`) preservam também o contexto.
O contexto não é fonte de fase: `TrainingPhaseEngine`, `GOAL`, periodização e readiness
continuam advisory/contratos separados.

## Dependências Futuras

- FTP-H4 pode usar `started_on` como boundary explícita para Advice quando FTP canônico
  estiver `UNKNOWN`, sem mudar plano ou referência.
- PROG-2/3 pode consumir o contexto somente após as decisões Q1-Q4 e os seams de
  execution/recovery-week.
- FTP-H6 resolve FTP temporal e prescrição em contrato separado; esta boundary não
  autoriza build a consumir `FtpHistory`.

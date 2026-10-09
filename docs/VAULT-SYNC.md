# Sync repo → vault

> Dono: **repo** (`docs/VAULT-SYNC.md`). Espelho: este documento não é espelhado
> no vault (é documentação de processo, não conteúdo de leitura).
> Escopo: o procedimento de espelhar documentos do repo no Obsidian vault.

## Regra

O **repo** é dono. O **vault** é mirror de leitura. A direção é sempre
repo → vault; não existe sincronização inversa.

Cada documento espelhado declara isso no topo, num callout
`> [!info] Dono deste documento`. O lado do repo aponta para o espelho
(`Espelho: ~/Documents/...`); o lado do vault aponta para a fonte
(`Fonte canônica: docs/X.md **no repo**`).

## Procedimento

Não copie e cole manualmente. Use o utilitário:

```bash
# 1. verificar (read-only; exit != 0 se houver divergência)
python3 scripts/sync_vault_docs.py --check

# 2. ver o que mudaria, sem escrever
python3 scripts/sync_vault_docs.py --check --dry-run

# 3. sincronizar tudo
python3 scripts/sync_vault_docs.py --sync-all

# 4. ou um documento só (por path do repo, nome do repo ou nome do espelho)
python3 scripts/sync_vault_docs.py --sync GLOSSARIO
python3 scripts/sync_vault_docs.py --sync docs/ROADMAP.md
python3 scripts/sync_vault_docs.py --sync PLANO-NOVAS-IMPLEMENTACOES.md
```

`--check` é read-only por definição e domina qualquer `--sync` na mesma linha:
com `--check` nada é escrito, mesmo que `--sync-all` esteja presente.

## Mapeamento

Os pares repo ↔ vault são **explícitos** em `MIRRORS`, no topo de
`scripts/sync_vault_docs.py`. Nada é inferido pelo nome do arquivo — dois pares
propositalmente discordam do basename:

| repo | espelho no vault |
|---|---|
| `docs/ROADMAP.md` | `PLANO-NOVAS-IMPLEMENTACOES.md` |
| `docs/ARQUITETURA.md` | `hermes_coach_arquitetura_e_implementa_o.md` |

`CHANGELOG.md` fica na raiz do repo e espelha em `CHANGELOG.md`.

Para adicionar um documento ao sync: acrescente uma entrada em `MIRRORS`. O
script não adivinha pares, e um documento do repo com bloco de ownership mas sem
par no mapping aparece no relatório de `--check` como *não sincronizado* — é um
achado, não um erro silencioso.

## O que o utilitário garante

Estas propriedades existem porque o sync manual da sessão do HR-3 (PROMPT 27–29)
falhou duas vezes: quatro espelhos receberam `corpo_antigo + corpo_novo`, e os
blocos de ownership originais foram sobrescritos.

- **O corpo é substituído, nunca concatenado.** O corpo anterior do espelho não
  entra na conta em nenhuma hipótese. O espelho final é
  `prefixo_do_repo + ownership + corpo_do_repo` — exatamente uma cópia.
- **Ordem preservada.** O bloco de ownership não precisa vir logo após o título
  (`docs/PORTAL-UI-DESIGN.md` tem um callout `> Status:` entre os dois), então o
  prefixo é copiado verbatim e o documento não é reordenado.
- **Ownership preservado.** Se o espelho já tem um bloco de ownership válido, ele
  é mantido byte-a-byte. O template determinístico só é usado quando o bloco
  está ausente. Isso evita degradar wording específico de cada documento
  ("não um segundo glossário", "não um segundo deck") — o `mirror_note` de cada
  par fica no mapping e é aplicado só na geração.
- **Validação antes de escrever.** O conteúdo final é montado em memória e
  verificado (corpo canônico duplicado, mais de um bloco de ownership). Se a
  validação falhar, **não escreve**.
- **Escrita atômica com backup.** `tempfile` no mesmo diretório → `fsync` →
  `os.replace`. O conteúdo anterior é copiado para
  `<vault>/.sync_vault_backups/<nome>.bak` antes da troca, para restaurar na
  mesma execução. Não depende de Git: o vault não é repositório.
- **Idempotência.** Sync duas vezes produz bytes idênticos; a segunda execução
  reporta `in_sync` e não escreve.
- **Repo read-only.** O único alvo de escrita é o espelho no vault. O tool não
  tem opção vault → repo.
- **Falha fechada.** Documento sem bloco de ownership, ou espelho cujo resultado
  não valida, é erro com exit != 0. Nada é adivinhado.

## Relatório

Cada documento sai com um marcador:

```
  [=] docs/GLOSSARIO.md  -> GLOSSARIO.md   in_sync
  [~] docs/ROADMAP.md    -> PLANO-...md    would_update
  [+] docs/TEMAS.md      -> TEMAS.md       updated
  [!] docs/X.md          -> X.md           error
```

`in_sync` é idêntico ao repo; `would_update` diverge (só em `--check`/`--dry-run`);
`updated` foi escrito; `error` falhou e nada foi escrito para esse documento.

## Testes

```bash
python3 -m unittest tests.test_vault_sync
```

Os testes usam `tempfile.TemporaryDirectory()` para repo e vault falsos. Nenhum
teste escreve em `~/Documents/Obsidian Vault/`. A cobertura inclui a regressão
do bug real (espelho com corpo antigo + repo com corpo novo), a contagem de
blocos de ownership, idempotência, round-trip lógico, escrita atômica com
simulação de falha no `os.replace`, e a CLI (`--check`, `--dry-run`,
`--sync`, `--sync-all`, nome desconhecido).

## Limitação conhecida

Quatro espelhos tiveram o bloco de ownership reescrito durante o sync manual do
HR-3 e perderam a cauda específica de wording (o "não um segundo glossário
independente" e equivalentes):

```
GLOSSARIO.md
PLANO-NOVAS-IMPLEMENTACOES.md
ROTEIRO-TREINADOR.md
EMBASAMENTO-CIENTIFICO.md
```

O texto original **não está disponível** — o vault não é repositório Git e não
há backup. Os quatro mantêm hoje a variante neutra
(`**Este arquivo é espelho para leitura**.`), que é coerente com a convenção,
e os corpos estão íntegros e idênticos ao repo. O `mirror_note` desses quatro
entradas no mapping fica vazio de propósito: não se inventa histórico perdido.

A partir de agora o wording de qualquer espelho só muda por decisão explícita
neste arquivo, nunca por efeito colateral de um sync.
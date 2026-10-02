# SPEC — Issue #58, Passo A: prontidão no caminho do plano

Status: **implementado** (código + testes), revisão 3. A §15 (a leitura de
hoje não alcançava nenhuma sessão no uso diário) está **resolvida**: o fluxo
diário invoca a avaliação e há teste que prova.

Escopo: ligar a avaliação de prontidão ao uso diário real. **Não** implementa o
motor de decisão do Passo B, nem a unificação dos módulos isolados.

---

## 1. O que estava quebrado (estado anterior, verificado)

1. **Não existia produtor.** `ReadinessAssessment` (`src/readiness_assessment.py`)
   é um modelo de 7 eixos sem nenhuma função que construísse um a partir de
   dados. O único construtor era o chamador.
2. **O gate era inalcançável.** `_readiness_unfavorable()` lia
   `has_data` / `illness` / `signals`, atributos do `Readiness` legado. Para um
   `ReadinessAssessment` os três não existem, então a função retornava `False`
   **para qualquer avaliação, sempre**. O caminho era inerte.
3. **O CLI nunca passava readiness.** `build_plan()` aceita `readiness=`, e
   `cmd_build()` não fornecia nada. O `build` não consultava wellness.
4. **A consequence era desproporcional.** Qualquer sinal isolado — inclusive
   uma noite ruim de sono — trocava a sessão por Z2 900 s, porque a função
   tratava "sinal ligado" e "possível doença" como a mesma coisa.
5. **Sem `--dry-run` no `build`.** Só o `push` tinha. Não havia como inspecionar
   uma adaptação sem gravar `plan.json`.

## 2. O que existe agora

| Peça | Onde | Papel |
|---|---|---|
| `assess_readiness_assessment(records, days)` | `src/readiness.py` | wellness bruto → `(avaliacao \| None, trace)` |
| `readiness_decision(...)` | `src/readiness.py` | classe ordinal → `NONE \| REDUCE \| REPLACE` |
| `_reduce_one_step(params, piso, ...)` | `src/plan.py` | um degrau da escada de volume-antes-intensidade |
| `_adapt_session(params, state)` | `src/plan.py` | funde TSB e prontidão, um mais restritivo vence |
| `cmd_build()` + `_print_readiness_decision()` | `src/training_plan.py` | uma leitura de wellness, imprime o motivo, respeita `--dry-run` |

`plan.json` **não** ganhou campos. O motivo da decisão é saída de CLI, para não
mexer no formato persistido.

## 3. O que se mede — e o que não se mede

O Intervals expõe quatro métricas em `/wellness`: `restingHR`, `hrv`/`hrvSDNN`,
`sleepSecs` e o `readiness` do próprio Intervals. Só elas são usadas.

| Eixo | Fonte | Status |
|---|---|---|
| `hrv_score` | `hrv` / `hrvSDNN` | real |
| `rhr_score` | `restingHR` | real |
| `sleep_score` | `sleepSecs` | real |
| `recent_load_score` | — | `None`. A carga recente não existe no momento da decisão: a série de treino ainda não foi resolvida quando o dia é montado. |
| `subjective_fatigue_score` | — | `None`. RPE é digitado no treino realizado; não chega em `/wellness`. |
| `performance_score` | — | `None`. Sem fonte. |
| `consistency_score` | — | `None`. Só teria fonte derivada. |

**Cobertura máxima real: 3/7 ≈ 43%.** `ReadinessAssessment.confidence` é
reportado como **cobertura** (fração de eixos observados), não confiança
estatística. Não existe piso de cobertura: descartar uma avaliação por
cobertura baixa jogaria fora sinais ruins que foram de fato observados.

### 3.1 Ausência de dado não é neutra

Eixo sem observação fica `None`. **Não** `0.5`.

Preencher ausente com neutro rebaixaria a média de todo mundo: um atleta
saudável com 3 eixos a `0.8` e 4 ausentes cairia para média `0.34` e leria
RED. `0.5` não é "sem informação" — é uma observação ruim. A ausência precisa
ficar ausente, e a política precisa saber distingui-la.

### 3.2 O readiness do Intervals não é um sétimo eixo

O campo `readiness` do Intervals é um **composto** derivado de HRV, sono e RHR —
as mesmas entradas que já viraram eixo. Mapeá-lo para um eixo contaria o mesmo
dado duas vezes e inflaria a cobertura sem acrescentar observação.

Ele fica fora de `ReadinessAssessment` e entra como sinal separado
(`composite_low`), preservando o limiar legado `READINESS_LOW = 60` e a
semântica de `readiness_low` que já existia.

## 4. A escala dos escores — por que 0.8 / 0.2

`saudável → 0.8`, `sinal ligado → 0.2`.

**Isto é heurística do sistema, não escala calibrada.** Não há literatura que
fixe esses dois valores para prontidão. A justificativa é operacional, não
científica: o limiar *poor* do modelo (`< 0.4`) fica exatamente no meio do
intervalo entre eles, então qualquer outro par é pelo menos tão arbitrário, e
com esse par um sinal ruim isolado **não** vira RED (ver §5).

Os três limiares do modelo (`< 0.4` poor, média `< 0.5`, média `< 0.7`) mantêm
o significado que tinham antes desta ponte. `ReadinessAssessment.level()` e
`adjustments()` **não** foram modificados.

## 5. Política de decisão

Precedência, da mais restritiva para a menos. Nenhuma regra desfaz a anterior.

| # | Condição | Ação |
|---|---|---|
| 1 | `illness_alert` | `REPLACE` |
| 2 | `level() == RED` | `REPLACE` |
| 3 | `level() == YELLOW` | `REDUCE` |
| 4 | `composite_low` (isolado) | `REDUCE` |
| 5 | nenhuma | `NONE` |
| — | sem observação e sem alerta | `NONE`, motivo "dados indisponíveis" |

### 5.1 O alerta separado

`_illness()` legado é reutilizado sem alteração: RHR subindo em 2+ noites
seguidas **E** HRV caindo. É uma conjunção observada, não uma média, então
vence inclusive com `level()` GREEN e cobertura baixa.

O `level()` original **permanece no `ReadinessDecision`** para auditoria, mesmo
quando o alerta o ultrapassa: o registro mostra o que a média dizia e o que a
conjunção dizia, sem que a segunda apague a primeira.

O alerta **não** rebaixa `rhr_score`/`hrv_score` para `0.2`. Rebaixar os dois
contaria o mesmo dado duas vezes e criaria um RED que o detector de doença nunca
pediu — a decisão é um campo próprio.

**Nomeação:** sempre "alerta de possível doença/recuperação comprometida".
Nunca diagnóstico. Ausência de RHR ou HRV não permite inferir a conjunção.

### 5.2 Sinal ruim isolado não cria RED

Com um único eixo a `0.2` e dois a `0.8`: média `0.60` → YELLOW → `REDUCE`.
Uma noite ruim de sono reduz volume; não troca a sessão. O caso RED exige
três eixos abaixo de `0.4` **E** média abaixo de `0.5` — a conjunção de `level()`
continua exigindo as duas coisas.

### 5.3 `REPLACE` não é política clínica

`REPLACE` mantém a prescrição legada: Z2, 1×900 s, 70% FTP. É um recurso
conservador **de convenção**, herdado do motor, e não uma resposta validada
para possível doença. Treino leve não é garantia de adequação para ninguém, e o
CLI diz isso explicitamente quando o alerta dispara. Este passo **não** valida
essa prescrição; apenas a mantém e a nomeia corretamente.

## 6. REDUCE — o que muda

`REDUCE` aplica **um degrau** da mesma escada de `_fit_budget`, extraída em
`_reduce_one_step` para que os dois caminhos não possam divergir:

1. `repeats -= 1`
2. `on_sec *= 0.8` (mínimo 120 s)
3. `off_sec *= 0.8` (mínimo 0)
4. `on_power -= 0.05` — só até o piso de `ZONE_BANDS` da zona

Garantias: preserva `focus`, tipo e ordem dos segmentos; nunca aumenta
intensidade nem duração; nunca baixa `on_power` abaixo do piso da zona.

**"Um degrau" é escolha de projeto, não constante científica.** Não há lastro
para uma magnitude específica de redução por prontidão. O número é o mesmo do
ajuste por orçamento justamente para não inventar um segundo conjunto de
percentuais; a limitação está registrada aqui em vez de mascarada como
precisão.

Como REDUCE encurta o dia, o TSB da janela rolante libera orçamento e os dias
seguintes podem ficar com TSS **maior** que sem readiness. Isso é o motor de
orçamento respondendo à redução, não uma segunda redução.


## 7. Precedência com TSB

TSB abaixo de `-15` continua trocando qualidade por Z2 (regra histórica,
inalterada). Com os dois presentes, a mais restritiva vence:

- `REPLACE` (TSB ou prontidão) > `REDUCE` > `NONE`

A escala é única e ordenada, e `REDUCE` nunca é aplicado sobre um `REPLACE`.
`NONE` por prontidão não impede a adaptação por TSB: as duas fontes são
avaliadas antes de escolher a ação.

O escopo por dia (§8) vale **apenas para prontidão**. TSB continua valendo
para a primeira sessão de qualidade do plano, como sempre — é a regra
histórica, não uma leitura de um dia.

---

# Revisão 2 — lacunas estruturais fechadas

A revisão 1 deixou três defeitos estruturais. Nenhum foi visível na matriz de
decisão, porque todos apareciam **no plano**, não no veredito.

## 8. Não compensar automaticamente a carga reduzida

### O defeito

`_fit_budget` decide olhando `recent`, o registro de TSS **já planejado**. Reduzir
uma sessão diminuía sua entrada e, portanto, **devolvia teto** para os dias
seguintes. O sintoma medido:

| dia | referência | com readiness (antes) |
|---|---|---|
| 14/09 | `3x480@0.88` = 37 | `2x480@0.88` = 27 |
| 18/09 | `4x139@1.14` = 32 | **`5x139@1.14` = 39** |

O atleta que leu "prontidão ruim" recebia **mais** carga na sexta. Isso é
justamente o inverso do pretendido, e é a inferência que a evidência não
sustenta: um sinal de recuperação de **um dia** não informa sobre a capacidade
de absorver carga em outros dias.

Preservar `focus` e `on_power` — como fazia o primeiro teste — não prova nada
sobre isso: `repeats`, `on_sec` e TSS podem subir com o `focus` intacto. Foi
exatamente o que aconteceu.

### A correção

Quando uma intervenção de prontidão age sobre um dia, o livro-razão do orçamento
recebe o TSS **pré-intervenção** (`tss_pre`), não o TSS reduzido:

```python
recent.append((day, tss_pre if readiness_agiu else tss))
```

Efeito: a pressão de orçamento fica **idêntica** à de um plano sem readiness. O
teto é um guarda-chuva, não uma meta — ficar abaixo dele é correto, e cada dia
sai com carga **menor ou igual** à referência.

As regras de `_fit_budget` não foram tocadas: ordem da escada, piso de zona,
absorção de treino perdido e `weekly_budget` seguem iguais. A mudança é
exclusivamente o valor que entra no razão para a intervenção de prontidão.

**Progressão continua possível, mas não é automática.** Uma avaliação posterior
pode legitimamente aumentar carga — é decisão de produto, rastreável e
separada. Nada aqui a impede; apenas deixa de ser efeito colateral de uma
redução.

### O razão é por fonte, não por presença de readiness

A primeira redação marcava `readiness_agiu` pela **presença** de
`state.readiness`. Isso está errado por construção: uma decisão `NONE` não
adapta nada, mas o ledger usava `tss_pre` assim que *qualquer* readiness
existia. Medido com TSB -30 e decisão NONE: carga total **173 → 166**, sem
que a prontidão tivesse feito nada.

`_readiness_dirige()` (§`src/plan.py`) exige quatro condições: ser
`ReadinessDecision`, ter ação **adaptativa**, a leitura valer para o dia, **e**
o TSB não ter forçado REPLACE.

A quarta condição fechou um segundo defeito. Com TSB abaixo do limite a ação já
é REPLACE **por TSB**; uma REDUCE não dirigiu a mudança e mesmo assim inflava o
razão com o `tss_pre` do treino que o TSB tinha substituído por Z2. O plano
divergia em 18/09 (39 → 32 TSS) e o relatório dizia `aplicada` indevidamente.

| cenário | plano vs. referência |
|---|---|
| TSB 0 + REDUCE | dia da leitura reduzido; **nenhum dia maior** |
| TSB 0 + NONE | **idêntico** |
| TSB -30 + REDUCE | **idêntico** (`outra_adaptacao_ocorreu_antes`) |
| TSB -30 + NONE | **idêntico** |

### Prova

`tests/test_readiness_step_a.py::NaoCompensacaoTest` compara o plano adaptado
com um de referência de **mesmas entradas, exceto a intervenção**, e exige, para
**todos** os dias: TSS ≤, `planned_duration` ≤, `on_power` ≤ e
`repeats × on_sec` ≤. Também cobre TSB negativo.

> Nota sobre `on_sec`: reduzir `repeats` não exige encurtar cada repetição, e a
> ordem do motor é *adaptação → teto diário → orçamento*. `on_sec` pode diferir
> sem que isso seja compensação; o invariante é o produto `repeats × on_sec`.

## 9. Horizonte temporal: o sinal vale para o dia que descreve

### O defeito

O sinal era aplicado à **primeira sessão de qualidade do plano**, onde quer que
ela estivesse. Medido, com uma leitura de **01/10**:

| build | sessão de 05/10 |
|---|---|
| 01/10 | `3x480` (reduzida) |
| 02/10 | `3x360` (reduzida de novo) |
| 03/10 | **`1x720`** (reduzida pela terceira vez) |

Uma única leitura degradou a mesma sessão ao longo de três builds. Era o
defeito 3 (cumulatividade) e o defeito 2 (horizonte) ao mesmo tempo, e ambos
tinham a mesma causa.

### A correção: ancoragem por dia, não prazo

`ReadinessDecision` ganhou `applies_to_day` — **o dia do último registro de
wellness**, isto é, o dia que a leitura *descreve*. `_readiness_applies_on()`
só admite a intervenção quando o dia do plano é esse dia.

Isto substitui um prazo de validade arbitrário por uma âncora factual: uma
leitura descreve o dia em que foi medida, e nada além disso.

| situação | resultado |
|---|---|
| leitura de hoje, sessão de qualidade hoje | aplica |
| leitura de ontem, sessão de hoje | **não aplica** — não transfere para amanhã |
| leitura de 9 dias atrás | **não aplica** — o dia descrito já passou |
| leitura de hoje, dia é só Z2 | **não aplica** — não há sessão elegível |

"Não transfira silenciosamente" é metade do requisito; a outra metade é **não
ser silencioso**. `build_plan` preenche `readiness_report` com `situacao`
(`SITUACOES_READINESS`) e o CLI imprime o motivo. Um sinal ruim que não toca em
nada agora é distinguível de "prontidão boa".

`ReadinessDecision.applies_to_day = None` mantém o comportamento legado (aplica
onde for) e existe só para decisões montadas à mão em teste; o produtor sempre
preenche.

### Sem remover a flag one-shot

A flag `adapted` continua. Ela não é mais o mecanismo do horizonte — a âncora
é — mas segue sendo a garantia de **no máximo uma adaptação por build**, e
mantém o comportamento de TSB intacto. Removê-la foi explicitamente descartado:
aumentaria o efeito de um sinal sem decisão de produto.

## 10. Ausência de redução cumulativa

### O defeito

Causa raiz comum com §9. Detalhado porque a pergunta merece resposta direta:
**o motor reconstrói a proposta a partir do template, não do resultado
anterior.** `_block_for()` lê `BLOCK_VARIANTS[focus][slot % 3]` a cada build, e
`recent`/`existing` só entram como teto e como "preservar o treino de hoje".
Logo, reduzir duas vezes exigiria reduzir `3x480 → 2x480 → 1x480`; o que
acontecia era aescalão de redução ser reaplicada ao resultado do build
**anterior** pela âncora ausente.

### A prova

`SemReducaoCumulativaTest`:

- `test_replanejar_com_a_mesma_leitura_da_o_mesmo_plano` — três builds
  consecutivos com a mesma leitura produzem planos byte-idênticos
  (`day`, `focus`, `params`, `tss`).
- `test_sessao_ja_reduzida_nao_e_reduzida_de_novo` — `repeats` estável.
- `test_referencia_sem_prontidao_e_o_plano_nao_adaptado` — sem a intervenção, a
  mesma entrada produz a prescrição cheia. É o que valida a comparação de §8.

## 11. Contrato ordinal — e uma atribuição incorreta

O contrato de `ReadinessAssessment.level()` permanece intocado, e os 19 testes
de `tests/scientific/test_readiness.py` seguem sem modificação:

| regra | estado |
|---|---|
| sinal isolado → YELLOW → `REDUCE` | preservado |
| RED exige `poor >= 3` **E** média `< 0.5` | preservado (conjunção) |
| alerta separado, com precedência na decisão efetiva | preservado |
| dado ausente não adapta e não vira escore artificial | preservado |

### Correção de atribuição

O prompt que originou a revisão 1 afirmava que *"um sinal ruim isolado deveria
poder gerar RED"* e citava isso como requisito. **Essa afirmação está errada e
não foi implementada.** Registrar o motivo, porque ela é plausível o bastante
para ser reimplementada por engano:

Com a escala em vigor (`saudável 0.8`, `sinal ligado 0.2`), três eixos ligados
somam média `0.20`, o que satisfaz a conjunção de RED — mas nesse ponto os três
eixos **estão de fato ruins**, e RED é a resposta correta. Um sinal *isolado*
dá média `(0.2 + 0.8 + 0.8) / 3 = 0.60`: acima de `0.5`, então **YELLOW**, e
`poor = 1 < 3`. RED com um sinal isolado é **inalcançável** por construção, e
torná-lo alcançável exigiria fabrication de escore ou afrouxar a conjunção.

O que a revisão 1 fez — REDUCE para sinal isolado — é o comportamento correto.
Nenhum caminho produz RED a partir de um sinal isolado, e não existe código que
tente.

## 12. Alcance de `all --dry-run`

A correção que impede reconciliação contra o `plan.json` antigo foi mantida:
`all --dry-run` executa **apenas o `build`** e encerra.

A saída diz exatamente o que foi e o que não foi simulado:

```
dry-run: encerrando apos build. Apenas o planejamento foi simulado; a
reconciliacao nao foi executada nem simulada, e nada foi publicado ou gravado.
```

`test_all_dry_run_nao_chama_reconcile_nem_push` substitui `cmd_reconcile` e
`cmd_push` por stubs que **levantam** se forem alcançados, e verifica aabsence
de `plan.json`. Ausência de persistência, de publicação **e** de reconciliação
são as três afirmadas por teste, não só as duas últimas.

`build --dry-run` (sem `reconcile`) mostra o plano adaptado e não grava —
comportamento inalterado na revisão 2.

---

## 13. Cobertura de teste

`tests/test_readiness_step_a.py`, 54 casos. `tests/test_readiness_today.py`,
21 casos (§15), pelo dispatcher real.

**Produtor** — 3 eixos preenchidos / 4 em `None`; ausência não vira `0.5`; sem
wellness → `None`; registro único; leituras ausentes no registro; data ilegível;
datas desatualizadas; sinal ruim observado; composto fora dos eixos;
`reference_day` é o dia do último registro.

**Política** — a matriz de §5; alerta vence GREEN; alerta não anulado por
cobertura baixa; composto isolado → `REDUCE`; sinal isolado não cria RED; sem
dado → `NONE` com motivo; `is_adaptive`.

**Plano** — REDUCE preserva `focus` e `on_power`; corta volume; respeita o
piso de zona; RED troca a primeira sessão de qualidade; reduz só a primeira;
TSB continua mandando; mais restritiva vence sem dupla redução; ausência não
adapta; Z2 planejado permanece Z2.

**Não compensação** (§8) — nenhum dia com TSS, duração, `on_power` ou trabalho
maior que a referência; redução no dia da leitura; TSB negativo sem
compensação.

**Ledger por fonte** (§8) — decisão NONE não altera o plano com TSB ativo;
decisão NONE não altera o plano sem TSB; TSB vencedor usa o razão de TSB e não
reporta a prontidão como aplicada; REDUCE da prontidão não promove nenhum dia.

**Horizonte** (§9) — leitura de ontem não adapta hoje; leitura de 9 dias não
adapta nada; dia sem sessão de qualidade não transfere; dia fora da janela não
alcançado; avaliações ruins em dias consecutivos adaptam dias distintos; TSB
continua sem âncora.

**Cumulatividade** (§10) — três builds idênticos; sessão já reduzida não é
reduzida de novo; referência sem prontidão é a prescrição cheia.

**CLI** — plano adaptado; alerta como alerta e não diagnóstico; wellness
ausente não quebra o build; wellness lido **uma única vez**; `--dry-run` não
grava; build normal grava; `all --dry-run` encerra; `all --dry-run` não chama
`reconcile`/`push`; saída avisa quando a leitura não foi aplicada.

## 14. Lacunas: classificação

### Resolvida, com evidência

| lacuna | evidência |
|---|---|
| Reduzir hoje aumentava amanhã | `NaoCompensacaoTest` (4 testes) |
| Decisão NONE alterava o plano via TSB | `LedgerEhPorFonteTest` |
| TSB vencedor inflava o razão da prontidão | `LedgerEhPorFonteTest` |
| Sinal transferido para sessão futura | `HorizonteTemporalTest` (6 testes) |
| Redução cumulativa entre builds | `SemReducaoCumulativaTest` (3 testes) |
| Não-aplicação silenciosa | `situacao` + `SITUACOES_READINESS`, teste de CLI |
| `all --dry-run` sem escopo declarado | `test_all_dry_run_nao_chama_reconcile_nem_push` |
| Atribuição incorreta sobre RED | §11, registro explícito |

### Bloqueadora da ativação

**Resolvida em §15.** A janela do plano não alcançava o dia da leitura; a
avaliação passou a rodar no fluxo diário (`check` antes de `reconcile`/`push`).
Limitações residuais da resolução estão em §15.

### Limitação aceita explicitamente

- **Escala `0.8`/`0.2` e "um degrau"** são heurística do sistema, sem
  calibração e sem lastro em literatura. Nenhum teste deste arquivo valida
  fisiologia; os testes verificam consistência de contrato e ausência de
  compensação. `REPLACE` (Z2 900 s) é recurso conservador **de convenção**, não
  resposta validada para possível doença.
- **Cobertura 3/7.** Quatro eixos sem fonte em `/wellness`. O resultado é
  honesto (`ausência de dado não vira escore`), mas deixa a avaliação dependente
  de três sinais apenas.
- **Deterioração moderada não verificada com dados reais.** Um sinal que não
  cruza o limiar legado não gera escore ruim. A detecção de doença
  (`_illness`) exige ≥ 3 noites e é heurística de convenção.

### Evolução posterior

- Ampliar cobertura com fonte nova no Intervals (carga recente, RPE).
- **Progressão após redução**, como decisão rastreável e separada — hoje
  liberada pelo orçamento, mas nunca automática (§8).
- Ampliar a prescrição de `REPLACE` com base em evidência, não em convenção.

---

## 15. A leitura de hoje: resolvido

**Resolvido.** O fluxo diário real invoca a avaliação, e há teste que prova.

### O que era

As duas únicas chamadas de produção de `build_plan` (`cmd_build` e a recursão
interna) entram com `start=None`. Sem `existing`, o plano começa **amanhã**; com
`existing` e hoje no plano, a sessão de hoje é **preservada verbatim** e nunca
passa por `_adapt_session`. Como a leitura descreve **hoje**, `aplicada_em` era
sempre vazio no uso diário. A regra estava certa e **inerte**.

### Decisão: `check` no fluxo diário, não um `build` diferente

Três opções foram pesadas.

**A. `check` antes de `reconcile`/`push` no script do timer** — escolhido.
`scripts/daily_reconcile.sh` é o que o systemd `cycling-coach-daily.timer`
dispara, e o passo `push --start $(date +%F)` **publica a sessão de hoje**. A
janela em que a leitura de hoje ainda pode mudar o plano é exatamente essa, e
já estava no fluxo.

**B. `build` passar a incluir hoje** — rejeitada. O default `start=None`
(amanhã) é contrato (`tests/test_plan.py:64`); mudar globalmente regraria toda
a semana e forçaria a reconstrução da sessão de hoje, que hoje é preservada.

**C. Um novo comando `check-today`** — rejeitada. Duplicaria o motor e o
`check` já é, por nome e por `--apply`, "prontidão do dia".

`cmd_all` (`build` + `reconcile` + `push`) **não** ganhou `check`: ali a
avaliação e a publicação estariam no mesmo comando, sem confirmação no meio.
Um teste trava essa separação.

### O `check` foi migrado para o motor do Passo A

Ele existia desde a #31, mas usava o motor legado (`assess_readiness` /
`suggest_swap` / `recovery_workout`), que trocava a sessão por Z2 900 s diante
de **qualquer** sinal ligado e **não checava se o treino já tinha acontecido**.
Isso era um segundo motor com política diferente do `build` — o oposto do que
esta SPEC exige.

Agora `check` chama `build_plan` com `start=hoje` e compara três versões do
mesmo dia: `sem` (sem readiness), `com` (com a decisão) e `atual` (o que está
no `plan.json`). Disso decorrem, sem código extra:

- **motor único** — `check` e `build` não podem divergir, por construção
  (`test_check_e_build_conferem_a_mesma_sessao`);
- **sem cumulatividade** — `build_plan` sempre reconstrói do template, então
  reexecutar dá 38 → 32 → **32**, não 38 → 32 → 22;
- **diferença atribuível** — se `atual` divergir de `sem`, a diferença não é da
  leitura de hoje: o `check` **propõe e não aplica**.

### Política de elegibilidade

`readiness_eligibility()` (`src/plan.py`), na ordem em que cada filtro barra:

| situação | resultado |
|---|---|
| sem treino hoje | nada a adaptar; **não desloca para amanhã** |
| foco não qualitativo | fora (REDUCE/REPLACE só existe para qualidade) |
| sem `external_id` | sem identidade; não dá para confirmar o estado |
| **concluída** | **preservada**, sempre |
| horário planejado já passou, sem realização confirmada | **DESCONHECIDO: propõe, não aplica** |
| caso contrário | não iniciada; elegível |

**"Iniciada" não é um estado suportado, e isso é explícito.** O Intervals só
confirma realização via `paired_activity_id` (o critério que `_done_and_extra`
já usava). Sem ele, não há como distinguir "começou e ainda não sincronizou"
de "não começou". Ler a ausência como "não iniciada" reescreveria uma sessão em
andamento. Então, passado o horário planejado, o estado é `DESCONHECIDO` e o
comando **não aplica nada** — registra a proposta e sai. A incerteza é
declarada na saída, não escondida.

O horário planejado é `START_TIME` (`07:30`), que é o mesmo valor que o `push`
publica via `event_payload` — não é um palpite novo.

### Data do atleta

O projeto **não tem configuração de fuso suportada** (`date.today()` em todo o
motor, zero ocorrência de `zoneinfo`/`TZ`). "Data local do atleta" é,
consequentemente, a data local da máquina, e é isso que `check` usa. Criar
suporte a fuso seria uma refatoração global de datas, fora do escopo deste
passo — está registrado como limitação, não silenciado.

### Validade temporal

Inalterada de §9: a leitura vale para o dia que **descreve** (o último
registro). `check` compara `decisao.applies_to_day` com a data de hoje antes de
qualquer coisa e recusa, dizendo por quê. Uma leitura de ontem não toca em
hoje nem em amanhã. Nenhum prazo arbitrário foi ativado.

### Proposta, aplicação, publicação

Três etapas separadas, e só a segunda escreve:

| etapa | como | escreve? |
|---|---|---|
| **proposta** | `check` (padrão) | não — imprime e diz o que rodar |
| **aplicação local** | `check --apply` | só no `plan.json` |
| **publicação externa** | `push` | só o calendário, comando separado |

`check --apply` grava apenas no `plan.json` local e diz isso na saída. O
calendário só muda pelo `push`, que já era a única etapa do script diário que
fala com o Intervals. `--dry-run` bloqueia a escrita e é verificado por teste.
A aprovação não foi ampliada para portal nem fila: o mecanismo existente
(`--apply` explícito, mais o `push` separado) é o que já estava no projeto.

O `check --apply` no script diário é **aplicação local, não publicação** — a
mesma fronteira que o `reconcile` já tinha antes desta entrega. A aprovação de
publicar continua sendo o `push`.

### Evidências

`tests/test_readiness_today.py`, **21 casos**, todos pelo **dispatcher real**
(`tp.main([...])`), com data e hora congeladas e fronteiras externas mockadas
(`get_client`, `latest_metrics`, disco temporário, `_agora`).

Os 12 cenários exigidos, e onde cada um está provado:

| cenário | teste |
|---|---|
| wellness de hoje + sessão elegível + REDUCE → proposta reduzida | `test_leitura_de_hoje_com_sessao_elegivel_propoe_reducao`, `test_apply_grava_somente_no_plan_json_local` |
| NONE → nada muda | `test_decisao_none_nao_altera_nada` |
| ausência de wellness → nada muda | `test_sem_wellness_nao_altera_nada` |
| leitura antiga → não adapta hoje nem amanhã | `test_leitura_antiga_nao_adapta_hoje_nem_amanha` |
| sessão concluída → preservada | `test_sessao_concluida_e_preservada`, `test_sessao_concluida_preservada_mesmo_apos_o_horario` |
| sessão iniciada → preservada (suportado como desconhecido) | `test_sessao_em_andamento_preservada_apos_o_horario` |
| estado desconhecido → proposta sem aplicação | idem (o mesmo caso é o desconhecido) |
| ausência de sessão hoje → não desloca para amanhã | `test_ausencia_de_sessao_hoje_nao_desloca_para_amanha` |
| TSB já REPLACE → readiness sem crédito | `test_tsb_vencedor_nao_credita_a_prontidao` |
| reexecução → sem cumulatividade | `test_reexecucao_com_as_mesmas_entradas_nao_reduz_de_novo` |
| `--dry-run` → sem persistência nem publicação | `test_dry_run_nao_persiste_nem_publica` |
| fluxo diário não publica proposta não aprovada | `test_all_nao_avalia_readiness_de_hoje`, `test_proposta_nao_aplicada_nao_chega_ao_push`, `test_fluxo_diario_real_chama_check_antes_de_reconciliar_e_publicar` |

Fronteiras de dia/horário também travadas:
`test_antes_do_horario_a_sessao_publicada_e_elegivel` (07:29) contra
`test_sessao_em_andamento_preservada_apos_o_horario` (19:00).

**Os testes foram mutados para provar que mordem.** Cinco alterações, cinco
falhas: remover `check` do script diário; ignorar a sessão concluída; tratar
estado desconhecido como aplicável; remover a guarda de idempotência; remover a
âncora por dia.

### Limitações que permanecem

1. **Sem fuso horário.** A data é a da máquina (§ acima).
2. **`ONCE` o estado "iniciada" não existe.** Acima do horário, o `check`
   propõe e não aplica; quem quiser aplicar depois de sincronizar precisa
   rodar de novo.
3. **Resolvido: o timer foi movido para 05:30.** Ele rodava a 00:00, quando o
   dispositivo quase nunca tinha sincronizado a leitura do dia — a intervenção
   estava ligada no fluxo, mas raramente tinha dado para agir. Medido no campo
   `updated` de `/wellness`, as chegadas locais foram 00:23, 00:42, 00:43, 01:19,
   03:52 e 04:05: **todas depois da meia-noite**. 05:30 fica depois desse
   agrupamento e ainda 2 h antes da sessão, que começa às 07:30
   (`START_TIME`, o valor que o `push` publica).
   `Persistent=true` cobre máquina dormindo: o catch-up roda ao acordar, e se já
   passou das 07:30 o `check` marca `estado_desconhecido` e **não aplica**.
   Unidade do usuário, com backup em
   `~/.config/systemd/user/.backup-20261002/`.
   **Ressalva honesta:** a chegada é variável (dois registros vieram às 11:28 e
   13:53, provavelmente reenvio). 05:30 maximiza a chance, não garante.
4. **Cobertura 3/7** e heurística sem calibração, de §14. Inalteradas.
5. **`build` continua sendo a autoridade do TSB.** `check` não aplica adaptação
   por TSB; quando o TSB domina, a saída diz isso explicitamente.

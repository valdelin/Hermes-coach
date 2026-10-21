# Hermes Coach — Onboarding de Colaborador

> **Objetivo deste documento:** colocar um novo colaborador em condições de entender o projeto, preparar o ambiente, trabalhar com segurança e contribuir sem quebrar os contratos arquiteturais, científicos e operacionais do Hermes Coach.
>
> **Referência oficial:** branch `master`.
>
> **Versão corrente:** consulte `VERSION`.
>
> **Release atual:** `0.0.36`.
>
> Não trate SHA fixo como verdade permanente. Confirme o checkout com
> `git rev-parse HEAD` e a referência remota com `git fetch origin`.
>
> A branch `feat/ui-foundation` foi integrada na release `0.0.36`; `master` é a
> linha oficial. Toda branch de feature deve nascer de `master`, e o CI deve
> passar antes do merge.

---

## 1. O que é o Hermes Coach

O Hermes Coach é um sistema de coaching de ciclismo que usa o **Intervals.icu** como fonte principal de dados observados e como calendário de publicação dos treinos.

O sistema combina:

- leitura de eventos, wellness, atividades e streams do Intervals.icu;
- geração determinística de plano de treino;
- readiness e adaptação diária;
- lifecycle local dos treinos;
- histórico canônico de FTP confirmado;
- evidências de FTP separadas do estado canônico;
- relatórios e resumos;
- reconciliação entre plano e atividades realizadas;
- publicação de workouts;
- uma fachada local (`scripts/hermes_agent.py`) para orquestração segura;
- integração opcional com OpenCode para desenvolvimento assistido.

**Importante:** o LLM/agente não é a fonte de verdade da prescrição. O motor determinístico do repositório é.

---

## 2. Princípios arquiteturais que não devem ser quebrados

Antes de editar código de domínio, leia e preserve estes contratos:

### View / Policy / Advice / Prescription

- **View** = estado observado/derivado.
- **Policy** = interpretação.
- **Advice** = recomendação.
- **Prescription** = alteração do treino.

Não misture essas camadas.

### Observed / Derived / Heuristic

Diferencie explicitamente:

- dados observados pelo provider;
- métricas computadas pelo Hermes;
- heurísticas do sistema;
- advice;
- prescrição.

Nunca apresente uma heurística como fisiologia universal.

### Missing data

Ausência de dado **não é zero** e não deve virar automaticamente “saudável”.

Exemplos importantes:

- HRV ausente != HRV normal;
- RHR ausente != RHR normal;
- potência ausente != 0 W;
- TSB ausente != 0.

### Planned != Observed

Treino planejado não é atividade realizada.

- `PlannedWorkout` = prescrição;
- activity/event/stream do provider = execução observada.

Nunca use a estrutura planejada como se fosse execução real.

---

## 3. FTP: regra de ouro

O projeto separa:

1. **FtpEvidence** — estimativa/observação;
2. **Advice** — sugestão;
3. **confirmação explícita do usuário**;
4. **FtpReference** — estado canônico confirmado.

Arquivos principais:

- `src/ftp_evidence.py`
- `src/ftp_history.py`
- `src/application.py`

Uma estimativa nunca deve criar automaticamente o FTP canônico.

O `.env`/`DEFAULT_FTP` ainda existe em caminhos operacionais legados, mas **não deve ser tratado como histórico fisiológico canônico**.

---

## 4. Estrutura principal do repositório

```text
Hermes-coach/
├── src/
│   ├── application.py          # Application seam / casos de uso
│   ├── plan.py                 # motor de geração do plano
│   ├── training_plan.py        # CLI principal / composition root
│   ├── provider.py             # contratos provider-independent
│   ├── intervals_adapter.py    # adapter Intervals.icu
│   ├── intervals_client.py     # client HTTP legado
│   ├── ftp_history.py          # FTP canônico
│   ├── ftp_evidence.py         # evidência/advice de FTP
│   ├── training_block.py       # BlockContext (FTP-H3)
│   ├── readiness.py            # readiness/policy atual
│   ├── recovery.py             # retorno/rampa legado
│   ├── pw_hr_decoupling.py     # Pw:HR observado
│   └── ...
├── scripts/
│   ├── hermes_agent.py         # fachada/orquestrador local
│   ├── daily_reconcile.sh
│   └── sync_vault_docs.py
├── tests/
├── docs/
├── .opencode/
├── AGENTS.md
├── opencode.json
└── .github/workflows/test.yml
```

### 4.1 Mapa do Código Python

O inventário completo dos módulos Python, o mapa de dependências (com diagramas Mermaid
por subsistema) e o guia para localizar responsabilidades estão em:

[`docs/GUIA-CODIGO-PYTHON.md`](GUIA-CODIGO-PYTHON.md)

Use esse documento para responder "onde fica X?", "o que faz Y?", "por onde começo a
alterar Z?" e para entender os contratos que não podem ser quebrados. Ele descreve uma
versão específica do projeto e precisa ser atualizado quando módulos forem criados,
removidos ou tiverem a responsabilidade alterada.

---

## 5. Documentos que devem ser lidos primeiro

Na primeira sessão, leia nesta ordem:

1. `AGENTS.md`
2. `README.md`
3. `docs/ROADMAP.md`
4. `docs/EMBASAMENTO-CIENTIFICO.md`
5. `docs/ROTEIRO-TESTES.md`
6. `docs/SPEC-progression.md`
7. `docs/VAULT-SYNC.md`
8. `docs/HOWTO-HERMES-AGENT.md`

Para FTP:

- `docs/SPEC-ftp-h3-block-context.md`
- documentação/roadmap referente a FTP-H2/H3/H5/H6

Para readiness:

- `docs/RDY-1-READINESS-VIEW.md`
- `docs/SPEC-passo-A-readiness.md`

---

## 6. Setup local

### Clonar

```bash
git clone https://github.com/valdelin/Hermes-coach.git
cd Hermes-coach
```

### Ambiente Python

O CI usa **Python 3.12**.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

A dependência externa atual principal é:

```text
requests>=2.31
```

### Configuração local

```bash
cp .env.example .env
```

Preencha localmente, nunca no Git:

```text
INTERVALS_ATHLETE_ID=...
INTERVALS_API_KEY=...
```

O `.env` contém dados sensíveis e está explicitamente protegido.

---

## 7. Segurança

Nunca:

- commite `.env`;
- cole API keys em issue, PR, log ou prompt;
- imprima segredos no terminal de CI;
- passe segredo em argv;
- faça `git add .` sem revisar;
- use `git push --force` sem autorização explícita;
- publique no calendário do Intervals sem saber exatamente o efeito.

No OpenCode, `.env` e padrões equivalentes devem resolver para **deny**.

Arquivos privados/gerados, como `relatorio-*.html`, não devem ser versionados.

---

## 8. Fluxo de desenvolvimento

Antes de editar:

```bash
git status --short
git branch --show-current
git log --oneline -10
```

Durante o trabalho:

- faça mudanças pequenas;
- mantenha escopo estreito;
- crie branches de feature a partir de `master`;
- só integre em `master` depois do CI verde;
- adicione regressão reproduzindo o bug;
- preserve compatibilidade de persistência;
- evite refactors oportunistas.

Antes de propor commit:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts
git diff --check
git diff --cached --check
git status --short
```

O CI oficial executa:

```bash
python3 -m unittest discover -s tests -v
```

O baseline da release `0.0.36`, a ser sempre reconfirmado no checkout atual, é:

```text
1531 tests
0 failures
0 errors
3 skips
```

O GitHub Actions deve passar antes de integrar qualquer mudança em `master`.

---

## 9. Política de commits

Preferir commits atômicos e reversíveis.

Exemplos recentes:

```text
325c1d9 feat(ftp): add FTP-H3 training block context boundary
dc83663 fix(security): harden agent permissions and FTP evidence handling
95cac5d refactor(plan): add shared planning config plumbing
264896a feat(plan): add configurable minimum regular duration
9d3ef1e feat(plan): add scheduled active recovery days
```

Regras:

- não misture feature + docs não relacionadas + cleanup;
- não misture PROG/Tally com FTP ou hardening;
- revise `git diff --cached` integralmente antes do commit;
- nunca reescreva a história de outra pessoa sem combinar antes.

---

## 10. Provider boundary

Código novo deve depender dos contratos em:

```text
src/provider.py
```

O Intervals.icu concreto vive atrás de:

```text
src/intervals_adapter.py
```

A Application deve depender do boundary, não do shape cru `icu_*`.

Detalhes específicos do provider não devem vazar para domínio/policy.

---

## 11. Application layer

`src/application.py` é o seam principal entre adapters/interfaces e domínio.

Objetivo:

- CLI/UI chamam casos de uso;
- casos de uso recebem dependências explicitamente;
- domínio não deve localizar `get_client()` escondido;
- writes devem ser claros;
- leitura e mutação devem permanecer separadas.

Ao adicionar um novo fluxo, pergunte:

> isso é lógica de domínio ou apenas orchestration?

Se for orchestration, provavelmente pertence à Application.

---

## 12. Readiness

Readiness atual trabalha com 7 eixos conceituais:

- HRV
- RHR
- sleep
- subjective fatigue
- recent load
- performance
- consistency

Nem todos têm fonte observada disponível hoje.

Regras importantes:

- missing != healthy;
- confiança depende da cobertura;
- sinais isolados não devem virar diagnóstico;
- readiness não é medicina;
- illness alert é alerta conservador, não diagnóstico.

O `check --apply` altera apenas `plan.json`.
Publicação continua sendo um passo separado via `push`.

---

## 13. Active Recovery

`ACTIVE_RECOVERY_DAYS`:

- é opcional;
- deve ser subconjunto de `TRAINING_DAYS`;
- representa **intenção da agenda/prescrição**;
- continua sendo Z2 leve;
- não é uma nova zona fisiológica;
- não deve ser compensado automaticamente quando perdido.

Readiness continua sendo uma adaptação por estado; os dois conceitos não devem ser fundidos.

---

## 14. Minimum Regular Duration

`MIN_REGULAR_DURATION_MINUTES`:

- é opcional;
- ausente → comportamento legado;
- é preferência de disponibilidade, não permissão para ultrapassar guardrails;
- cap diário, budget e readiness prevalecem;
- Ramp Test e sessões protegidas continuam isentos.

---

## 15. Persistência

Arquivos locais importantes:

- `plan.json`
- `ftp_history.json`
- `ftp_evidence.json`
- `training_snapshot.json`
- `activity_streams.json`

FTP history/evidence já usam escrita atômica com tempfile + `os.replace`.

**Atenção:** `plan.json` ainda é um ponto conhecido de melhoria; a escrita atual não é atômica.

Ao tocar em persistência:

- preserve backward compatibility;
- não descarte campos desconhecidos/aditivos;
- falhe fechado em estado corrompido;
- adicione round-trip tests.

---

## 16. Vault / Obsidian

Regra oficial:

```text
repo = source of truth
vault = mirror
```

Nunca edite/copie o espelho manualmente como forma de sync.

Use:

```bash
python3 scripts/sync_vault_docs.py --check
python3 scripts/sync_vault_docs.py --sync docs/ROADMAP.md
```

ou:

```bash
python3 scripts/sync_vault_docs.py --sync-all
```

Leia `docs/VAULT-SYNC.md` antes de tocar em documentos espelhados.

---

## 17. OpenCode

Arquivos principais:

- `opencode.json`
- `.opencode/agent/cycling-coach.md`
- `AGENTS.md`

O agente de desenvolvimento deve respeitar:

- escopo estreito;
- segurança;
- `.env` deny;
- testes antes de commit;
- nenhuma mutação externa sem autorização.

Não use o prompt do OpenCode como segunda fonte de fisiologia. O código/documentação canônica mandam.

---

## 18. Hermes Agent

`scripts/hermes_agent.py` é uma fachada determinística.

Ele:

- não contém LLM embutido;
- não deve decidir fisiologia;
- classifica efeitos de comandos;
- pede confirmação para mutações;
- não usa `shell=True`, `eval` ou `exec` com input do usuário;
- encaminha `raw` apenas para a CLI do projeto.

---

## 19. Estado atual da auditoria

A auditoria abaixo foi preservada como registro da integração de `feat/ui-foundation` na release `0.0.36`. Ela não declara os achados como corrigidos.

Resultado:

```text
P0: 0
P1: 2
P2: 8
P3: 2
MERGE RECOMMENDATION: MERGE_AFTER_P1_FIXES
```

Os dois P1 atuais são:

### AUD-01 — recovery/ramp legado

`src/recovery.py` ainda trata:

- `ramp_pts` fixo;
- deload a cada 4 semanas;
- fator de deload fixo;

como “prescrição segura”.

Isso conflita com a revisão científica mais recente: não existe uma progressão semanal universal nem ciclo universal 3:1/4:1.

### AUD-02 — FTP-H5

O fluxo de Ramp Test ainda prescreve automaticamente:

- D-2 recovery;
- D-1 spin;
- D0 test;
- D+1 recovery;

e apresenta isso como consenso.

A decisão final de segurança dessa área ainda depende da validação do treinador.

**Não copie essas regras para código novo como se fossem fisiologia estabelecida.**

---

## 20. Outros achados conhecidos

Também estão no backlog técnico da auditoria:

- tornar `plan.json` atomicamente persistido;
- corrigir casos de metadata que podem cair no formato lista pura;
- alinhar captura de `ProviderError` na CLI;
- preservar zero observado no adapter;
- remover narrativa conflitante de FTP no agent prompt;
- melhorar isolamento de `sys.path` nos testes;
- consolidar timezone semantics;
- tornar push externo mais resiliente a falha parcial;
- fortalecer CI;
- adicionar branch protection/status checks.

---

## 21. Progression

Existe especificação:

```text
docs/SPEC-progression.md
```

Mas a integração de progressão ainda não deve ser feita livremente.

A revisão científica concluiu que não existe:

- cutoff universal de adherence;
- número universal de treinos incompletos;
- ordem universal de progressão;
- deload universal por calendário.

Decisões Q1–Q4 pertencem ao treinador/produto antes de integração prescritiva.

Não implemente `+5%`, `+10% por semana`, `3:1`, `4:1` etc. como regras universais.

---

## 22. Tally / roteiro do treinador

O roteiro canônico é:

```text
docs/ROTEIRO-TREINADOR.md
```

O Tally é derivado.

Não trate o Tally como fonte canônica.

A trilha PROG/treinador é mantida separada das features técnicas.

---

## 23. Como revisar um PR

Ao revisar, procure primeiro por:

1. mudança de prescrição sem teste;
2. heurística apresentada como ciência;
3. missing convertido em zero;
4. planned tratado como observed;
5. provider-specific fields vazando para domínio;
6. writes externos implícitos;
7. perda de metadata/persistência;
8. defaults silenciosos;
9. datas/timezones implícitos;
10. diff maior do que o objetivo declarado.

Pergunta padrão:

> Se esse patch estiver errado, ele apenas exibe algo incorreto ou pode alterar o treino/calendário?

Se puder alterar treino/calendário, ele merece revisão mais rigorosa.

---

## 24. Checklist da primeira contribuição

Antes de abrir sua primeira mudança:

- [ ] li `AGENTS.md`;
- [ ] li o trecho relevante do `ROADMAP`;
- [ ] sei se estou mudando View, Policy, Advice ou Prescription;
- [ ] sei qual dado é observado e qual é derivado;
- [ ] rodei a suíte focada;
- [ ] rodei a suíte completa;
- [ ] rodei `compileall`;
- [ ] rodei `git diff --check`;
- [ ] revisei o diff staged;
- [ ] não incluí `.env`, relatórios privados ou Tally por acidente;
- [ ] documentei mudança científica se houver;
- [ ] não publiquei no Intervals sem confirmação.

---

## 25. Primeiro exercício recomendado

Para conhecer o sistema sem risco:

1. rode a suíte;
2. leia `src/provider.py`;
3. leia `src/application.py`;
4. siga o fluxo `cmd_check()` em `src/training_plan.py`;
5. siga o fluxo até `build_plan()` em `src/plan.py`;
6. leia `src/ftp_history.py` e `src/ftp_evidence.py`;
7. rode um `build --dry-run` com um `.env` de desenvolvimento;
8. não execute `push`.

Esse caminho mostra quase toda a arquitetura atual sem exigir mutação externa.

---

## 26. Regra final

Quando houver conflito entre:

- memória de conversa;
- prompt de agente;
- documento antigo;
- comentário;
- código/testes atuais;

**não adivinhe.**

Pare, verifique a fonte canônica e documente a divergência.

No Hermes Coach, segurança e rastreabilidade valem mais do que “fazer funcionar rápido”.
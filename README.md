# Hermes Coach — agente de treino de ciclismo indoor

[![CI](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml/badge.svg)](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml)

> **English version:** [README.en.md](README.en.md)

Agente que consulta o **Intervals.icu**, acompanha o **TSB** (forma), monta o
plano e publica o treino no calendario do Intervals.icu (os arquivos
`.zwo` sao baixados direto no app).

## Custo de modelos: R$ 0

- **Autoria aqui:** opencode CLI, tier gratuito (`big-pickle` no CLI).
- **Orquestracao (Hermes):** turnos curtos; o trabalho pesado e delegado ao
  CLI do opencode via o skill `hermes/skills/cycling-coach/` (veja abaixo).
- **Execucao do treino:** `training_plan.py` e deterministico — roda sem LLM.

## Estrutura

```
hermes-coach/
├── .opencode/agent/cycling-coach.md   # agente opencode (treinador)
├── hermes/skills/cycling-coach/       # skill de delegacao do Hermes
├── src/
│   ├── intervals_client.py            # cliente da API do Intervals.icu
│   ├── coach.py                       # prescrição e TSS estimado do plano
│   ├── impulse_response.py            # motor Banister (CTL/ATL/TSB) + Expected PMC com zonas Friel
│   ├── plan.py                        # plano semanal (build/reconcile/adherence/taper de prova)
│   ├── plan_run.py                    # protótipo de corrida (#18): %LTHR/RPE/pace, sem power meter
│   ├── recovery.py                    # retorno a forma: PMC real + estimativa de prazo + rampa segura
│   ├── activity_summary.py            # resumo dos treinos feitos por dia/semana/mês
│   ├── brand.py                       # identidade: 22 temas + tokens de cor (#21)
│   ├── charts.py                      # gráficos em texto: PMC + carga semanal (#21)
│   ├── report.py                      # export HTML (SVG) / PDF via chromium (#21)
│   ├── ftp_estimation.py              # estimativa de FTP de pedais não agendados (#6)
│   ├── training_phase.py              # fases do plano (base/build/specific/peak/recovery/test)
│   ├── progression.py                 # progressão de estímulos por família de treino
│   ├── intensity_distribution.py      # distribuição de intensidade por minutos efetivos
│   ├── athlete_profile.py             # perfil fisiológico (FTP/CP/W′/VO₂max/FC, todos opcionais)
│   ├── adaptation.py                  # estado de adaptação heurístico (6 domínios)
│   ├── training_decision.py           # decisão adaptativa com rationale e confidence
│   ├── readiness_assessment.py        # prontidão multimodal (adequação ao treino, não diagnóstico)
│   ├── critical_power.py              # Critical Power / W′ como complemento ao FTP
│   ├── vo2_generator.py               # gerador VO2max estruturado (progressão por dimensão)
│   ├── zone_intent.py                 # intenção e dose por família (a potência não decide a zona)
│   └── training_plan.py               # CLI (info/model/build/adherence/recovery/summary/reconcile/push)
├── tests/                             # 712 testes (stdlib unittest)
└── docs/                              # ROADMAP, GLOSSARIO, PITCH-DECK, ARQUITETURA, TEMAS, ...
```

## Documentação

- [docs/ROADMAP.md](docs/ROADMAP.md) — roadmap consolidado: backlog por fase
  (issues #1–#18) + benchmarks de mercado/ciência (Tredict, Joe Friel,
  Science to Sport) que justificam decisões.
- [docs/GLOSSARIO.md](docs/GLOSSARIO.md) — acrônimos e decisões (CTL/ATL/TSB,
  rFTP/LTHR, W′/CP como contexto, etc.).
- [docs/PITCH-DECK.md](docs/PITCH-DECK.md) — deck do produto (diferenciais vs
  Tredict, motor e testes).
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — conceito original do agente
  (motor Impulse-Response/Banister, schema de estado do atleta, system prompt)
  e diferenças para a implementação atual. **Não implementado** — referência de
  design e direção futura multi-esporte (corrida). Sincronizado com o vault do
  Obsidian.
- [CHANGELOG.md](CHANGELOG.md) — histórico de versões (SemVer, tags).
- Roteiro de validação com treinador (ciência do treino + produto
  multi-atleta/modo solo): `ROTEIRO-TREINADOR.md` no vault do Obsidian — inclui
  seção "perguntas que o treinador fará e as respostas que já temos".
- [docs/SYNC-PLATAFORMAS.md](docs/SYNC-PLATAFORMAS.md) — como conectar cada
  plataforma (Garmin, Zwift, Wahoo, Strava, Polar, COROS, Suunto, Oura/WHOOP
  etc.) ao Intervals.icu (atividades, wellness e treinos planejados).
- [docs/ROTEIRO-TESTES.md](docs/ROTEIRO-TESTES.md) — roteiro de testes
  manual/semi-automático (CLI, agente, calendário, reconciliação, onboarding,
  disponibilidade, FTP) com checklist, caça a bugs e template de reporte.

## Setup

1. Copie as credenciais:
   ```
   cp .env.example .env
   # preencha INTERVALS_ATHLETE_ID, INTERVALS_API_KEY, FTP
   # opcional: CUE_LANG=pt (padrao) ou en — idioma das mensagens dos treinos
   ```
   (A API do Intervals.icu usa HTTP Basic Auth: username fixo `API_KEY`,
   senha = a sua API key.)

2. Defina sua agenda de treinos no `.env` (opcional):
   ```
   TRAINING_DAYS=seg,ter,qua,qui,sex
   ```
   Aceita nomes em portugues (`seg,ter,...`) ou ingles (`mon,tue,...`).
   Ausente ou invalido -> seg-sex como padrao. Pode ser configurado no chat
   com o agente no primeiro uso.

2a. (Opcional) **Disponibilidade semanal** — o agente pergunta no primeiro uso
    e grava no `.env`:
   ```
   WEEKLY_HOURS=5   # horas disponiveis por semana; o build ajusta as duracoes
   LONG_DAY=dom     # dia preferido para treinos longos (seg..dom ou mon..sun)
   ```
   Com `WEEKLY_HOURS`, o `build` escala a duração dos treinos (mínimo 120s por
   esforço) para a semana caber nas horas disponíveis — o orçamento de TSS
   continua mandando. Com `LONG_DAY`, o treino longo/endurance do ciclo cai no
   dia preferido (ou no dia de treino mais próximo, se você não treinar no dia
   preferido). Se você não tem tempo para treinos longos no fim de semana,
   informe o melhor dia — o plano se adapta.

3. Defina o **tipo de plano** (opcional):
   ```
   GOAL=back-to-fitness   # ou ftp-builder | gran-fondo | time-trial |
                          # climbing | active-off-season | race
   ```
   Com `GOAL=race`, defina a data alvo (o `build` **pergunta** se faltar):
   ```
   RACE_DATE=2026-12-01
   ```
   Ausente ou invalido -> comportamento padrao por TSB. O `build` mostra o
   plano ativo e o `plan.json` guarda `goal`/`race_date`.

4. (Opcional) **Agende um teste de FTP**: quando o `ftp-check` indicar
   reteste devido, rode `build --ftp-test YYYY-MM-DD` (ou defina no `.env`
   `FTP_TEST_DATE=YYYY-MM-DD`). O plano protege as **48h antes** do teste
   (D-2 recuperação, D-1 spin fácil), cria o evento `Ramp Test (FTP)` no dia
   e a recuperação no dia seguinte — nada de VO2/Limiar com fadiga acumulada
   antes de testar.

**Primeiro uso (onboarding):** ao montar o primeiro plano, o agente conduz a
configuração no chat — confirma se você já tem conta no Intervals.icu (se não,
orienta criar conta gratuita e conectar suas plataformas via
**Settings → Connections**; guia em `docs/SYNC-PLATAFORMAS.md`), coleta a
API Key (**Settings → Developer Settings**, nunca compartilhe), pergunta sua
**disponibilidade** (quantos dias e quantas horas por semana, e o melhor dia
para treinos longos), agenda, FTP e objetivo (menu com os 7 tipos de plano e a
descrição de cada) e gera o plano. Trocar o objetivo no meio do plano: basta
pedir em linguagem natural (ex.: "quero treinar pra prova de dezembro") — o
agente ajusta o plano (preservando o treino de hoje) e pede confirmação antes
de publicar.

## Instalação do agente por sistema operacional

Requisitos: **Python 3** e o CLI do [opencode](https://opencode.ai). O agente é
linkado na config global do opencode (`~/.config/opencode/agent/`). Troque
`<USERHOME>` pela sua pasta home e ajuste o caminho do repo se não estiver em
`~/Work/hermes-coach`.

### Linux

```bash
mkdir -p ~/.config/opencode/agent
ln -s <USERHOME>/Work/hermes-coach/.opencode/agent/cycling-coach.md \
      ~/.config/opencode/agent/cycling-coach.md
```

Opcional — skill de delegação para o orquestrador Hermes (`~/.hermes`):
```bash
mkdir -p ~/.hermes/skills
ln -s <USERHOME>/Work/hermes-coach/hermes/skills/cycling-coach \
      ~/.hermes/skills/cycling-coach
```

### macOS

O opencode usa a mesma pasta de config (`~/.config/opencode/`), então os
comandos são idênticos ao Linux:

```bash
mkdir -p ~/.config/opencode/agent
ln -s <USERHOME>/Work/hermes-coach/.opencode/agent/cycling-coach.md \
      ~/.config/opencode/agent/cycling-coach.md
```

Opcional — skill para o Hermes (`~/.hermes`):
```bash
mkdir -p ~/.hermes/skills
ln -s <USERHOME>/Work/hermes-coach/hermes/skills/cycling-coach \
      ~/.hermes/skills/cycling-coach
```

### Windows (WSL)

O opencode recomenda rodar no **WSL**. A instalação roda dentro do WSL e a
config fica em `~/.config/opencode/agent/` **dentro do WSL**.

1. Instale o [WSL](https://learn.microsoft.com/windows/wsl/install).
2. No terminal WSL, instale o opencode:
   ```
   curl -fsSL https://opencode.ai/install | bash
   ```
3. Clone o repo preferencialmente no filesystem do WSL (mais rápido) e monte o
   `.env`:
   ```
   git clone https://github.com/valdelin/Hermes-coach.git ~/Work/hermes-coach
   cd ~/Work/hermes-coach
   cp .env.example .env
   ```
   > **Repo privado:** o clone exige a sua conta GitHub logada (SSH ou
   > `gh auth login`); terceiros não têm acesso sem convite.
4. Link do agente (idêntico ao Linux, dentro do WSL):
   ```
   mkdir -p ~/.config/opencode/agent
   ln -s <USERHOME>/Work/hermes-coach/.opencode/agent/cycling-coach.md \
         ~/.config/opencode/agent/cycling-coach.md
   ```

Acesso aos arquivos do Windows via `/mnt/c/Users/<voce>/...`.

## O que o cycling coach faz

O agente `cycling-coach` atua como treinador + automatizador: consulta o
Intervals.icu, decide o foco do dia pelo TSB, monta o plano na agenda
configurada (`TRAINING_DAYS`, padrao seg-sex), respeita o orcamento de carga
(TSS de 7 dias), reage a treinos extras nao planejados e publica tudo no
calendario.

**Plano e cargas**
- `info` — TSB/CTL/ATL atuais no Intervals.icu.
- `check` — **prontidão do dia** (wellness + sinais de recuperação): sugere
  (nunca impõe) trocar o treino de hoje por recuperação Z2 curta (`--apply`
  aplica no `plan.json`, depois `push`); detecta início de doença (RHR subindo
  + HRV caindo) e avisa o treinador via `COACH_WEBHOOK` se configurado.
- `periodization` — explica os 5 modelos de periodização (polarized, pyramidal,
  undulating, linear, block) em linguagem de atleta e sugere o melhor para o
  `GOAL`/TSB atual (`--model NOME` detalha um); não altera nada.
- `build` — plano dos próximos 14 dias com ciclo de foco pelo TSB, orcamento de
  TSS, preservacao do treino de hoje, escala por `WEEKLY_HOURS` e treino longo
  em `LONG_DAY`. Opções: `--no-power` (prescricao em %FTHR + RPE, modo FC),
  `--ftp-test YYYY-MM-DD` (protege 48h antes do Ramp Test) e **`--recovery`**
  (#19): ora cada semana pelos **tetos da rampa de retorno a forma** — consulta
  todo o histórico real, usa a prescrição do `recovery` (mesma rampa `--ramp-pts`
  e `--recovery-weeks`, deload a cada 4 semanas) como orçamento em vez do padrão.
  Com `GOAL=race` dentro do horizonte, mostra a **projecao de TSB no dia da
  prova**.
- `adherence` — cumprimento semanal do plano: treinos feito/perdido/pendente e
  % de conclusão.
- `recovery` — **retorno a forma**: varre todo o histórico real do Intervals
  (só treinos feitos), reconstrói o PMC (CTL/ATL/TSB) ao longo do tempo e
  compara o hoje com o pico histórico (CTL, melhor mês, TSB). Estima o prazo
  (semanas/meses) para voltar a X% do CTL de pico sob rampas conservadora/
  realista/otimista e prescreve a **rampa semanal de TSS** (deload a cada 4
  semanas, teto = carga que sustenta o CTL-alvo). Para gerar os treinos
  respeitando esses tetos, rode `build --recovery`.
- `summary` — **resumo dos treinos realizados** por período (dia/semana/mês,
  trimestre/semestre/ano, duração livre `45d`/`6m`/`1y`, `plan` e `custom`),
  janela terminando no dia-ancla, por padrão ontem: sessões, carga total
  (TSS), tempo, distância, elevação, potência média/NP e FC média, com o
  detalhe de cada treino feito. Usa só atividades pareadas — o
  planejado-não-feito fica fora. **Períodos:**
  - `--period month` / `quarter` / `semester` / `year` — nomes prontos
    (30/90/180/365 dias);
  - `--period 45d` / `6m` / `1y` — duração livre (d = dias, m = meses, y =
    anos);
  - `--period plan` — do primeiro ao último dia do plano salvo (relatório
    final do ciclo);
  - `--period custom --start 2026-08-18 --end 2026-09-24` — intervalo
    explícito.
  **Gráficos** opcionais no espírito do
  "Advanced Progress Tracking": `--chart auto` (padrão) traz o **PMC**
  (CTL/ATL/TSB em sparklines, escala compartilhada; a janela acompanha o
  período, piso de 90 dias) e a
  **carga semanal** (barras de TSS/semana ISO); `--chart none|pmc|load|all`
  escolhe o modo. **`--export arquivo`** gera o relatório com gráficos SVG:
  `.html` salva direto; `.pdf` renderiza o mesmo HTML no **chromium headless**
  (`--print-to-pdf`) — independente de `--chart`, sempre leva os dois gráficos.
  O relatório tem **`--theme TEMA`** (22 temas, default `tokyo-night`); no
  HTML o leitor troca pelo menu **"Temas"** ou tecla **T** e a escolha é
  lembrada (`localStorage`). A **linha de forma (TSB) muda de cor pelo estado**
  do atleta: vermelho = alto risco (TSB ≤ −10), verde = treino ideal, azul =
  fresco e em forma (`docs/TEMAS.md` tem o kit portátil dos temas).
- `reconcile` — treino perdido de Z2/Sweet Spot pode ser absorvido no orçamento
  semanal disponível; recuperação ativa e Limiar/VO2 não são compensados por
  volume. Treino extra fora do plano é considerado pela carga real.
- `push` — upsert no calendario + limpeza automatica de eventos `hermes-plan*`
  orfaos; `.zwo` baixado no app (sem geracao local).
- `model` — Expected PMC (Banister): CTL/ATL/TSB projetados do real + plano,
  com **zona de TSB de Joe Friel** por dia (`high-risk < −30` → R&R,
  `transition > +25` → descanso longo) e avisos.
- `all` — fluxo completo.
- Nome dos treinos no padrao `YYYY-MM-DD - Treino de <Foco>`; descricao na
  notacao nativa do workout builder (passos com mensagem explicativa, repeticoes
  achatadas, idioma por `CUE_LANG`, comparativo `prev`).

**Objetivos (GOAL)** — 7 tipos de plano: `back-to-fitness`, `ftp-builder`,
`gran-fondo`, `time-trial`, `climbing`, `active-off-season` e `race` (exige
`RACE_DATE`). Para `race`, a ultima semana vira **taper progressivo** (periodizacao
de Joe Friel): D-6 ultimo estimulo de qualidade (Limiar curto), D-5..D-3
recuperacao Z2, D-2/D-1 spin muito leve; o dia da prova recebe um **evento no
calendario** (TSS 0, `Prova: dia de prova`) e o `build` projeta o TSB no dia
da prova contra a faixa-alvo `−10..+20` (avisa se chega cansado ou passou do
pico — semente do #16, TSB-alvo pessoal). Troca de objetivo a qualquer momento
preservando o treino de hoje.

**Teste de FTP**
- `ftp-check` — ultimo teste de FTP no historico e se o reteste (janela de 8
  semanas) e devido; quando devido, sugere o Ramp Test do Zwift (nunca agenda
  por conta propria).
- `ftp-scan` (issue #6): estima FTP de **pedais duros nao agendados**
  (best-20min x 0,95 + gates de qualidade, `src/ftp_estimation.py`) e propoe a
  atualizacao **apenas com confirmacao do atleta**.

**Automacao** — timer systemd `cycling-coach-daily` roda `reconcile + push` a
meia-noite (`scripts/daily_reconcile.sh`, log em `logs/`); falha notifica no
desktop via `notify-send`.

**Seguranca/qualidade** — API key so no `.env` (nunca exposta/commitada); nunca
inventa TSB se o Intervals falhar; suíte de testes obrigatoria antes de concluir
(`python3 -m unittest discover -s tests -v`).

## Uso

Plano de treinos adaptativo (historico -> calendario do Intervals):
```
python3 src/training_plan.py info                        # TSB/CTL/ATL atuais
python3 src/training_plan.py model                       # Expected PMC (Banister) + zonas Friel + projecao
python3 src/training_plan.py build --days 60 --days-plan 14   # gera plano
python3 src/training_plan.py build --no-power            # modo FC: alvos em %FTHR + RPE
python3 src/training_plan.py adherence --show            # cumprimento semanal do plano
python3 src/training_plan.py recovery                    # retorno a forma: estimativa + rampa segura
python3 src/training_plan.py summary --period week       # resumo da semana + gráficos (PMC 90d, carga semanal)
python3 src/training_plan.py summary --period semester --export relatorio-6m.html   # relatório de 6 meses
python3 src/training_plan.py summary --period year       # resumo do ano (365 dias)
python3 src/training_plan.py summary --period 6m         # duração livre (6 meses)
python3 src/training_plan.py summary --period plan       # do início ao fim do plano salvo
python3 src/training_plan.py summary --period custom --start 2026-08-18 --end 2026-09-24  # intervalo explícito
python3 src/training_plan.py summary --chart none        # só os números, sem gráficos
python3 src/training_plan.py summary --export resumo.html  # relatório com gráficos SVG
python3 src/training_plan.py summary --export resumo.pdf   # PDF via chromium headless
python3 src/training_plan.py summary --theme matte-black --export resumo.pdf  # tema
python3 src/training_plan.py reconcile --show         # detecta treinos perdidos
python3 src/training_plan.py push --start 2026-09-16  # publica no Intervals (upsert)
python3 src/training_plan.py all                      # fluxo completo
```
O comando `model` roda o **motor de carga Impulse-Response** (Banister,
`src/impulse_response.py`): calcula CTL/ATL/TSB localmente a partir do TSS
diario da janela, compara com o Intervals e projeta a forma ao seguir o plano
atual (`plan.json`), classificando cada dia na **zona de TSB de Joe Friel**
(`high-risk`/`transition` recebem aviso de R&R/descanso longo). Referencia
confiavel para o dia a dia continua sendo o Intervals; o motor local brilha na
**projecao** (ex.: "seguir o plano derruba o TSB para X em 2 semanas").
O `external_id` e usado como chave de upsert: rodar de novo nao duplica eventos
no Intervals. O `push` tambem remove automaticamente eventos `hermes-plan*`
que nao constam mais no plano (ex.: datas que mudaram em um rebuild). Treinos
de hoje sao publicados com `push --start <data-de-hoje>`; os arquivos `.zwo`
correspondentes sao baixados no app do Intervals.icu.

Via Hermes (delega ao agente opencode — tier gratuito):
> "rode o cycling-coach: gera o treino de hoje"

Via opencode direto:
```
opencode run --agent cycling-coach "Gera o treino de hoje"
```

Testes:
```
python3 -m unittest discover -s tests -v
```
(712 testes, apenas stdlib — o CI roda a mesma suíte em todo push/PR.)

## Automacao diaria (opcional)

O fluxo completo pode rodar automaticamente a meia-noite, sem depender do
Hermes/opencode:
- **Timer do systemd** `cycling-coach-daily.timer` dispara
  `scripts/daily_reconcile.sh` (reconcile + push do dia).
- O log fica em `logs/daily_reconcile.log`.
- **Alerta de falha:** se qualquer passo falhar, o script emite uma
  notificacao no desktop (`notify-send`) e sai com codigo != 0 — assim uma
  falha silenciosa nao passa despercebida.

## Plano e autoregulação

Treinos planejados apenas nos dias configurados em `TRAINING_DAYS` (padrao:
**segunda a sexta**); os demais dias sao descanso (treino fora da agenda so por
pedido ao Hermes). O foco de cada dia acompanha a **posicao** na agenda (a
tabela abaixo assume a semana completa de 5 dias; com uma agenda menor, os
primeiros focos do ciclo sao usados). A carga respeita um **orcamento semanal**:
a soma rolante de TSS dos ultimos 7 dias nao estoura `cap_diario * 7`; se
estourar, o treino do dia e reduzido (encurta `on_sec` >= 120s, depois
`on_power` >= 55%) e os dias subsequentes herdam a folga. Ao regerar o plano,
o treino de hoje ja existente no `plan.json` e preservado.

**Treinos extras fora do plano:** se o atleta pedalar num dia nao agendado,
o reconcile considera a carga desses treinos (eventos com `paired_activity_id`
e `external_id` nao-hermes) nos ultimos 7 dias. Se a soma chegar a um treino
cheio (`>= cap_diario`, calculado pela carga real), o proximo dia de treino
vira recuperacao e o proximo Limiar e reduzido 5%. Trabalho leve nao altera o
plano. O mesmo vale para **treinos perdidos** (planejados e nao feitos): o
proximo limiar e reduzido no maximo uma vez por reconcile — a protecao
(`reduced_ids`) evita que dois eventos na mesma janela reduzam o mesmo treino
duas vezes, e a recuperacao nunca e inserida em dias passados.

A agenda em uso e impressa no `build` e no `reconcile`
(`Agenda: seg,ter,qua,qui,sex`), com aviso quando `TRAINING_DAYS` nao esta
definido no `.env`.

O **tipo de plano** (`GOAL`) muda a distribuição de focos e a escala de carga
do `build` (via `GOAL_TEMPLATES`/`GOAL_BUDGET_SCALE` em `src/plan.py`):

| `GOAL` | Comportamento |
|---|---|
| *(ausente)* | Padrão por TSB (como antes) |
| `back-to-fitness` | Volta de pausa longa: base zona 2, carga ~60% |
| `ftp-builder` | Mais Limiar/Sweet Spot + VO2 curto; carga padrão |
| `gran-fondo` | Endurance longo na semana + volume maior |
| `time-trial` | Ênfase em Limiar/super-limiar; carga alta |
| `climbing` | VO2/Limiar em repetições; carga alta |
| `active-off-season` | Quase tudo zona 2; carga ~60% |
| `race` | Exige `RACE_DATE`; a última semana vira **taper progressivo** (D-6 estímulo → D-5..D-3 recuperação → D-2/D-1 spin), evento no dia da prova e projeção de TSB contra a faixa-alvo `−10..+20` |

Com `GOAL` ativo o `build` também **varia os formatos** dos treinos do mesmo
foco (séries curtas/longas, over-unders, contínuos) para o plano não ficar
monótono — a prescrição é própria do hermes (periodização clássica), não uma
replicação de planos prontos.

O nome de cada evento no Intervals leva a data na frente:
`YYYY-MM-DD - Treino de <Foco>` (ex.: `2026-09-21 - Treino de Zona 2`).

`GOAL` e proximidade da prova definem a fase e o alvo semanal. TSB e readiness
são sinais de autoregulação diária: TSB abaixo de −15 ou readiness desfavorável
adaptam somente a primeira sessão de qualidade para recuperação Z2. Eles não
mudam automaticamente a fase do macrociclo.

Cada treino tem aquecimento 10 min (45% -> 75%) e desaquecimento 10 min
(70% -> 45%). A descricao publicada usa a notacao nativa do workout builder do
Intervals (os watts aparecem calculados pelo app) e inclui **mensagens
explicativas** antes de cada passo (o aquecimento explica a zona, e cada
intervalo recebe "Agora voce vai entrar em X minutos a Y por cento do seu
FTP"). O idioma das mensagens e controlado por `CUE_LANG` no `.env` (`pt`|`en`).

### Camada de decisão adaptativa (módulos, ainda não no fluxo de publicação)

A v0.0.34 adiciona um conjunto de módulos de domínio que **ainda não alteram o
que é publicado no Intervals.icu**. O `build`/`push` continuam usando
`src/plan.py` exatamente como antes; os módulos abaixo existem para que a lógica
de decisão possa ser testada e revisada isoladamente antes de entrar no caminho
de publicação.

| Módulo | Papel |
|---|---|
| `training_phase.py` | Fases `base`/`build`/`specific`/`peak`/`recovery`/`test` com critérios de progressão, deload e saída |
| `progression.py` | Progressão por família de estímulo; só avança com `CompletionScore` bem-sucedido |
| `intensity_distribution.py` | Minutos efetivos LOW/MOD/HIGH por semana, sem pressupor 80/20 |
| `athlete_profile.py` | Marcadores fisiológicos opcionais, com `FtpSource`/`FtpConfidence` |
| `adaptation.py` | Seis domínios de adaptação com decaimento e saturação |
| `training_decision.py` | Compõe tudo numa decisão com `rationale` e `confidence` |
| `readiness_assessment.py` | Prontidão multimodal; `GREEN`/`YELLOW`/`RED` = adequação ao treino |
| `critical_power.py` | CP e W′ como complemento ao FTP, com ajuste `P = CP + W′/t` |
| `vo2_generator.py` | Bloco VO2max estruturado; 106–120% FTP, progressão alterando **uma** dimensão por degrau |
| `zone_intent.py` | Intenção e dose de Z2 / Sweet Spot / Limiar; `classify()` recusa adivinhar na sobreposição de 91–97% FTP |

Os limiares e sequências desses módulos são **heurísticas computacionais
configuráveis**, não constantes fisiológicas universais — ver
[docs/EMBASAMENTO-CIENTIFICO.md](docs/EMBASAMENTO-CIENTIFICO.md).

## Direções futuras (em validação)

> Visão consolidada com escopo, fases e status: **[docs/ROADMAP.md](docs/ROADMAP.md)**.

- **Produto**: vender para treinadores (**multi-atleta**) com **modo solo**
  (sem treinador) como opção — roteiro de entrevista no vault do Obsidian
  (`ROTEIRO-TREINADOR.md`).
- **IA vs biblioteca**: decidir com o treinador se o treino continua gerado por
  regras (determinístico, como hoje) ou passa a ser escolhido de uma biblioteca
  de treinos validados.
- **Semanas de descanso / deload** a cada 3–4 semanas: avaliar agendamento
  automático.
- **Multi-esporte (corrida)**: protótipo implementado em
  `src/plan_run.py` (#18) — prescrição **sem power meter**, variável de controle
  **por template**: contínua/longa = `hr` (%LTHR), tempo/limiar/VO2 = `pace`
  (ritmo-alvo rFTP), fartlek = `rpe`; `tss: 0` (carga via Intervals por FC).
  Falta validar com treinador quando usar cada controle + decisão FIT vs texto
  puro para o relógio. O conceito original (vDOT, pace/km) segue em
  [docs/ARQUITETURA.md](docs/ARQUITETURA.md) como referência.
- **Notificações do treino** (issue [#2](https://github.com/valdelin/Hermes-coach/issues/2)):
  enviar resumo do treino por **e-mail, WhatsApp ou Telegram** (foco + TSB +
  TSS previsto/real + avisos do reconcile). Proposta: começar por Telegram e
  manter interface extensível; envio assíncrono para não quebrar o fluxo diário.
  **Adiado** (decisão do roteiro com treinador).
- **Treinos sem medidor de potência** (issue [#3](https://github.com/valdelin/Hermes-coach/issues/3)):
  **implementado** (v0.0.16) e encerrado — `build --no-power` prescreve alvos em
  **%FTHR + RPE** (modo FC, `FTHR` no `.env`); o `ftp-scan` estima FTP de pedais
  duros não agendados (#6) para alimentar o modo potência.
- **TSB-alvo pessoal** (issue [#16](https://github.com/valdelin/Hermes-coach/issues/16)):
  semente implementada (v0.0.20) — o `build` projeta o TSB no dia da prova contra
  a faixa `−10..+20` (referência Joe Friel ~+20, benchmark de case study);
  aprendizado pessoal do alvo em validação.
- **Formato FIT structured workout vs texto puro** (#18): decidir com o treinador
  se os treinos de corrida vão para o relógio como FIT estruturado ou texto.
- **Sync de wellness** (issue [#4](https://github.com/valdelin/Hermes-coach/issues/4)):
  **implementado** — o Garmin Connect → Intervals.icu já entrega RHR e sono
  reais; o `info` agora exibe `Wellness:` (RHR atual/média 7d, sono, passos,
  HRV quando disponível). **Decisão HRV (FR935):** sem HRV Status overnight
  (exige Elevate Gen 3+); monitorar via Oura/WHOOP ou novo relógio fica em
  aberto no backlog.
- **Tipos de plano de treino** (issue [#5](https://github.com/valdelin/Hermes-coach/issues/5)):
  **implementado** — `GOAL` no `.env` (`back-to-fitness`, `ftp-builder`,
  `gran-fondo`, `time-trial`, `climbing`, `active-off-season` e `race` com
  `RACE_DATE` + **taper progressivo** de 7 dias e projeção de TSB no dia da
  prova). Próximos passos em aberto: validar a
  prescrição por tipo com treinador (ROTEIRO-TREINADOR) e usar o catálogo na
  tela de seleção do onboarding (Fase 3, ADR-003 "Runna do ciclismo indoor").
- **FTP sugerido de treinos não agendados** (issue [#6](https://github.com/valdelin/Hermes-coach/issues/6)):
  **implementado** (`ftp-scan`, `src/ftp_estimation.py`) — quando o atleta faz
  uma prova ou treino livre com potência, estima um novo
  FTP do **stream de potência** (melhor média móvel de 20 min × 0,95), com
  gates de qualidade do esforço e de contexto (fatiga, dias protegidos) e
  **confirmação do atleta** antes de atualizar `.env FTP` + `indoor_ftp` no
  Intervals. Complementa o `ftp-check` da #5 ("teste grátis de FTP").

## Notas / limitacoes do scaffold

- Campos retornados pelo endpoint `/events` do Intervals.icu podem variar
  (`tsb`/`ctl`/`atl` vêm do parametro `?summary=1` por evento, ou de dentro de
  `summary`). `src/coach.py::latest_metrics` tolera ambos; ajuste se o seu
  plano retornar outro formato.
- `estimated_tss` é uma estimativa operacional do **treino planejado**
  (somatório de `seg*fração³ / 36`), usada para orçamento. TSS **executado** por
  potência usa NP/FTP (`horas × IF² × 100`) apenas quando essas medidas existem;
  o Intervals continua sendo a fonte autoritativa de carga histórica.
- Fora do escopo: geracao de `.zwo` local. Baixe os treinos em
  **Custom Workouts / exportar** no app do Intervals para usar no Zwift.

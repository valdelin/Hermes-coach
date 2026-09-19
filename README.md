# Hermes Coach — agente de treino de ciclismo indoor

[![CI](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml/badge.svg)](https://github.com/valdelin/Hermes-coach/actions/workflows/test.yml)

> **English version:** [README.en.md](README.en.md)

Agente que consulta o **Intervals.icu**, calcula o **TSB** (forma), decide o
foco do dia e publica o treino no calendario do Intervals.icu (os arquivos
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
│   ├── coach.py                       # TSB -> foco -> carga (TSS)
│   ├── impulse_response.py            # motor Banister local (CTL/ATL/TSB)
│   ├── plan.py                        # plano semanal (build/reconcile)
│   └── training_plan.py               # CLI do plano (info/model/build/reconcile/push)
└── tests/                             # testes (stdlib unittest)
```

## Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — conceito original do agente
  (motor Impulse-Response/Banister, schema de estado do atleta, system prompt)
  e diferenças para a implementação atual. **Não implementado** — referência de
  design e direção futura multi-esporte (corrida). Sincronizado com o vault do
  Obsidian.
- Roteiro de validação com treinador (ciência do treino + produto
  multi-atleta/modo solo): `ROTEIRO-TREINADOR.md` no vault do Obsidian.
- [docs/SYNC-PLATAFORMAS.md](docs/SYNC-PLATAFORMAS.md) — como conectar cada
  plataforma (Garmin, Zwift, Wahoo, Strava, Polar, COROS, Suunto, Oura/WHOOP
  etc.) ao Intervals.icu (atividades, wellness e treinos planejados).

## Setup

1. Copie as credenciais:
   ```
   cp .env.example .env
   # preencha INTERVALS_ATHLETE_ID, INTERVALS_API_KEY, FTP
   # opcional: CUE_LANG=pt (padrao) ou en — idioma das mensagens dos treinos
   ```
   (A API do Intervals.icu usa HTTP Basic Auth com usuario = senha = API_KEY.)

2. Defina sua agenda de treinos no `.env` (opcional):
   ```
   TRAINING_DAYS=seg,ter,qua,qui,sex
   ```
   Aceita nomes em portugues (`seg,ter,...`) ou ingles (`mon,tue,...`).
   Ausente ou invalido -> seg-sex como padrao. Pode ser configurado no chat
   com o agente no primeiro uso.

2. Instale o agente no opencode (ja linkado em `~/.config/opencode/agent/`):
   ```
   mkdir -p ~/.config/opencode/agent
   ln -s /home/valdelin/Work/hermes-coach/.opencode/agent/cycling-coach.md \
         ~/.config/opencode/agent/cycling-coach.md
   ```

3. Instale a skill no Hermes (ja linkada em `~/.hermes/skills/`):
   ```
   mkdir -p ~/.hermes/skills
   ln -s /home/valdelin/Work/hermes-coach/hermes/skills/cycling-coach \
         ~/.hermes/skills/cycling-coach
   ```

## Uso

Plano de treinos adaptativo (historico -> calendario do Intervals):
```
python3 src/training_plan.py info                        # TSB/CTL/ATL atuais
python3 src/training_plan.py model                       # motor Banister local + projecao do plano
python3 src/training_plan.py build --days 60 --days-plan 14   # gera plano
python3 src/training_plan.py reconcile --show         # detecta treinos perdidos
python3 src/training_plan.py push --start 2026-09-16  # publica no Intervals (upsert)
python3 src/training_plan.py all                      # fluxo completo
```
O comando `model` roda o **motor de carga Impulse-Response** (Banister,
`src/impulse_response.py`): calcula CTL/ATL/TSB localmente a partir do TSS
diario da janela, compara com o Intervals e projeta a forma ao seguir o plano
atual (`plan.json`). Referencia confiavel para o dia a dia continua sendo o
Intervals; o motor local brilha na **projecao** (ex.: "seguir o plano derruba
o TSB para X em 2 semanas").
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
(64 testes, apenas stdlib — o CI roda a mesma suíte em todo push/PR.)

## Automacao diaria (opcional)

O fluxo completo pode rodar automaticamente a meia-noite, sem depender do
Hermes/opencode:
- **Timer do systemd** `cycling-coach-daily.timer` dispara
  `scripts/daily_reconcile.sh` (reconcile + push do dia).
- O log fica em `logs/daily_reconcile.log`.
- **Alerta de falha:** se qualquer passo falhar, o script emite uma
  notificacao no desktop (`notify-send`) e sai com codigo != 0 — assim uma
  falha silenciosa nao passa despercebida.

## Regras de decisao (TSB)

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

O nome de cada evento no Intervals leva a data na frente:
`YYYY-MM-DD - Treino de <Foco>` (ex.: `2026-09-21 - Treino de Zona 2`).

| TSB          | Ciclo semanal (5 dias de treino)               |
|--------------|-----------------------------------------------|
| < -15        | Z2, Z2, Sweet Spot, Z2, Sweet Spot            |
| -15 a 0      | Z2, Sweet Spot, Z2, Sweet Spot, VO2 Max       |
| 0 a 5        | Sweet Spot, Limiar, Sweet Spot, Limiar, VO2   |
| >= +5        | Limiar, VO2 Max, Sweet Spot, Limiar, VO2 Max  |

Cada treino tem aquecimento 10 min (45% -> 75%) e desaquecimento 10 min
(70% -> 45%). A descricao publicada usa a notacao nativa do workout builder do
Intervals (os watts aparecem calculados pelo app) e inclui **mensagens
explicativas** antes de cada passo (o aquecimento explica a zona, e cada
intervalo recebe "Agora voce vai entrar em X minutos a Y por cento do seu
FTP"). O idioma das mensagens e controlado por `CUE_LANG` no `.env` (`pt`|`en`).

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
- **Multi-esporte (corrida)**: o conceito original do agente (vDOT, pace/km,
  FC, sistema prompt de corrida) está em [docs/ARQUITETURA.md](docs/ARQUITETURA.md)
  como direção futura — não implementado.
- **Notificações do treino** (issue [#2](https://github.com/valdelin/Hermes-coach/issues/2)):
  enviar resumo do treino por **e-mail, WhatsApp ou Telegram** (foco + TSB +
  TSS previsto/real + avisos do reconcile). Proposta: começar por Telegram e
  manter interface extensível; envio assíncrono para não quebrar o fluxo diário.
- **Treinos sem medidor de potência** (issue [#3](https://github.com/valdelin/Hermes-coach/issues/3)):
  pedais outdoor sem potência deixam os dados incompletos (sem NP/TSS por
  watts e sem verificação de %FTP). Proposta: detectar ausência de potência,
  configurar `FTHR` (FC de limiar) no `.env`, estimar carga por FC
  (`hrTSS`) e prescrever alvos em %FTHR/RPE nos dias outdoor.
- **Sync de wellness** (issue [#4](https://github.com/valdelin/Hermes-coach/issues/4)):
  ativar Garmin Connect → Intervals.icu (RHR, sono, Body Battery) — hoje os
  registros de wellness estão vazios, limitando a avaliação de recuperação ao
  TSB. Avaliar HRV (Forerunner 935 não tem HRV status overnight).

## Notas / limitacoes do scaffold

- Campos retornados pelo endpoint `/events` do Intervals.icu podem variar
  (`tsb`/`ctl`/`atl` vêm do parametro `?summary=1` por evento, ou de dentro de
  `summary`). `src/coach.py::latest_metrics` tolera ambos; ajuste se o seu
  plano retornar outro formato.
- A estimativa de TSS e aproximada (somatorio de `seg*fracao^3 / 36`), suficiente
  para comparar carga dia a dia, nao para planejamento cientifico.
- Fora do escopo: geracao de `.zwo` local. Baixe os treinos em
  **Custom Workouts / exportar** no app do Intervals para usar no Zwift.
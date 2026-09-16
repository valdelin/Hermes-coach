# Hermes Coach — agente de treino de ciclismo indoor

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
│   ├── plan.py                        # plano semanal (build/reconcile)
│   └── training_plan.py               # CLI do plano (info/build/reconcile/push)
└── tests/                             # testes (stdlib unittest)
```

## Setup

1. Copie as credenciais:
   ```
   cp .env.example .env
   # preencha INTERVALS_ATHLETE_ID, INTERVALS_API_KEY, FTP
   # opcional: CUE_LANG=pt (padrao) ou en — idioma das mensagens dos treinos
   ```
   (A API do Intervals.icu usa HTTP Basic Auth com usuario = senha = API_KEY.)

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
python3 src/training_plan.py build --days 60 --days-plan 14   # gera plano
python3 src/training_plan.py reconcile --show         # detecta treinos perdidos
python3 src/training_plan.py push --start 2026-09-16  # publica no Intervals (upsert)
python3 src/training_plan.py all                      # fluxo completo
```
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

## Regras de decisao (TSB)

Treinos planejados de **segunda a sexta, todos os dias uteis preenchidos**;
sabado e domingo sao descanso (treino de fim de semana so por pedido ao
Hermes). A carga respeita um **orcamento semanal**: a soma rolante de TSS dos
ultimos 7 dias nao estoura `cap_diario * 7`; se estourar, o treino do dia e
reduzido (encurta `on_sec` >= 120s, depois `on_power` >= 55%) e os dias
subsequentes herdam a folga.

O nome de cada evento no Intervals leva a data na frente:
`YYYY-MM-DD - Treino de <Foco>` (ex.: `2026-09-21 - Treino de Zona 2`).

| TSB          | Ciclo semanal (seg-sex)                       |
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

## Notas / limitacoes do scaffold

- Campos retornados pelo endpoint `/events` do Intervals.icu podem variar
  (`tsb`/`ctl`/`atl` vêm do parametro `?summary=1` por evento, ou de dentro de
  `summary`). `src/coach.py::latest_metrics` tolera ambos; ajuste se o seu
  plano retornar outro formato.
- A estimativa de TSS e aproximada (somatorio de `seg*fracao^3 / 36`), suficiente
  para comparar carga dia a dia, nao para planejamento cientifico.
- Fora do escopo: geracao de `.zwo` local. Baixe os treinos em
  **Custom Workouts / exportar** no app do Intervals para usar no Zwift.
# Comparação de Cálculo de PMC — modelo antigo vs atual (v0.0.29)

Análise de 27/09/2026, dados reais da conta do atleta (janela de 60 dias,
28/07 a 26/09/2026). Contexto completo da investigação no ROADMAP (#33, #34,
#35) e no CHANGELOG [0.0.29].

## Resumo

| | Modelo antigo (reconstrução de zero) | Modelo atual (ancorado no Intervals) |
|---|---|---|
| Mecanismo | EWMA 42/7 **partindo de zero** sobre a carga real `icu_training_load` (somada por dia, treino feito) | Parte dos valores **reais `icu_ctl`/`icu_atl`** que a API devolve em cada treino; decaimento EWMA 42/7 com TSS 0 entre os dias |
| Onde era usado | `summary` (gráfico), `recovery`, `build --recovery` | `coach.real_pmc_by_day` + `recovery.pmc_series_anchored` (padrão do `summary`) |
| Onde ainda cai no antigo | — | fallback (`pmc_series`): clientes de teste / quando a API não traz `icu_ctl` |
| CTL (60d) | 10.0 | **25.3** |
| ATL (60d) | 24.2 | **47.1** |
| TSB (60d) | −14.2 | **−21.8** |
| Formato da curva | mesma forma (sobe + recuo no fim) | mesma forma, na escala correta |

O gráfico comparativo gerado na sessão (HTML/SVG lado a lado, tema do
relatório) mostrou que as duas curvas têm o **mesmo formato** — subida partindo
do retorno de treino e recuo final — porém o modelo antigo plotava a curva em
uma escala ~2× menor.

## Por que o modelo antigo divergia

A pipeline interna do Intervals.icu calcula a carga efetiva com valores ~2× o
`icu_training_load` (visto nos eventos reais: transição de ATL 29.1→54.3 com
loads 54/57/49/57 exige carga efetiva ~110; `strain_score` 60.5 e `joules`
417900 num treino de 52min). Então:

1. A reconstrução local alimentava o EWMA com **metade da carga** → CTL/ATL
   cresciam mais devagar;
2. A reconstrução **partia de zero** no primeiro treino da janela → subestimava
   o estado no dia de retorno (que na verdade já carregava o decaimento do
   histórico completo do Intervals);
3. O Intervals usa o **histórico completo** da conta (constantes
   `ctl_days`/`atl_days` configuráveis, NP, timezone) — não reproduzível por
   EWMA simples sobre `icu_training_load`.

## O que o modelo atual faz

- `coach.real_pmc_by_day(events)` — extrai o `icu_ctl`/`icu_atl` **reais por
  dia de treino** (o mesmo número que o Intervals plota no painel);
- `recovery.pmc_series_anchored(real, start, end)` — monta a série diária:
  nos dias com treino usa o valor real da API; nos demais dias decai EWMA com
  TSS 0 (mesmo decaimento do Intervals entre treinos). Sem cold-start de zero.

Resultado na janela de 60 dias: fim da série em 26/09 = **CTL 25.34** (último
valor real 25/09 = 25.95 decaído 1 dia) — batendo com o painel do Intervals.

## Por que o bug importava além do gráfico (e como ficou)

O `recovery` (CLI) e o `build --recovery` ainda reconstruíam o PMC de zero —
o número que **decidia a rampa de retorno** estava na escala errada. Com a
reconstrução o histórico mostrava CTL atual 9.8 e pico 23.9; ancorado no
Intervals, CTL atual **24.7** e pico **32.0** (fev/22).

- Pico/melhor-mês/TSB reportados pelo `recovery` agora são os do Intervals;
- A rampa em **TSS do plano** não pode usar `pico × 7` direto (misturaria a
  escala ~2× do Intervals com o TSS do plano). O teto é **calibrado**
  (`recovery.calibrated_state`): teto = volume semanal atual × CTL pico / CTL
  atual. Ex.: 100 × 32/24.7 ≈ **130 TSS/sem**, vs os 224 de `32×7`.
- `build --recovery` ora os próximos dias por essa rampa calibrada.

## Escopo e limites da comparação

- Validade: conta do próprio usuário (1 atleta, ~5 semanas de retorno após
  hiato de 2 anos).
- O **hiato de 2 anos** não causa a divergência: a memória exponencial do EWMA
  (τ CTL=42, τ ATL=7) faz CTL/ATL irem a ~0 nos dois modelos após o hiato —
  zero pós-hiato é fisiologicamente correto (memória de treino expira).
- A ancoragem é barata e robusta (usa dado da API) — por isso preferida à
  recriação da pipeline do Intervals (#34).
- **#35 registrado**: validar a consistência do modelo com dados de ao menos
  um **2º atleta de verdade** (outdoor/NP, FTHR, CTL alto, periodização por
  blocos) quando o fluxo do portal (#23) estiver pronto.
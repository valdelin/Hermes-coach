# Manual da TUI — Hermes Coach

> A TUI é uma interface local-first em [Textual](https://textual.textualize.io/).
> Ela apresenta dados do motor determinístico e do Intervals.icu; não substitui
> nem duplica as regras de prescrição.

## Executar

```bash
python3 scripts/hermes_tui.py
```

Pré-requisitos:

- dependências de `requirements.txt` instaladas;
- `.env` com `INTERVALS_ATHLETE_ID`, `INTERVALS_API_KEY` e `FTP`;
- acesso ao Intervals.icu para histórico, wellness e streams de atividade.

Sem credenciais ou dados remotos, as telas continuam abrindo, mas mostram apenas
o que puder ser obtido do plano local.

## Telas e atalhos

| Tela | Abrir | Conteúdo |
|---|---|---|
| Dashboard | inicial / `h` | FTP, VO₂, CTL, ATL, TSB, PMC, treino de hoje e próximos treinos. |
| Calendário | `c` | Plano local + atividades realizadas no Intervals.icu. |
| Prontidão | `t` | Cobertura de wellness, avaliação visual e recomendações informativas. |

Atalhos globais: `q` sai; `Esc` volta. A barra inferior mostra os atalhos da
tela atual.

## Operações protegidas

No dashboard, `g`, `r` e `p` iniciam respectivamente gerar plano, reconciliar e
publicar. Em Prontidão, `a` inicia `check`. A TUI sempre executa primeiro uma
prévia pela facade `scripts/hermes_agent.py`, mostra a saída e só então oferece
aplicação. Para publicar, além da prévia há uma confirmação adicional: digite
`PUBLICAR`. Cancelar em qualquer etapa não executa a ação mutável.

## Calendário e detalhe de treino

Use as setas para selecionar o dia, `m`/`w` para alternar mensal/semanal e
`Enter` (ou espaço) para abrir o detalhe.

- **REALIZADO**: treino planejado e atividade realizada no mesmo dia;
- **PLANEJADO • NÃO REALIZADO**: existe plano, sem atividade realizada;
- **EXTRA**: atividade realizada sem treino planejado.

Quando há mais de uma atividade no mesmo dia, a TUI prefere a que contém maior
evidência de execução (carga, duração, potência e origem não manual), evitando
que um evento manual vazio oculte o FIT/Zwift real.

O detalhe busca sob demanda os streams de atividade do Intervals.icu. Quando
existirem, mostra potência, FC e cadência ao longo da atividade e tempo em zonas
de potência e FC. Os limites de FC vêm de `icu_hr_zones` da atividade. A tela se
redesenha ao redimensionar o terminal e mantém streams em cache enquanto aberta.

## Prontidão: interpretação e limites

Não é diagnóstico médico. O Intervals pode fornecer FC de repouso, HRV,
duração/score de sono, fadiga, soreness, stress, mood, motivation, readiness do
provider, CTL e ATL. Campos ausentes aparecem em cinza e reduzem a confiança.

Um score de prontidão só é interpretável quando o sinal bruto tem baseline
individual e regra de normalização explícitos. A TUI atual é de leitura: não
executa `check --apply` nem muda o plano.

## Segurança e escopo atual

Dashboard e telas implementadas são **somente leitura**. Ações futuras devem
usar exclusivamente `scripts/hermes_agent.py`, preservar dry-run e pedir
confirmação antes de qualquer `build --apply`, `reconcile --apply` ou `push`.

## Código comentado para estudo

As cópias didáticas da TUI ficam em `docs/CODIGO-COMENTADO/src/ui/` e
`docs/CODIGO-COMENTADO/scripts/hermes_tui.py`. Elas possuem somente um cabeçalho
explicativo; o código executável e canônico continua em `src/ui/` e
`scripts/hermes_tui.py`.

## Diagnóstico rápido

| Sintoma | Verificar |
|---|---|
| PMC sem dados | Credenciais, atividades com carga e acesso ao Intervals.icu. |
| Sem gráfico no detalhe | A atividade precisa de stream de potência/FC/cadência; evento manual pode não ter streams. |
| Poucos eixos de prontidão | O provider não enviou wellness para a data; confira a sincronização no Intervals.icu. |
| Dados antigos | A TUI prioriza o registro de wellness mais recente com algum sinal. |

## Próximas capacidades

O backlog específico está no item **#65** de
[`docs/ROADMAP.md`](ROADMAP.md): ações protegidas, prontidão com baselines,
plano semanal, PMC explorável, alertas e configuração.

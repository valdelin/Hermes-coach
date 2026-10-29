# Esboço da Interface - Hermes Coach (v1)

> Status: **Fundação de leitura implementada; operações mutáveis pendentes**
> Abordagem: **TUI com Textual** (local-first, reaproveita arquitetura atual)
> Data: 29/10/2026

## 1) Objetivo

Criar uma interface mais legível para o fluxo diário do Hermes Coach, sem duplicar a lógica do motor. A UI deve ser um "painel" sobre o que já existe: `src/training_plan.py`, `src/application.py`, `plan.json` e integração com `Intervals.icu`.

## 2) Princípios

- **Reutilizar, não reescrever**: usar `Application`, `load_plan`, `IntervalsAdapter` e funções já existentes.
- **Seguro por padrão**: toda ação mutável exige confirmação. `push` sempre com `--dry-run` antes.
- **Espelhar o CLI**: mapeia 1:1 com comandos existentes (`build`, `check`, `reconcile`, `push`, `adherence`, etc.).
- **Local-first**: sem servidor externo, roda 100% no terminal.
- **Determinístico**: não introduzir LLM na UI. A prescrição continua vindo do motor.

## 3) Mapeamento: Comando CLI -> Tela UI

| Comando (CLI/Facade) | Tela UI | Tipo |
|---|---|---|
| `info`, `model` | **Dashboard** | Leitura |
| `build` | **Plano Semanal** | Mutável (confirma) |
| `check` / `today` | **Prontidão / Treino do Dia** | Leitura + Mutável |
| `reconcile` | **Plano Semanal / Dashboard** | Mutável/Leitura |
| `push` | **Publicar** | Externo (confirma + dry-run) |
| `daily` | **Diário** | Workflow mutável |
| `adherence`, `summary` | **Histórico/Aderência** | Leitura |
| `ftp-check`, `ftp-scan` | **FTP & Diagnóstico** | Leitura + Mutável |
| `recovery` | **Recuperação** | Leitura |

## 4) Wireframes ASCII

### 4.1 Dashboard (Tela Inicial)

```
┌─ HERMES COACH ──────────────────────────────────────────────────────────────┐
│ FTP: 265W  |  CTL: 72.4  |  ATL: 68.1  |  TSB: +4.3                       │
│ Plano: salvo em plan.json (atualizado há 2h)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ TREINO DE HOJE - Quarta-feira (29/10/2026)                                  │
│ [Sweetspot] 3x10' @88-92% FTP | 75 min | TSS 78 | Foco: Sustentado        │
│ Prontidão: Sem ajuste sugerido                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ PRÓXIMOS 3 DIAS                                                             │
│ Qui 30/10 | Z2 60m (TSS 39)                                                  │
│ Sex 31/10 | VO2 55m (TSS 76)                                                 │
│ Sáb 01/11 | Longo 90m (TSS 72)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ [1] Prontidão  [2] Ver Plano  [3] Gerar Plano  [4] Publicar  [q] Sair      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Plano Semanal

```
┌─ PLANO SEMANAL ─────────────────────────────────────────────────────────────┐
│ Período: 27/10 - 02/11 | TSS Total Estimado: 424 | Horas: ~7h 55m         │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────┤
│ SEG 27/10 │ TER 28/10 │ QUA 29/10 │ QUI 30/10 │ SEX 31/10 │ SÁB 01/11 │ DOM 02/11│
├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼─────────┤
│ Z2       │ Descanso │ Sweetspot│ Z2       │ VO2max   │ Longo    │ Rec/Z1   │
│ 60m TSS42│ --       │ 75m TSS78│ 60m TSS39│ 55m TSS76│ 90m TSS72│ 45m TSS28│
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘
│ [Enter] Ver treino  [G] Gerar/Regerar  [R] Reconciliar  [Esc] Voltar       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Prontidão / Treino do Dia

```
┌─ PRONTIDÃO & TREINO DO DIA ────────────────────────────────────────────────┐
│ Sessão atual: Sweetspot 3x10' @88-92% FTP                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ AVALIAÇÃO                                                                 │
│ Estado: elegível | Motivo: prontidão adequada                                │
│ Eixos observados: sono ok | carga recente ok | percepção ok                  │
│ Cobertura: 86% (6/7)                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ PROPOSTA                                                                    │
│ Nenhum ajuste sugerido pela leitura de prontidão                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ [A] Aplicar ajuste (se houver proposta)  [D] Dry-run  [Esc] Voltar         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Publicar no Intervals.icu

```
┌─ PUBLICAR ──────────────────────────────────────────────────────────────────┐
│ Etapa 1/2: Simulação (dry-run)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ $ python3 src/training_plan.py push --dry-run                               │
│ ...                                                                          │
│ Eventos a sincronizar: 7                                                     │
│ [VAR-03] Sanity check: OK (sem bloqueios)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Etapa 2/2: Confirmação                                                       │
│ [!] Isso irá PUBLICAR no calendário do Intervals.icu                        │
│                                                                              │
│ [S] PUBLICAR AGORA  [N] Cancelar  [Esc] Voltar                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.5 Histórico / Aderência

```
┌─ ADERÊNCIA (últimos 45 dias) ───────────────────────────────────────────────┐
│ Semana    | Feito | Perdido | Pendente | %                                     │
├───────────┼───────┼─────────┼──────────┼─────────────────────────────────────┤
│ 2026-W43  | 5     | 0       | 0        | 100%                                  │
│ 2026-W44  | 4     | 1       | 0        | 80%                                   │
│ 2026-W45  | 5     | 0       | 0        | 100%                                  │
├───────────┴───────┴─────────┴──────────┴─────────────────────────────────────┤
│ Total: 14 feito / 1 perdido / 0 pendente -> 93% dos ocorridos              │
│ [Esc] Voltar                                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5) Navegação e Atalhos

| Atalho | Ação |
|---|---|
| `1-9` | Navegação entre telas principais |
| `h` / `Home` | Voltar ao Dashboard |
| `p` | Ir direto para **Publicar** |
| `t` | Ir direto para **Treino/Prontidão** |
| `g` | **Gerar plano** (`build`) |
| `r` | **Reconciliar** |
| `d` | **Diário** (`daily`) |
| `q` / `Esc` | Sair / Voltar |
| `?` | Ajuda com atalhos |

## 6) Estrutura de Arquivos Proposta

```text
src/ui/
├── __init__.py
├── app.py           # Classe HermesCoachApp(TextualApp)
├── constants.py     # Cores, ícones, textos
├── utils.py         # Helpers: get_app(), load_dashboard_data(), etc.
├── screens/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── plan_week.py
│   ├── today.py
│   ├── readiness.py
│   ├── publish.py
│   ├── daily.py
│   ├── adherence.py
│   ├── ftp_diag.py
│   └── recovery.py
└── widgets/
    ├── __init__.py
    ├── metric_card.py
    ├── week_grid.py
    └── workout_card.py
```

## 7) Dependências

Adicionar ao `requirements.txt` (ou instalar localmente):

```text
textual>=0.80,<1.0
rich>=13.7
```

Ambos são estáveis, bem documentados e se integram bem com Python puro.

## 8) Validação Inicial

Antes de integrar, validar:

- [ ] Conseguimos ler `plan.json` sem quebrar se não existir
- [ ] `TSB/CTL/ATL` vindos do `model`/`info` batem com o CLI
- [ ] `push --dry-run` funciona igual ao CLI
- [ ] `check` respeita a lógica de prontidão atual
- [ ] Confirmações idênticas ao `hermes_agent.py`
- [ ] Não chamamos `src/training_plan.py` de forma direta sem passar pelos mesmos fluxos

## 9) Estado em 29/10/2026

Implementado em `src/ui/` e executado por `scripts/hermes_tui.py`:

- dashboard com FTP, VO₂, CTL/ATL/TSB e PMC;
- calendário mensal/semanal com plano, histórico do Intervals e detalhe de dia;
- detalhe de atividades com streams reais de potência, FC e cadência;
- prontidão visual com cobertura de eixos e recomendações informativas.

As ações mutáveis descritas neste esboço permanecem pendentes. Elas deverão usar
somente `scripts/hermes_agent.py`, com dry-run e confirmação, sem acesso mutável
direto pela UI. O manual operacional é [`docs/MANUAL-TUI.md`](../MANUAL-TUI.md)
e o backlog canônico é o item #65 do `docs/ROADMAP.md`.

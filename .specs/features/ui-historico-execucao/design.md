# Histórico planejado e execução em outra data — Design

**Spec:** `.specs/features/ui-historico-execucao/spec.md`
**Status:** Proposto

## Architecture Overview

Consultar plano local, eventos Hermes e atividades no intervalo necessário;
traduzir os dados externos na borda e projetar uma coleção por dia que preserve
todas as prescrições e atividades, com vínculos explícitos por ID. Renderizar
essa projeção no calendário, detalhe e resumo semanal. A projeção é somente
leitura e nunca modifica `plan.json` ou o provider.

### Alternativas

1. **Projeção de leitura com plano local + eventos remotos (recomendada):**
   recupera o histórico já publicado e identifica sua origem; exige tratar
   indisponibilidade do provider e estruturas de treino não suportadas.
2. **Arquivar planos em cada build:** preserva futuros históricos offline, mas
   sozinho não recupera 02/11 e acrescenta persistência e migração.
3. **Usar somente eventos remotos:** recupera eventos publicados, mas perde
   planos locais não publicados e prejudica o funcionamento local-first.

## Code Reuse Analysis

| Componente | Local | Uso |
| --- | --- | --- |
| Provider / adapter | `src/provider.py`, `src/intervals_adapter.py` | Consulta e tradução do provider. |
| Projeções de revisão | `src/ui/training_review.py` | Totais e comparações factuais. |
| Calendário e detalhe | `src/ui/screens/calendar.py`, `src/ui/screens/calendar_detail.py` | Exibição e navegação existentes. |

## Components

- Adaptador: expor identidade de evento, vínculo, origem e estrutura de treino
  sem converter campos ausentes em dados fictícios.
- Projeção pura: unir fontes por identidade, distinguir dia prescrito de dia
  realizado e deduplicar apenas quando o evento identifica a atividade pareada.
- Visualização: mostrar procedência, vínculos e disponibilidade; manter totais
  por dia efetivo e não suprimir atividades diferentes do mesmo dia.
- Perfil histórico: interpretar somente passos estruturados suportados pelo
  provider; nunca inferir potência a partir do nome ou da descrição livre.

## Data Models

A projeção deve manter coleções de eventos e atividades por dia, IDs de evento
e atividade, data planejada, data efetiva e indicação de origem. Prescrições
locais e remotas divergentes permanecem identificáveis; a local tem prioridade
para apresentação sem descartar a divergência.

## Error Handling Strategy

| Cenário | Tratamento |
| --- | --- |
| Provider indisponível | Manter plano local visível e sinalizar ausência do histórico remoto. |
| Estrutura não suportada | Mostrar perfil indisponível, sem fabricar parâmetros. |
| Vínculo ausente ou ambíguo | Não associar nem suprimir atividades por semelhança. |

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| --- | --- | --- | --- |
| Um treino e uma atividade por dia | `src/ui/screens/calendar.py` | Perda silenciosa de outros registros. | Projeção usa coleções e testes com múltiplos itens. |
| Repetição de consultas e streams | `src/ui/screens/calendar.py` | Latência e chamadas extras ao provider. | Limitar janela e reutilizar cache de streams existente; resumo não faz batch-fetch. |
| Interpretação de formato externo | `src/intervals_adapter.py` | Gráfico incorreto com estruturas não suportadas. | Aceitar apenas passos explicitamente reconhecidos e testar falhas. |
| Dados de teste reais e preferências locais | `tests/test_application.py` | Suíte varia com arquivos locais. | Isolar fixtures sem alterar dados de usuário. |

## Tech Decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Identidade | Usar vínculo explícito do evento ao ID da atividade. | Nome e data não comprovam identidade. |
| Históricos | Combinar local e remoto sem escrever no plano. | Recupera o caso atual e mantém local-first. |

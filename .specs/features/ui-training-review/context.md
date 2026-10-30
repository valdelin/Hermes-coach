# Revisão de treino na TUI — Context

**Gathered:** 2026-10-30
**Spec:** `.specs/features/ui-training-review/spec.md`
**Status:** Ready for design

## Feature Boundary

Entregar leitura de treino planejado, comparação factual plano × realizado e
resumo semanal na TUI. A entrega não altera plano, calendário remoto ou regras
de prescrição.

## Implementation Decisions

### Comparação do dia

- Exibir Planejado e Realizado lado a lado.
- Comparar duração e TSS, com potência média ou normalizada apenas quando a
  atividade a fornecer.
- Mostrar diferenças numéricas. Não classificar adaptação ou cumprimento
  fisiológico.

### Status semanal

- Plano sem atividade antes de hoje é perdido.
- Plano sem atividade hoje ou no futuro é pendente.
- Atividade sem plano é extra.

### Arquitetura da leitura

- Extrair projeções puras compartilhadas em `src/ui/`.
- As telas ficam responsáveis por obter dados e renderizar projeções.
- A mesma classificação de zona deve alimentar detalhe e resumo semanal.

### Dados remotos incompletos

- A distribuição realizada só existe com streams reais de potência.
- Falha ou ausência de streams mostra indisponível, sem estimativa.
- Dados locais do plano e demais métricas continuam visíveis.

## Agent's Discretion

- Densidade exata das colunas e barras no terminal.
- Nomes internos das funções e dataclasses de projeção.
- Ordem visual dos blocos planejados e das zonas.

## Specific References

- Calendário inspirado no Intervals.icu, com cards compactos e semana como
  unidade operacional.

## Deferred Ideas

- Unificar o mini-gráfico do card e o gráfico detalhado.
- Sobrepor séries temporais planejadas e reais.

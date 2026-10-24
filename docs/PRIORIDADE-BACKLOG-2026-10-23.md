# Priorização do backlog aberto — 2026-10-23

> Recorte: itens abertos no `docs/ROADMAP.md`, o único bug aberto em
> `docs/KNOWN_ISSUES.md` e as melhorias VAR-01..03. Isto é uma tabela de decisão;
> não autoriza implementação, publicação no Intervals ou mudança fisiológica.

## Critérios

| Critério | Pergunta |
|---|---|
| Impacto no atleta | Melhora segurança, aderência ou utilidade no fluxo real atual? |
| Integridade | Evita erro silencioso, plano incorreto ou publicação indevida? |
| Evidência | Há caso observado/teste offline ou ainda depende de hipótese/treinador? |
| Dependência | Pode ser feito localmente ou bloqueia em portal, servidor, segundo atleta ou treinador? |
| Esforço | Baixo, médio ou alto; não substitui os critérios anteriores. |

**Prioridades:** P0 = decidir/validar agora; P1 = próximo ciclo do motor; P2 =
piloto/UX após P0-P1; P3 = produto futuro; P4 = SaaS/escala. “Hold” = não gastar
tempo até surgir gatilho concreto.

## Matriz de prioridade

| Prioridade | ID | Item | Impacto / evidência | Dependência | Recomendação |
|---|---|---|---|---|---|
| **P0 concluído localmente** | DUR-01 | Cada atleta configura `MAX_WORKOUT_DURATION_MINUTES` por treino; faixa indoor **30–180 min**, default/teto 180; independente de `WEEKLY_HOURS` | Configuração ausente/inválida mantém 180; Threshold/VO₂ compactam sem perder foco/potência; sessão de hoje é preservada | Nenhuma | Verificação independente PASS: 8 testes, sensor 3/3 mutantes mortos, `validate_state` verde. Pendente apenas de commit explícito. |
| **P0 concluído localmente** | VAR-01 | Rotação de variantes por semana | Problema observado: duas semanas parecidas. Protótipo reduziu repetições de assinatura em 14d de **15/20 para 10/20**; implementação usa semana ISO | Nenhuma | Verificação independente PASS: 1.557 testes e sensor matou remoção do offset. Medir 2–4 semanas reais antes de VAR-02 |
| **P0** | VAR-03 | Sanity check pré-push | Barreira de integridade; protótipo detectou qualidade em D-1 de prova | **implementado** (`src/plan_sanity.py`, integrado ao `push`) | Alerta/bloqueio: SAN-02/SAN-03/SAN-04/SAN-05/SAN-06; sem auto-correção. Testes em `tests/test_plan_sanity.py` |
| **P1** | VAR-02 | Variação baseada em histórico executado | Conceito correto, mas o protótipo atual não superou VAR-01 (**10/20**) porque há só 3 variantes/foco | VAR-01; ampliar catálogo ou refinar política | Não implementar antes de medir VAR-01 em plano real; decidir se vale adicionar variantes primeiro |
| **P1** | PROG-2 | Guardrails de progressão | Evita inventar limiares para adesão e sessões incompletas | Respostas Q1–Q4 do treinador | Coletar decisões do treinador; sem código até então |
| **P1** | PROG-3 | Integrar evidência de execução/readiness/fase/rampa | É a ponte para que o próximo bloco responda ao que foi realmente feito | PROG-2 e seams de key-workout/recovery-week | Especificar depois das respostas do treinador; não confundir com VAR-02 |
| **P1** | #2 / AGENT-2 | Notificações | Aumenta aderência no produto já funcional; não altera prescrição | Escolha de canal e credenciais | Começar por notificação read-only; sem mutação por mensagem |
| **P2** | #61 | Revisão do `hermes_agent.py` | Protege a futura interface de automação; suíte já existe | Code review | Fazer antes de tornar agente interface oficial |
| **P2** | #22 / AGENT-3 | “Próximo passo” pós-treino e Q&A read-only | UX útil, mas depende de decisões/rationale mais estáveis | Decision ledger futuro | Limitar a explicação read-only; não criar chat autor de plano |
| **P2** | #23 + #35 | Portal e validação com 2º atleta | Maior aprendizado externo: PMC/TSB e decisões hoje só foram vistos em um atleta | Portal/OAuth e voluntário | Tratar como piloto: critério de sucesso explícito, consentimento e dados reais |
| **P2** | #1 | Atividade “fantasma” do Intervals | Cosmético; não altera CTL/ATL/TSB nem reconcile | Limitação da API do Intervals | **Hold**: atacar só quando houver folga ou reclamação recorrente; sempre com `--dry-run` |
| **P3** | #9, #10, #15 | Perfil de esforço, nível do atleta, wellness objetivo | Podem melhorar personalização, mas ainda precisam de critério/treinador | Validação com treinador | Não colocar heurísticas novas no motor sem decisão explícita |
| **P3** | #18, #30 | Corrida e multi-esporte | Alto alcance, mas altera contratos (`sport`, carga compartilhada, eventos) | Modelo multi-esporte e testes | Começar pelo contrato de domínio, não por geração de workout |
| **P3** | #28, #29, AGENT-4 | Race Recon, Coach+, proposta de mutação | Diferenciais de produto; risco se agente puder mutar sem contrato | Decision ledger, ProposedChange, portal | Ledger antes de interface conversacional; motor continua autor |
| **P4** | #7, #8, #11, #12 | PWA, multi-atleta, catálogo, app comercial | Produto/mercado; não corrige o motor atual | Pesquisa de produto e piloto | Só após validar fluxo com atleta externo |
| **P4** | #13, #24–#27, AGENT-5 | MCP, banco, API, worker, pagamento, hub | Infra/SaaS; alto custo operacional e de segurança | Portal, modelo de negócio, threat model, evals | Contrato de ferramentas + ledger antes de MCP; não começar pelo transporte |

## Sequência recomendada

```text
fechar MAX_WORKOUT_DURATION
  -> VAR-01
  -> VAR-03
  -> respostas do treinador (PROG-2)
  -> PROG-3
  -> VAR-02 (somente se VAR-01 não bastar)
  -> notificações read-only
  -> revisão AGENT-0
  -> portal piloto + 2º atleta
```

## Decisões explícitas de não-prioridade

- **Não** implementar VAR-02 agora: a simulação não mostrou ganho sobre VAR-01 com o
  catálogo atual.
- **Não** fazer limpeza de fantasmas (#1) agora: impacto cosmético, mitigação manual
  segura e causa no Intervals.
- **Não** iniciar MCP/Coach+/SaaS antes de `DecisionRecord`/`RuleRef` e do contrato de
  ferramentas; MCP é distribuição, não o motor.
- **Não** inserir novos thresholds fisiológicos em PROG-2/15 sem decisão do treinador.

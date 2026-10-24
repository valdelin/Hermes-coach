# STATE

## Decisions

### AD-001
- **Decision**: Métricas fisiológicas observadas com histórico próprio usarão repositories dedicados e provider-independent; o primeiro é VO₂max, enquanto FTP continua em `FtpHistory`.
- **Reason**: O histórico precisa sobreviver à substituição do Intervals.icu e preservar revisões/provenance sem transformar `TrainingSnapshot` em fonte canônica.
- **Trade-off**: Há mais um arquivo e contrato local agora; métricas wellness adicionais exigem decisão explícita antes de entrarem no modelo.
- **Scope**: Histórico fisiológico, relatórios e futura persistência PaaS.
- **Date**: 2026-10-22
- **Status**: active

### AD-002
- **Decision**: Treinos indoor têm teto configurável de 30 a 180 minutos, com default e máximo de 180; somente intenção `endurance_low_intensity` pode se aproximar desse teto por padrão. O operador quer preferência de 60 min, mas a aplicação global está pendente de design por conflitar com taper, recuperação e orçamento.
- **Reason**: Limitar exposição térmica/logística do trainer e impedir que disponibilidade semanal escale VO₂, limiar ou Sweet Spot para sessões longas sem intenção explícita.
- **Trade-off**: O atleta com disponibilidade/objetivo maior precisa dividir o volume em sessões ou usar treino livre outdoor; impor 60 min globalmente hoje converte qualidade em recuperação em cenários de baixo orçamento.
- **Scope**: Configuração de duração máxima, gerador de planos indoor, validação pré-push e futuros templates longos.
- **Date**: 2026-10-23
- **Status**: active

## Handoff

### VAR-03
- **Decision**: Adicionar sanity check pré-push (alerta + bloqueio, sem auto-correção). Integrado ao `training_plan.py push` antes de mutações. Em `--dry-run` apenas reporta.
- **Rules**: SAN-02 (teto de duração), SAN-03 (qualidade em D-0/D-1/D-2 de prova), SAN-04 (estrutura mínima), SAN-05 (piso de zona), SAN-06 (alerta para `MIN_REGULAR_DURATION_MINUTES`).
- **Reason**: Barreira de integridade para evitar publicar sessões inconsistentes com as regras vigentes.
- **Trade-off**: Pode bloquear um `push` legítimo em casos ambíguos; decisão explícita por código, sem reescrita automática.

### NOT-01/02/03 (Notifications - Telegram)
- **Decision**: Interface `Notifier` com `NullNotifier` por padrão; `TelegramNotifier` via Bot API (stdlib, best-effort). Nunca quebra `push`/fluxos.
- **Config**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `NOTIFY_ENABLED`.
- **Integration**: Notificação em `push` bem-sucedido com contagens básicas.
- **Reason**: Feedback imediato sem dependências pesadas.
- **Trade-off**: Primeiro canal só Telegram; sem fila/retry complexo.

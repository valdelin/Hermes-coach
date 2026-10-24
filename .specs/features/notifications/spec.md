# Feature: Notifications (Telegram) — #2

## Objetivo
Enviar notificações não-bloqueantes sobre ações do Hermes Coach (push publicado, daily concluído, erros relevantes). Primeiro canal: Telegram. Arquitetura extensível para e-mail/WhatsApp.

## Requisitos

### P1: Arquitetura
- **NOT-01**: Criar interface `Notifier` com método `send(title: str, message: str, level: str = "info") -> bool`
- **NOT-02**: Implementação `TelegramNotifier` usando Bot API via `urllib.request` (stdlib)
- **NOT-03**: `Notifier` deve ser best-effort: nunca lançar exceção que quebre `push`/`daily`. Erros devem ser logados e ignorados.

### P2: Configuração
- **NOT-04**: Config via `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Se ausentes, notificador desativado.
- **NOT-05**: `NOTIFY_ENABLED` opcional (default true quando credenciais presentes). `NOTIFY_CHANNELS` opcional para filtrar.

### P3: Integração
- **NOT-06**: Integrar em `training_plan.py push` após publicação bem-sucedida (resumir eventos publicados/orfãos/removidos)
- **NOT-07**: Integrar em `scripts/daily_reconcile.sh` ou via orquestrador `daily` (opcional mas desejável). Focar primeiro em `push`.
- **NOT-08**: Mensagem concisa em PT-BR com dados essenciais (datas, contagens, TSS se disponível)

### P4: Testes
- **NOT-09**: Testes unitários com mock HTTP (sem chamadas reais)
- **NOT-10**: Teste de falha não quebra o fluxo

## Não objetivos
- Webhook complexo, fila, retry agressivo
- E-mail/WhatsApp nesta primeira iteração
- Histórico de notificações

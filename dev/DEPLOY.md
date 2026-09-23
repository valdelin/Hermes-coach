# Deploy — Hermes Coach em container (Oracle Cloud Free Tier)

Guia para colocar o sistema em um container no **Oracle Cloud Infrastructure
(OCI) Always Free**. Estrutura:

| Etapa | Onde | Quem faz |
|---|---|---|
| Containerizar + testar local | Máquina local | terminal |
| Conta + instância Oracle | Console OCI | manual (com roteiro abaixo) |
| Provisionar VPS + deploy | Terminal → SSH | terminal |
| Validar + monitorar | Terminal + Intervals.icu | terminal |

Referência de console: wiki do
[zwift-offline](https://github.com/oldnapalm/zwift-offline/wiki/Creating-a-server-on-Oracle-Cloud-Free-Tier)
— usamos só a parte de **criação de instância**; as portas abertas, PuTTY,
swap e reverse proxy daquele guia **não se aplicam aqui**.

## O que roda no container

Um único serviço `coach`, **sempre ligado**, com o cron **supercronic** como
processo 1. À meia-noite (fuso `America/Sao_Paulo`) ele roda o mesmo fluxo do
timer systemd local:

```
reconcile --show
push --start $(date +%F)
```

Só o `data/` persiste (`.env`, `plan.json`, `logs/`). Nenhuma credencial entra
na imagem.

## 0. Containerizar e testar local

```bash
docker build -t hermes-coach:latest .
mkdir -p data/logs
cp plan.json data/plan.json          # seed de estado (se o plan.json existe)
docker compose up -d --build
```

Sanidade (se um destes falhar, não prossiga):

```bash
docker compose exec coach python3 src/training_plan.py info          # conecta no Intervals
docker compose exec coach python3 src/training_plan.py reconcile --show
docker compose logs coach
docker run --rm --entrypoint printenv hermes-coach:latest | grep -E 'INTERVALS|API_KEY'  # nada
```

Apagar lixo de teste **antes** de commitar: `docker compose down` e remover
`data/`.

## 1. Conta + instância Oracle (console)

1. Conta em <https://www.oracle.com/cloud/free/> (exige cartão para verificação
   de identidade; a instância abaixo permanece **Always Free**).
2. **Gerar chave SSH localmente** (a privada não sai da sua máquina):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/hermes_vps -C "hermes-coach-vps"
   ```
3. No console: **Compute → Instances → Create instance**, com:
   - **Image**: Ubuntu **24.04** (imagem compatível com ARM).
   - **Shape**: `VM.Standard.A1.Flex` (*Always Free*), **2 OCPU / 12 GB RAM**
     (ou 1 OCPU / 6 GB para folgar na cota).
   - **SSH keys**: upload do arquivo `hermes_vps.pub`.
   - **Network**: VCN default (subnet pública). Não precisa alterar a security
     list — o padrão já libera **SSH (22)**; nenhuma outra porta é necessária.
4. Anote o **IP público** da instância.

> A criação de conta OCI pode demorar ou exigir retries; em caso de
> **"out of host capacity"** no shape A1, tente outra região ou aguarde e
> repita — é o comportamento conhecido do free tier.
>
> O Always Free da Oracle foi cortado em **15/06/2026** (de 4 OCPU/24 GB para
> **2 OCPU/12 GB**). Contas PAYG mantêm a cota antiga, mas não é necessário.

## 2. Provisionar a VPS (SSH)

```bash
IP=<ip_publico>
ssh -i ~/.ssh/hermes_vps ubuntu@$IP

# dentro da VPS:
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker ubuntu
```

Roundtrip SSH (para `sg`-containers não precisarem de senha a cada chamada):

```bash
eval "$(ssh-agent)" && ssh-add ~/.ssh/hermes_vps
```

**Deploy key read-only** do repo privado: em *Settings → Deploy keys* no GitHub,
adicionar a chave pública (`hermes_vps.pub`), permissão **read-only**.

```bash
# dentro da VPS (com a chave no agent):
ssh-keyscan github.com >> ~/.ssh/known_hosts
git clone --depth 1 git@github.com:valdelin/Hermes-coach.git /opt/hermes-coach
cd /opt/hermes-coach
```

## 3. Deploy

```bash
# na máquina local:
scp -i ~/.ssh/hermes_vps .env          ubuntu@$IP:/opt/hermes-coach/.env
scp -i ~/.ssh/hermes_vps plan.json     ubuntu@$IP:/opt/hermes-coach/plan.json
scp -i ~/.ssh/hermes_vps -r logs/      ubuntu@$IP:/opt/hermes-coach/data/logs/
```

> Se for o primeiro deploy, criar `data/` na VPS:
> `mkdir -p /opt/hermes-coach/data/logs`

```bash
# dentro da VPS:
sudo chmod 600 .env
mkdir -p data/logs
cp plan.json data/plan.json
docker compose build && docker compose up -d
docker compose ps
```

## 4. Validar

```bash
docker compose exec coach python3 src/training_plan.py info
docker compose exec coach python3 src/training_plan.py reconcile --show
```

- O `reconcile --show` deve dizer que não há treinos perdidos.
- Conferir no calendário do Intervals.icu que o treino de hoje está publicado.
- Observar o primeiro job de meia-noite:
  ```bash
  docker compose logs -f
  cat data/logs/daily_reconcile.log
  ```

> A API do Intervals.icu não usa allowlist de IP — qualquer IP com a chave
> válida funciona. Se `reconcile` falhar aqui, o problema é de rede/chave, não
> de licença do servidor.

## 5. Atualizar o container (novas versões)

```bash
cd /opt/hermes-coach
git pull
docker compose build && docker compose up -d
```

## Segurança / backup / rollback

- **Imagem sem segredo**: `.dockerignore` exclui `.env*`, `plan.json`,
  `logs/`, `data/`. Conferência no passo 0.
- **Deploy key read-only**: a VPS só consegue `git fetch`, nunca push.
- **Único ponto de monitore**: o job não notifica na VPS (sem desktop). Rede de
  segurança: conferir `info`/calendário do dia seguinte. O bot de Telegram
  (issue #2) vira o alerta real.
- **Backup**: `data/` é o único estado — `rsync`/snapshot dele basta.
- **Rollback**: `docker compose down` e o setup local/systemd da máquina
  original continua como fallback.
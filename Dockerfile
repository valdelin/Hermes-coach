FROM python:3.12-slim

# supercronic (cron confiavel para containers): binario estatico, verificacao
# SHA-1 do proprio upstream (release notes v0.2.49).
ARG TARGETARCH=amd64
ARG SUPERCRONIC_VERSION=v0.2.49

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && curl -fsSLo /usr/local/bin/supercronic "$SUPERCRONIC_URL" \
 && case "$TARGETARCH" in \
      amd64) echo "e63c11a9726b775a6a11801e81af4f3fb926aa68  /usr/local/bin/supercronic" | sha1sum -c - ;; \
      arm64) echo "0b6c5bb743e0b0dafed1132198c81807927ac413  /usr/local/bin/supercronic" | sha1sum -c - ;; \
      *) echo "arch nao suportado: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && chmod +x /usr/local/bin/supercronic \
 && apt-get purge -y curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY crontab ./crontab

CMD ["supercronic", "-passthrough-logs", "/app/crontab"]
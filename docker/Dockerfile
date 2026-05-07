FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    tar \
    gzip \
    gpg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY scripts/ ./scripts/
COPY tests/ ./tests/

RUN pip install --no-cache-dir pytest && \
    chmod +x scripts/backup.sh scripts/restore.sh

ENV BACKUP_DIR=/backups
VOLUME ["/backups"]

ENTRYPOINT ["bash", "scripts/backup.sh"]
# Multi-stage build — python:3.11.9-slim, non-root user "bot" (Section 18)
FROM python:3.11.9-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11.9-slim

RUN groupadd --system bot && useradd --system --gid bot --create-home bot \
 && apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY main.py pyproject.toml ./
COPY bot ./bot
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY tests ./tests

RUN mkdir -p /app/data && chown -R bot:bot /app
USER bot

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

ENTRYPOINT ["python", "main.py"]

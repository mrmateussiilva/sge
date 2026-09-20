# ── Stage 1: Build Frontend (React + Vite) ──
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Backend Django (Python) ──
FROM python:3.13-slim

WORKDIR /app

# Baixa e instala o Litestream (para replicação do SQLite)
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz && rm /tmp/litestream.tar.gz

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p /app/data && chmod +x entrypoint.sh

EXPOSE ${PORT:-8000}

ENTRYPOINT ["./entrypoint.sh"]

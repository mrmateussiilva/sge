FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p /app/data && chmod +x entrypoint.sh

EXPOSE ${PORT:-8000}

ENTRYPOINT ["./entrypoint.sh"]

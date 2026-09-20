#!/bin/bash
set -e

# Se a URL de réplica estiver configurada e o banco local ainda não existir, restaura do backup
if [ -n "$LITESTREAM_REPLICA_URL" ] && [ ! -f /app/data/db.sqlite3 ]; then
  echo "[Litestream] Restaurando banco de dados a partir da réplica..."
  litestream restore -if-replica-exists -config /app/litestream.yml /app/data/db.sqlite3 || true
fi

uv run python manage.py migrate --noinput

uv run python manage.py createsuperuser \
    --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || true

uv run python manage.py collectstatic --noinput

# Se Litestream estiver configurado, roda gunicorn encapsulado no replicate
if [ -n "$LITESTREAM_REPLICA_URL" ]; then
  echo "[Litestream] Iniciando replicação contínua para o SQLite..."
  exec litestream replicate -config /app/litestream.yml -exec "uv run gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3"
else
  exec uv run gunicorn core.wsgi:application --bind 0.0.0.0:"$PORT" --workers 3
fi

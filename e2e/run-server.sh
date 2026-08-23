#!/usr/bin/env bash
set -euo pipefail

E2E_DB="${DJANGO_DB_NAME:-/tmp/sge-final-e2e.sqlite3}"
E2E_PASSWORD="${E2E_PASSWORD:-sge-e2e-local-2026}"

rm -f "$E2E_DB" "$E2E_DB-shm" "$E2E_DB-wal"

export DJANGO_DEBUG=True
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-sge-e2e-secret-key-local}"
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-127.0.0.1,localhost}"
export OMIE_ENCRYPTION_KEY="${OMIE_ENCRYPTION_KEY:-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=}"
export DJANGO_DB_NAME="$E2E_DB"
export E2E_PASSWORD

uv run python manage.py migrate --noinput
uv run python manage.py seed_e2e
exec uv run python manage.py runserver 127.0.0.1:8001 --noreload

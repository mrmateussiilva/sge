#!/bin/bash
set -e

uv run python manage.py migrate --noinput

uv run python manage.py createsuperuser \
    --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null || true

uv run python manage.py collectstatic --noinput

uv run gunicorn core.wsgi:application --bind 0.0.0.0:"$PORT" --workers 3

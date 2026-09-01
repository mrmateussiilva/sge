#!/usr/bin/env bash

# Backup consistente do SQLite usado pelo container do SGE.
# Pode ser executado manualmente ou pelo systemd na VPS.

set -Eeuo pipefail

umask 077

PROJECT_DIR="${SGE_PROJECT_DIR:-$(pwd)}"
BACKUP_DIR="${SGE_BACKUP_DIR:-/var/backups/sge}"
SERVICE="${SGE_SERVICE:-sge}"
DB_PATH="${SGE_DB_PATH:-/app/data/db.sqlite3}"
DAILY_RETENTION_DAYS="${SGE_DAILY_RETENTION_DAYS:-30}"
HOURLY_RETENTION_DAYS="${SGE_HOURLY_RETENTION_DAYS:-7}"
MONTHLY_RETENTION_DAYS="${SGE_MONTHLY_RETENTION_DAYS:-365}"

die() {
    printf '[ERRO] %s\n' "$1" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Comando obrigatório não encontrado: $1"
}

cd "$PROJECT_DIR" || die "Não foi possível acessar SGE_PROJECT_DIR=$PROJECT_DIR"

[[ -f docker-compose.yml || -f compose.yml ]] || die "docker-compose.yml/compose.yml não encontrado em $PROJECT_DIR"

require_command docker
require_command gzip
require_command sha256sum
require_command flock

mkdir -p "$BACKUP_DIR/hourly" "$BACKUP_DIR/daily" "$BACKUP_DIR/monthly"

LOCK_FILE="$BACKUP_DIR/.backup.lock"
exec 9>"$LOCK_FILE"
flock -n 9 || die 'Já existe outro backup em execução.'

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
CONTAINER_TMP="/tmp/sge-backup-${RUN_ID}.sqlite3"
HOST_TMP_DIR="$(mktemp -d "$BACKUP_DIR/.run-${RUN_ID}.XXXXXX")"
REMOTE_TMP_CREATED=0

cleanup() {
    if [[ "$REMOTE_TMP_CREATED" -eq 1 ]]; then
        docker compose exec -T "$SERVICE" rm -f "$CONTAINER_TMP" >/dev/null 2>&1 || true
    fi
    rm -rf "$HOST_TMP_DIR"
}
trap cleanup EXIT

printf '[INFO] Gerando cópia consistente do SQLite...\n'

REMOTE_TMP_CREATED=1
docker compose exec -T "$SERVICE" python - "$DB_PATH" "$CONTAINER_TMP" <<'PY'
import sqlite3
import sys

source_path, destination_path = sys.argv[1:]
source = sqlite3.connect(source_path, timeout=60)
destination = sqlite3.connect(destination_path)

try:
    source.backup(destination, pages=256)
    destination.commit()
finally:
    destination.close()
    source.close()

check = sqlite3.connect(destination_path, timeout=60)
try:
    result = check.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    check.close()

if result != "ok":
    raise SystemExit(f"integrity_check falhou: {result}")
PY

docker compose cp "$SERVICE:$CONTAINER_TMP" "$HOST_TMP_DIR/database.sqlite3"
[[ -s "$HOST_TMP_DIR/database.sqlite3" ]] || die 'O arquivo de backup ficou vazio.'

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
FILENAME="sge-${TIMESTAMP}.sqlite3.gz"
ARCHIVE="$BACKUP_DIR/hourly/$FILENAME"
TEMP_ARCHIVE="$HOST_TMP_DIR/$FILENAME"

gzip -9 -c "$HOST_TMP_DIR/database.sqlite3" > "$TEMP_ARCHIVE"
mv "$TEMP_ARCHIVE" "$ARCHIVE"
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

SIZE_BYTES="$(wc -c < "$ARCHIVE" | tr -d '[:space:]')"
printf '{"arquivo":"%s","criado_em":"%s","banco":"%s","tamanho_bytes":%s,"integrity_check":"ok"}\n' \
    "$FILENAME" "$(date --iso-8601=seconds)" "$DB_PATH" "$SIZE_BYTES" > "$ARCHIVE.json"

link_snapshot() {
    local destination_dir="$1"
    ln -f "$ARCHIVE" "$destination_dir/$FILENAME"
    ln -f "$ARCHIVE.sha256" "$destination_dir/$FILENAME.sha256"
    ln -f "$ARCHIVE.json" "$destination_dir/$FILENAME.json"
}

# O primeiro backup executado em cada dia vira a cópia diária.
TODAY="$(date +%Y%m%d)"
if [[ -z "$(find "$BACKUP_DIR/daily" -maxdepth 1 -type f -name "sge-${TODAY}-*.sqlite3.gz" -print -quit)" ]]; then
    link_snapshot "$BACKUP_DIR/daily"
fi

# O primeiro backup executado em cada mês vira a cópia mensal.
MONTH="$(date +%Y%m)"
if [[ -z "$(find "$BACKUP_DIR/monthly" -maxdepth 1 -type f -name "sge-${MONTH}??-*.sqlite3.gz" -print -quit)" ]]; then
    link_snapshot "$BACKUP_DIR/monthly"
fi

prune_archives() {
    local directory="$1"
    local retention_days="$2"
    local archive_file

    while IFS= read -r -d '' archive_file; do
        rm -f "$archive_file" "$archive_file.sha256" "$archive_file.json"
    done < <(find "$directory" -maxdepth 1 -type f -name '*.sqlite3.gz' -mtime "+$((retention_days - 1))" -print0)
}

prune_archives "$BACKUP_DIR/hourly" "$HOURLY_RETENTION_DAYS"
prune_archives "$BACKUP_DIR/daily" "$DAILY_RETENTION_DAYS"
prune_archives "$BACKUP_DIR/monthly" "$MONTHLY_RETENTION_DAYS"

printf '[OK] Backup criado: %s (%s bytes)\n' "$ARCHIVE" "$SIZE_BYTES"

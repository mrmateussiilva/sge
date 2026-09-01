#!/usr/bin/env bash

# Restaura uma cópia local do banco SQLite do SGE.
# Uso deliberadamente explícito: SGE_CONFIRM_RESTORE=YES ./scripts/restore_sge.sh arquivo.gz

set -Eeuo pipefail

umask 077

# Quando instalado na VPS, reutiliza os mesmos parâmetros do timer.
if [[ -r /etc/sge/backup.env ]]; then
    set -a
    # shellcheck disable=SC1091
    source /etc/sge/backup.env
    set +a
fi

PROJECT_DIR="${SGE_PROJECT_DIR:-$(pwd)}"
SERVICE="${SGE_SERVICE:-sge}"
DB_PATH="${SGE_DB_PATH:-/app/data/db.sqlite3}"
ARCHIVE="${1:-}"
BACKUP_SCRIPT="${SGE_BACKUP_SCRIPT:-$(dirname "${BASH_SOURCE[0]}")/backup_sge.sh}"

die() {
    printf '[ERRO] %s\n' "$1" >&2
    exit 1
}

[[ "${SGE_CONFIRM_RESTORE:-}" == "YES" ]] || die 'Restauração bloqueada. Defina SGE_CONFIRM_RESTORE=YES para confirmar.'
[[ -n "$ARCHIVE" ]] || die 'Informe o caminho de um arquivo .sqlite3.gz.'
[[ -f "$ARCHIVE" ]] || die "Arquivo não encontrado: $ARCHIVE"

cd "$PROJECT_DIR" || die "Não foi possível acessar SGE_PROJECT_DIR=$PROJECT_DIR"
command -v docker >/dev/null 2>&1 || die 'Comando obrigatório não encontrado: docker'
command -v gzip >/dev/null 2>&1 || die 'Comando obrigatório não encontrado: gzip'

gzip -t "$ARCHIVE" || die 'O arquivo compactado está inválido.'

TEMP_DIR="$(mktemp -d /tmp/sge-restore.XXXXXX)"
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

RESTORE_DB="$TEMP_DIR/db.sqlite3"
gzip -dc "$ARCHIVE" > "$RESTORE_DB"

python3 - "$RESTORE_DB" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()

if result != "ok":
    raise SystemExit(f"integrity_check falhou: {result}")
PY

if [[ "${SGE_SKIP_PRE_RESTORE_BACKUP:-NO}" != "YES" ]]; then
    [[ -x "$BACKUP_SCRIPT" ]] || die "Script de backup pré-restauração não encontrado: $BACKUP_SCRIPT"
    printf '[INFO] Criando backup do banco atual antes da restauração...\n'
    "$BACKUP_SCRIPT"
fi

printf '[ATENÇÃO] O serviço %s será parado e o banco atual será substituído.\n' "$SERVICE"
printf '[INFO] O backup pré-restauração já foi criado em %s.\n' "${SGE_BACKUP_DIR:-/var/backups/sge}"

# O backup prévio mantém a reversão possível caso a cópia escolhida esteja incorreta.
SERVICE_STOPPED=0
restore_cleanup() {
    if [[ "$SERVICE_STOPPED" -eq 1 ]]; then
        docker compose start "$SERVICE" >/dev/null 2>&1 || true
    fi
    rm -rf "$TEMP_DIR"
}
trap restore_cleanup EXIT

docker compose stop "$SERVICE"
SERVICE_STOPPED=1
docker compose cp "$RESTORE_DB" "$SERVICE:$DB_PATH"
docker compose start "$SERVICE"
SERVICE_STOPPED=0

docker compose exec -T "$SERVICE" python - "$DB_PATH" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1], timeout=60)
try:
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()

if result != "ok":
    raise SystemExit(f"integrity_check falhou após restauração: {result}")
PY

printf '[OK] Banco restaurado. Verifique o health check e os dados da aplicação.\n'

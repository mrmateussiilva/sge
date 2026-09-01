#!/usr/bin/env bash

# Instala o backup local do SGE na VPS.
# Executar uma única vez, como root, depois de atualizar o checkout do projeto.

set -Eeuo pipefail

PROJECT_DIR="${1:-$(pwd)}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
    printf '[ERRO] Execute este instalador como root (sudo).\n' >&2
    exit 1
fi

[[ -f "$PROJECT_DIR/scripts/backup_sge.sh" ]] || {
    printf '[ERRO] Script de backup não encontrado em %s.\n' "$PROJECT_DIR" >&2
    exit 1
}
[[ -f "$PROJECT_DIR/deploy/systemd/sge-backup.service" ]] || {
    printf '[ERRO] Unidade systemd não encontrada no checkout.\n' >&2
    exit 1
}

install -d -m 700 /var/backups/sge/hourly /var/backups/sge/daily /var/backups/sge/monthly
install -d -m 755 /etc/sge

install -m 0750 "$PROJECT_DIR/scripts/backup_sge.sh" /usr/local/sbin/sge-backup
install -m 0750 "$PROJECT_DIR/scripts/restore_sge.sh" /usr/local/sbin/sge-restore
install -m 0644 "$PROJECT_DIR/deploy/systemd/sge-backup.service" /etc/systemd/system/sge-backup.service
install -m 0644 "$PROJECT_DIR/deploy/systemd/sge-backup.timer" /etc/systemd/system/sge-backup.timer

if [[ ! -f /etc/sge/backup.env ]]; then
    umask 077
    cat > /etc/sge/backup.env <<EOF
SGE_PROJECT_DIR=$PROJECT_DIR
SGE_BACKUP_DIR=/var/backups/sge
SGE_SERVICE=sge
SGE_DB_PATH=/app/data/db.sqlite3
SGE_HOURLY_RETENTION_DAYS=7
SGE_DAILY_RETENTION_DAYS=30
SGE_MONTHLY_RETENTION_DAYS=365
EOF
    chmod 600 /etc/sge/backup.env
else
    printf '[INFO] Preservado /etc/sge/backup.env existente.\n'
fi

systemctl daemon-reload
systemctl enable --now sge-backup.timer

printf '[OK] Backup do SGE instalado e agendado.\n'
systemctl status --no-pager sge-backup.timer || true

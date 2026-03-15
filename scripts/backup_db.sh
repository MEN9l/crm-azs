#!/bin/bash
# Бэкап БД CRM АЗС. Запуск с хоста: ./scripts/backup_db.sh
# Или из корня проекта: bash scripts/backup_db.sh
# Требует: docker compose с сервисом db (postgres)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/crm_azs_${TIMESTAMP}.sql"

cd "$PROJECT_DIR"
docker compose exec -T db pg_dump -U crm_user crm_azs > "$BACKUP_FILE"
echo "Backup saved: $BACKUP_FILE"
# Оставить только последние 30 бэкапов
ls -t "$BACKUP_DIR"/crm_azs_*.sql 2>/dev/null | tail -n +31 | xargs -r rm --
echo "Done."

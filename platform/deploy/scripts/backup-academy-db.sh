#!/bin/bash
# EduBridge Academy — daily Postgres backup.
#
# Installed on the server at /usr/local/bin/backup-academy-db.sh, run by
# root's crontab (matches the pattern already used for the two sibling
# EduBridge projects on this box — see platform/deploy/docs/DEPLOY.md for
# the exact crontab line and for how to restore a backup with
# restore-academy-db.sh).
set -euo pipefail

BACKUP_DIR="/backups"
CONTAINER="academy_postgres"
DB_USER="edubridge_academy"
DB_NAME="edubridge_academy"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="$BACKUP_DIR/academy_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILENAME"

# Keep the last 7 days; anything older than 8 gets deleted. The one-day
# slack means a late/slow run never wipes the last good backup before its
# replacement has finished writing (set -e above already means the delete
# line below never even runs if pg_dump failed).
find "$BACKUP_DIR" -maxdepth 1 -name "academy_*.sql.gz" -mtime +8 -delete

echo "Backup created: $FILENAME ($(du -h "$FILENAME" | cut -f1))"

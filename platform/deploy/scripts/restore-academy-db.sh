#!/bin/bash
# EduBridge Academy — restore a Postgres backup made by backup-academy-db.sh.
#
# Usage: restore-academy-db.sh /backups/academy_2026-08-11_03-00-01.sql.gz
#
# DESTRUCTIVE: replays the dump's SQL into the live database (the dump is
# plain SQL, same as the other two EduBridge projects' backups — CREATE
# TABLE statements will fail loudly if the tables already exist, which is
# the point: this is meant for restoring into an empty/dropped database,
# not layering on top of a live one). Asks for confirmation before running.
set -euo pipefail

FILE="${1:?Usage: $0 <path-to-backup.sql.gz>}"
CONTAINER="academy_postgres"
DB_USER="edubridge_academy"
DB_NAME="edubridge_academy"

if [ ! -f "$FILE" ]; then
  echo "No such file: $FILE" >&2
  exit 1
fi

echo "About to restore '$FILE' into database '$DB_NAME' on container '$CONTAINER'."
echo "Make sure the target database is empty (or that's intentional) before continuing."
read -r -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

gunzip -c "$FILE" | docker exec -i "$CONTAINER" psql -v ON_ERROR_STOP=1 -U "$DB_USER" -d "$DB_NAME"

echo "Restore complete."

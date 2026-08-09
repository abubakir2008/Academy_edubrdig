#!/usr/bin/env bash
set -euo pipefail

if [ -z "${DEPARTMENT:-}" ]; then
  echo "DEPARTMENT env var is required (identity|engagement|content|backoffice|academics|calendar)" >&2
  exit 1
fi

cd "/app/microservices/${DEPARTMENT}"

echo "[${DEPARTMENT}] Running migrations..."
alembic upgrade head

echo "[${DEPARTMENT}] Starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

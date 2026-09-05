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
# --proxy-headers/--forwarded-allow-ips='*': the only thing that ever talks
# to this container directly is Traefik on the internal edubridge-net (never
# the public internet -- see docker-compose.prod.yml), and the shared nginx
# gateway in front of Traefik already sets X-Forwarded-For correctly (see
# nginx-gateway/nginx.conf's proxy_set_header). Without this flag,
# request.client.host is Traefik's own container IP for every request from
# every real user -- middleware.py's per-IP rate limiter (and anything else
# keyed by client IP) would otherwise throttle the whole site as if it were
# one visitor instead of one budget per real client.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'

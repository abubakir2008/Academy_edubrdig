#!/bin/bash
# Runs on the production server, triggered by GitHub Actions over the
# restricted `academy_deploy_key` (forced command, see DEPLOY.md and
# /usr/local/bin/academy-deploy-dispatch.sh) or manually via:
#   ssh -i ~/.ssh/id_rsa root@187.124.132.180 /usr/local/bin/deploy-academy-backend.sh
# Logs to /var/log/academy-deploy.log since a forced-command SSH session's
# stdout isn't reliably visible on the calling side (same reasoning as
# edubridge-crm's deploy-crm.sh).
set -e
exec >> /var/log/academy-deploy.log 2>&1
echo "=== $(date -u +%FT%TZ) backend deploy starting ==="

cd /EduBridge_Academy_1.0.0
git fetch origin
git reset --hard origin/master

cd platform
# --profile full also starts MinIO (avatar photo storage) and the lesson
# recorder — everything else runs fine without it.
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile full up -d --build

echo "Waiting for the gateway to come up..."
for i in $(seq 1 40); do
  if curl -fsS -m 5 http://127.0.0.1:8091/api/auth/health > /dev/null 2>&1; then
    echo "Backend is healthy"
    break
  fi
  if [ "$i" -eq 40 ]; then
    echo "Backend did not become healthy in time"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile full logs --tail 80
    exit 1
  fi
  echo "Attempt $i/40, retrying in 10s..."
  sleep 10
done

docker image prune -f
echo "=== $(date -u +%FT%TZ) backend deploy finished ==="

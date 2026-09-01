#!/bin/bash
# Runs on the production server, triggered by GitHub Actions over the
# restricted `academy_deploy_key` (forced command, see DEPLOY.md and
# /usr/local/bin/academy-deploy-dispatch.sh) or manually via:
#   ssh -i ~/.ssh/id_rsa root@187.124.132.180 /usr/local/bin/deploy-academy-frontend.sh
set -e
exec >> /var/log/academy-deploy.log 2>&1
echo "=== $(date -u +%FT%TZ) frontend deploy starting ==="

cd /EduBridge_Academy_1.0.0
git fetch origin
git reset --hard origin/master

cd frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo "Waiting for frontend container to become healthy..."
for i in $(seq 1 20); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' frontend 2>/dev/null || echo starting)
  if [ "$STATUS" = "healthy" ]; then
    echo "Frontend is healthy"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "Frontend did not become healthy in time (status: $STATUS)"
    docker logs --tail 50 frontend
    exit 1
  fi
  echo "Attempt $i/20 (status: $STATUS), retrying in 5s..."
  sleep 5
done

docker image prune -f
echo "=== $(date -u +%FT%TZ) frontend deploy finished ==="

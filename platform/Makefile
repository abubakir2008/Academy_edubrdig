# EduBridge platform - developer shortcuts

.PHONY: help up down build logs ps auth-shell migrate revision test lint

help:
	@echo "up        - build & start the whole stack"
	@echo "down      - stop the stack (keep volumes)"
	@echo "clean     - stop the stack and remove volumes"
	@echo "build     - build all images"
	@echo "logs      - tail logs (use S=identity to filter one department)"
	@echo "ps        - list containers"
	@echo "migrate   - run migrations for one department (D=identity)"
	@echo "revision  - autogenerate a migration for one department (D=identity M=\"message\")"
	@echo "test      - run the pytest suite against postgres+redis (starts them if needed)"

up:
	docker compose up -d --build

down:
	docker compose down

clean:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f $(S)

ps:
	docker compose ps

migrate:
	docker compose exec $(or $(D),identity) alembic upgrade head

revision:
	docker compose exec $(or $(D),identity) alembic revision --autogenerate -m "$(M)"

# Deliberately does NOT use `docker compose up -d postgres redis` for the
# test infra: this project's compose files hardcode both the network name
# (academy-internal) and, under docker-compose.prod.yml, the container
# names (academy_postgres/academy_redis) -- and Compose resolves its
# "project" purely from the directory basename ("platform"), so *any*
# checkout of this repo on a host that's also running the real deployment
# (e.g. this same VPS) is the same Compose project as far as the daemon is
# concerned. `docker compose up -d postgres redis` from a throwaway clone
# has, for real, reconciled against and recreated the live production
# postgres/redis containers -- the data survived only because the named
# volume is also project-scoped and got reattached, not because it was
# safe. own throwaway containers on their own network side-steps all of
# that: nothing here can ever resolve to a project Compose already knows
# about.
test:
	docker compose build identity
	docker network create eb_test_net >/dev/null 2>&1 || true
	docker rm -f eb_test_pg eb_test_redis >/dev/null 2>&1 || true
	docker run -d --name eb_test_pg --network eb_test_net \
		-e POSTGRES_USER=edubridge -e POSTGRES_PASSWORD=edubridge -e POSTGRES_DB=edubridge \
		postgres:16
	docker run -d --name eb_test_redis --network eb_test_net redis:7-alpine
	@echo "Waiting for postgres..."
	@for i in $$(seq 1 30); do docker exec eb_test_pg pg_isready -U edubridge >/dev/null 2>&1 && break; sleep 1; done
	docker run --rm --network eb_test_net \
		-v "$$(pwd)/tests:/app/tests" \
		-e POSTGRES_HOST=eb_test_pg -e REDIS_HOST=eb_test_redis \
		-e TEST_DATABASE_URL=postgresql://edubridge:edubridge@eb_test_pg:5432/edubridge \
		-e TEST_REDIS_URL=redis://eb_test_redis:6379/15 \
		platform-identity:latest \
		bash -c "pip install --quiet pytest pytest-asyncio asyncpg httpx cryptography && cd /app && python -m pytest tests/ -v"; \
	status=$$?; \
	docker rm -f eb_test_pg eb_test_redis >/dev/null 2>&1; \
	docker network rm eb_test_net >/dev/null 2>&1; \
	exit $$status

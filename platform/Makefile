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

test:
	docker compose up -d postgres redis
	docker compose build identity
	docker run --rm --network academy-internal \
		-v "$$(pwd)/tests:/app/tests" \
		-e POSTGRES_HOST=postgres -e REDIS_HOST=redis \
		-e TEST_DATABASE_URL=postgresql://edubridge:edubridge@postgres:5432/edubridge \
		-e TEST_REDIS_URL=redis://redis:6379/15 \
		$$(docker compose images -q identity) \
		bash -c "pip install --quiet pytest pytest-asyncio asyncpg httpx cryptography && cd /app && python -m pytest tests/ -v"

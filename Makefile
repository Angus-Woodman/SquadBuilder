.PHONY: backend-fetch backend-lint backend-format backend-test db-up db-down db-logs backend-api backend-dev frontend-dev

backend-fetch:
	cd backend && uv run python -m app.cli fetch -c PL

backend-lint:
	cd backend && uv run ruff check .

backend-format:
	cd backend && uv run ruff format .

backend-test:
	cd backend && uv run pytest

db-up:
	docker compose -f infra/docker-compose.yml up -d

db-down:
	docker compose -f infra/docker-compose.yml down

db-logs:
	docker compose -f infra/docker-compose.yml logs -f

backend-api:
	cd backend && uv run uvicorn app.api.main:app --reload

backend-dev: db-up backend-api

frontend-dev:
	cd frontend && pnpm run dev

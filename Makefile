.PHONY: help up down logs ingest ingest-force lint-wiki migrate test test-local typecheck frontend-dev

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

up: ## Start all services (Docker Compose)
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

ingest: ## Ingest wiki pages into the vector DB (via Docker)
	docker compose exec backend python -m sobriquets.ingest

ingest-force: ## Re-ingest all wiki pages, ignoring hashes (via Docker)
	docker compose exec backend python -m sobriquets.ingest --force

lint-wiki: ## Check wiki for broken refs and missing frontmatter (via Docker)
	docker compose exec backend python -m sobriquets.lint

migrate: ## Run Alembic migrations (via Docker)
	docker compose exec backend alembic upgrade head

test: ## Run backend tests (via Docker)
	docker compose exec backend pytest

test-local: ## Run backend tests locally without Docker
	cd backend && pip install --quiet pytest pytest-asyncio python-frontmatter fastapi httpx pydantic-settings anyio && pytest tests/ -v

typecheck: ## Run TypeScript type check on the frontend
	cd frontend && npm run typecheck

frontend-dev: ## Start the frontend dev server locally
	cd frontend && npm run dev

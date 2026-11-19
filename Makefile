.PHONY: help install db-up db-down db-reset api migrate migration admin test lint type check web-install web web-build web-test

help:
	@echo "SchoolOps targets"
	@echo "  make install    Install backend dependencies"
	@echo "  make web-install  Install frontend dependencies"
	@echo "  make db-up      Start PostgreSQL (host port 5433)"
	@echo "  make db-down    Stop PostgreSQL"
	@echo "  make api        Run the API with reload on :8000"
	@echo "  make web        Run the Angular dev server on :4200"
	@echo "  make migrate    Apply migrations"
	@echo "  make migration  Create a migration (m='message')"
	@echo "  make admin      Create an admin (email=...; prompts for a password)"
	@echo "  make test       Run backend tests"
	@echo "  make lint       Check formatting and lint"
	@echo "  make type       Type-check backend"
	@echo "  make check      Full gate: lint + type + backend tests + web build/test"

install:
	cd backend && uv sync

web-install:
	cd frontend && npm ci

db-up:
	docker compose up -d db

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d db

api:
	cd backend && uv run uvicorn schoolops.main:app --reload --port 8000

web:
	cd frontend && npm start

migrate:
	cd backend && uv run alembic upgrade head

migration:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

admin:
	cd backend && uv run python -m schoolops.cli create-admin --email "$(email)"

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff format --check . && uv run ruff check .

type:
	cd backend && uv run mypy src tests

web-build:
	cd frontend && npm run build

web-test:
	cd frontend && npm test -- --watch=false

check: lint type test web-build web-test

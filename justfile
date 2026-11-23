# List available recipes
default:
    @just --list

# Install backend dependencies
install:
    cd backend && uv sync

# Install frontend dependencies
web-install:
    cd frontend && npm ci

# Start PostgreSQL (host port 5433)
db-up:
    docker compose up -d db

# Stop PostgreSQL
db-down:
    docker compose down

# Drop the database volume and start PostgreSQL again
db-reset:
    docker compose down -v
    docker compose up -d db

# Run the API with reload on :8000
api:
    cd backend && uv run uvicorn schoolops.main:app --reload --port 8000

# Run the Angular dev server on :4200
web:
    cd frontend && npm start

# Apply migrations
migrate:
    cd backend && uv run alembic upgrade head

# Create a migration: just migration "message"
migration message:
    cd backend && uv run alembic revision --autogenerate -m "{{message}}"

# Create an admin (prompts for a password): just admin email@example.com
admin email:
    cd backend && uv run python -m schoolops.cli create-admin --email "{{email}}"

# Run backend tests
test:
    cd backend && uv run pytest

# Check formatting and lint
lint:
    cd backend && uv run ruff format --check . && uv run ruff check .

# Type-check backend
type:
    cd backend && uv run mypy src tests

# Build the frontend
web-build:
    cd frontend && npm run build

# Run frontend tests
web-test:
    cd frontend && npm test -- --watch=false

# Full gate: lint + type + backend tests + web build/test
check: lint type test web-build web-test

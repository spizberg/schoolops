# ADR-0001: FastAPI + Angular monorepo with a src-layout backend

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

We need a single-congregation children's ministry app (Children's Bible Study Group) with a rich admin UI, a typed HTTP
API, and straightforward local development. The team is small and the domain is
CRUD-heavy but has real rules (ministry calendar, attendance, promotion) that must be
tested independently of HTTP.

## Decision

- Backend: FastAPI + SQLAlchemy 2.0 (async) + asyncpg + Alembic + Pydantic v2.
- Frontend: Angular (standalone components, signals), consuming the OpenAPI schema.
- One repository with `backend/`, `frontend/`, and `docs/`; no Nx or monorepo tooling.
- Backend uses a `src/schoolops` layout and is organized by feature, not by file type.
  The package name is retained through the church-domain refactor to avoid a second
  mechanical rename; user-facing vocabulary is church-specific.

## Consequences

- Business rules are testable without HTTP or a browser.
- The OpenAPI document is the contract; Angular types can be generated from it.
- We build all admin screens ourselves (Django admin was considered and rejected for UX
  control and API-first design).
- Two toolchains (uv and npm) in one repo; the justfile is the single entry point.

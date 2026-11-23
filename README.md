# Children's Bible Study Group

The admin system for the Children's Bible Study Group, a single-congregation children's ministry: ministry years, age-band classes,
households and guardians, children, volunteers, weekly Sunday sessions, lesson content,
attendance (including one-off visitors), and attendance reports.

**Stack:** FastAPI · SQLAlchemy 2 (async) · PostgreSQL · Alembic · Angular

## Documentation

| Document | Purpose |
| --- | --- |
| [Requirements](docs/01-requirements.md) | Scope, user stories, acceptance criteria, assumptions |
| [Technical design](docs/02-design.md) | Architecture, ERD, API contract, testing and deployment |
| [Agent workflow](docs/03-agent-workflow.md) | Orchestrator + subagents for the full-stack SDLC, with human gates |
| [ADRs](docs/adr/) | Recorded design decisions |

## Repository layout

```text
backend/     FastAPI app (src layout) + migrations + tests
frontend/    Angular 22 admin UI (zoneless, standalone components)
docs/        Requirements, design, decision records
```

## Quickstart

Prerequisites: [`just`](https://github.com/casey/just), `uv`, Docker, and (for the
frontend) Node.js 22/24 LTS.

```bash
cp .env.example backend/.env         # local settings
just install                         # backend dependencies
just web-install                     # frontend dependencies
just db-up                           # PostgreSQL on localhost:5433
just migrate                         # apply migrations
just demo                            # seed demo ministry data
just admin admin@example.com         # prompts for a password
just api                             # http://localhost:8000/docs
just web                             # http://localhost:4200 (proxies /v1 to the API)
```

Run `just` with no arguments to list every recipe.

### Full stack in Docker (one command)

```bash
just up            # docker compose up --build
```

| Service | URL |
| --- | --- |
| Web UI | http://localhost:8080 |
| API docs | http://localhost:8000/docs (also http://localhost:8080/docs) |
| API | http://localhost:8000/v1 |
| PostgreSQL | localhost:5433 |

The API container applies Alembic migrations on startup and waits for PostgreSQL via
health checks; nginx serves the Angular build and proxies `/v1` to the API. Data persists
in the `schoolops-pgdata` volume.

```bash
just up-detached   # same, in the background
just down          # stop everything (volume kept)
docker compose down -v   # stop and delete the database volume
```

Set a real `JWT_SECRET` in the shell or in a root `.env` before exposing the stack beyond
your machine.

Health checks: `GET /health/live` and `GET /health/ready`.

## Demo data

```bash
just demo
```

Creates two ministry years, volunteers, households, guardians, children, age-band
classes, enrollments, Sunday sessions, session volunteers, attendance, and visitor
entries. The `2026-2027` year is active; `2025-2026` is available for the promotion
screen. The seed refuses to run when ministry years already exist, so it will not
duplicate data.

The most recent session is Sunday `2026-11-22`; the dashboard's "today" section will be
empty while today is not a Sunday. Use the Sessions screen with a September–November
range to review the seeded attendance. The Angular dev server uses
`frontend/proxy.conf.json`, so the browser talks to `/v1` on the same origin.

## Quality gate

```bash
just check    # ruff + mypy + pytest, then Angular build and unit tests
```

The same commands run in CI (`.github/workflows/ci.yml`). Integration tests use a
dedicated `schoolops_test` database, created automatically, so local data is untouched.

## Status

- [x] Phase 1 — requirements and scope
- [x] Phase 2 — architecture, ERD, API map, ADRs
- [x] Phase 3 — foundation: app factory, settings, DB session, migrations, health, CI
- [x] Foundation — app factory, DB, migrations, CI, auth and RBAC
- [x] Church domain — ministry years, volunteers, households, guardians, children
- [x] Age-band classes, enrollments, and one active class per ministry year
- [x] Sessions, lesson content, session volunteers, present/absent attendance, visitors
- [x] Household/guardian links, guardian search, child safety fields
- [x] Annual promotion with preview and idempotent apply
- [x] Dashboard, not-seen report, attendance reports and CSV exports
- [x] Audit trail — append-only actor/changes log and query screen
- [x] Hardening — production config guards, security headers, request IDs, JSON logs, body limit
- [x] Seed/demo data — `just demo`
- [ ] Deployment runbook and production checks

## Conventions

- Target meeting week: Sunday only (ISO weekday 7), configurable per ministry year.
- All `/v1` routes except `POST /v1/auth/login` require an admin bearer token.
- Attendance is per class session; missing attendance is "not recorded", never absence.
- Volunteers are deactivated, enrollments are ended, and history is not hard-deleted.
- Households group siblings; guardians are linked per child with one primary guardian.
- Check-in/check-out, labels, pickup codes, and pickup verification are out of scope for
  the MVP.
- Errors use RFC 9457 Problem Details.

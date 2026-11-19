---
name: FastAPI API Development
description: Build production FastAPI APIs with app factories, lifespan resources, Annotated dependencies, Pydantic v2 contracts, async SQLAlchemy transactions, Problem Details errors, JWT auth, pagination, idempotency, and async tests. Use when creating or reviewing a FastAPI service or endpoint.
---

# FastAPI API Development

A good FastAPI API is thin at the edges, explicit about contracts, and testable
without a network. The framework handles HTTP; your code owns business rules.

## Default stack

| Concern | Default |
| --- | --- |
| Framework | `fastapi[standard]` |
| Validation | Pydantic v2 (`BaseModel`, `ConfigDict`) |
| Settings | `pydantic-settings` |
| DB | SQLAlchemy 2.0 async + `asyncpg`/`aiosqlite` |
| Migrations | Alembic, run before the app starts |
| Auth | Bearer JWT verified with `PyJWT[crypto]` or a provider's JWKS |
| Tests | `pytest` + `httpx.AsyncClient` + `asgi-lifespan` |
| Server | `fastapi run` locally, Uvicorn workers in production |

Do not add SQLModel unless the team wants it; SQLAlchemy 2.0 with separate
Pydantic schemas keeps persistence and the public contract independent.

## Layout

Organize by feature, not by file type. A feature owns its router, schemas,
service, and repository.

```text
src/app/
├── main.py                  # create_app(), lifespan, middleware
├── core/
│   ├── config.py            # Settings + get_settings()
│   ├── errors.py            # domain errors + Problem Details handlers
│   ├── logging.py
│   └── security.py          # token verification, current user
├── db/
│   ├── base.py              # DeclarativeBase
│   ├── session.py           # engine/sessionmaker factories
│   └── models/
├── api/
│   ├── deps.py              # SessionDep, UowDep, pagination
│   └── v1/
│       ├── router.py
│       └── orders/
│           ├── router.py
│           ├── schemas.py
│           ├── service.py
│           └── repository.py
└── domain/                  # pure rules, no FastAPI imports
```

Routers may import services. Services and domain must not import FastAPI,
`Request`, `HTTPException`, or Pydantic request models. That boundary is what
makes the logic reusable and unit-testable.

## App factory and lifespan

Create the app in a function so tests can inject settings. Build engines,
clients, and pools in `lifespan`, store them on `app.state`, and dispose them on
shutdown. Never create an engine at import time.

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = build_engine(settings.database_url)
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    install_exception_handlers(app)
    app.include_router(api_router, prefix="/v1")
    return app


app = create_app()
```

- Use `lifespan`, not `@app.on_event("startup")`.
- Run migrations in the deploy pipeline, not with `Base.metadata.create_all`.
- Keep `create_app` in `app/factory.py` and `app/main.py` as
  `app = create_app()`. Tests import the factory, so they do not need production
  environment variables at import time.
- Importing `app.main` must not connect to anything.
- Keep startup checks cheap; deep dependency checks belong in readiness probes.

## Dependency injection

Use `Annotated[T, Depends(...)]` aliases. No default-value `Depends()`.

```python
async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]
```

Rules:

- One dependency owns each resource (session, HTTP client, clock, settings).
- Dependencies are cached per request by default; don't duplicate expensive
  work.
- Exit code in a `yield` dependency runs after the response by default. Give the
  transaction/unit-of-work dependency
  `Depends(get_uow, scope="function")` so commit or rollback happens before the
  response is sent. Never use `scope="function"` for streaming responses that
  still need the resource.
- Clean up in `finally`; re-raise exceptions you did not translate.
- Override dependencies in tests; do not monkeypatch internals.
- Do not inject a `Request` into domain logic. Pass values.

## Request and response contracts

Define separate models:

```python
class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: list[OrderLineCreate] = Field(min_length=1, max_length=100)

class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: OrderStatus
    total_cents: int
    created_at: datetime
```

- Request models: `extra="forbid"`, explicit bounds, no server-owned fields
  (`id`, `created_at`, `status`).
- Response models: only public fields. Never return ORM models directly.
- `from_attributes=True` for ORM-to-schema conversion; use
  `Schema.model_validate(entity)`.
- Never expose password hashes, internal flags, or secrets "just in case".
- Declare `response_model` explicitly when the returned object is not the
  response type (`response_model=OrderRead` while returning an `Order`).
- Keep `response_model` and the return annotation consistent; FastAPI uses the
  annotation when `response_model` is absent.
- Use aliases only for external contracts, and document them.

## Routing and HTTP semantics

```python
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=201)
async def create_order(
    payload: OrderCreate,
    uow: UowDep,
    user: UserDep,
) -> OrderRead:
    order = await orders_service.create(uow, payload, customer_id=user.id)
    return OrderRead.model_validate(order)
```

- Handlers parse, call one service, and serialize. No business rules.
- Use plural nouns; actions as sub-resources (`POST /orders/{id}/cancel`).
- Status codes: `200` read/update, `201` create (+`Location`), `202` accepted,
  `204` delete, `401` unauthenticated, `403` forbidden, `404` missing,
  `409` conflict, `422` validation, `429` rate limited.
- `PUT` replaces, `PATCH` partially updates. For PATCH use
  `model_dump(exclude_unset=True)` so absent is not the same as `null`.
- Delete is idempotent: `204` even if already absent, unless the contract says
  otherwise.
- Cap pagination (`Query(ge=1, le=100)`) and never expose unbounded `limit`.
- Return `404` for resources the caller may not see, instead of leaking
  existence with `403`, when that matches the product's security policy.
- Use ISO 8601 UTC timestamps, string enums, and integer minor units for money.
- Prefix with `/v1`; make additive changes, deprecate fields with headers before
  removal, and generate clients from OpenAPI in CI.

## Persistence and transactions

- One `AsyncSession` per request; one transaction per use case.
- Repositories read and write; they do not commit.
- The unit of work or service owns the commit boundary:

```python
async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    async with request.app.state.sessionmaker() as session, session.begin():
        yield UnitOfWork(session)
```

- On exception the transaction rolls back; map the domain error to HTTP after
  that.
- Use an async driver in async routes. A sync driver inside `async def` blocks
  the event loop. If the driver is sync, define the route with `def` so FastAPI
  runs it in a threadpool, or use `run_in_threadpool`.
- Avoid lazy loading in async code. Set `lazy="raise"` on relationships and load
  explicitly with `selectinload`/`joinedload`.
- Create the engine once per process; size pools against worker count and the
  database's connection limit.
- Use `expire_on_commit=False` for response serialization after commit.
- Add `pool_pre_ping=True` and statement/connection timeouts.
- Use Alembic for schema changes; inspect generated migrations.

## Errors

Raise domain errors, translate at the edge, and return one envelope. RFC 9457
Problem Details (`application/problem+json`) is the default:

```python
class NotFound(DomainError):
    status_code = 404
    title = "Not found"


@app.exception_handler(DomainError)
async def handle_domain(request: Request, exc: DomainError) -> JSONResponse:
    return problem_response(
        request,
        status=exc.status_code,
        title=exc.title,
        detail=str(exc),
        type_uri=exc.type_uri,
    )
```

- Register handlers for `DomainError`, `RequestValidationError`,
  `StarletteHTTPException`, and a catch-all `Exception`.
- Normalize FastAPI's default `{"detail": ...}` so clients parse one shape.
- Use `jsonable_encoder(exc.errors())` for validation details.
- Log unexpected exceptions with `logger.exception` and a request ID; return a
  generic message without stack traces, SQL, or paths.
- Do not catch `Exception` in handlers to return `200`. Do not swallow
  `CancelledError`.
- Validate at the boundary; trust parsed data inside the process.
- See the `python-security` skill for authz, injection, and secret handling.

## Authentication and authorization

- Verify signature, algorithm allowlist, `exp`, `iat`, `iss`, and `aud`. Never
  decode with verification disabled.
- Accept tokens from the `Authorization: Bearer` header only.
- Put identity in a small `CurrentUser` object; inject it, don't re-parse the
  token in handlers.
- Check object ownership on every read and write, in the query when possible.
- Use `Security` with OAuth2 password flow when you need Swagger scopes;
  `HTTPBearer` is fine for provider-issued tokens.
- Use Argon2id (`argon2-cffi`/`pwdlib`) for passwords; never write your own
  crypto. Avoid `python-jose` and `passlib` (unmaintained).
- Rate-limit login and token endpoints at the gateway or a shared store.

## Async correctness

- Use `async` routes only when the whole path is async.
- Never call `requests`, `time.sleep`, sync SQLAlchemy, or heavy CPU work in an
  `async def` handler.
- Set client timeouts on every outbound call; a request with no timeout can hang
  a worker forever.
- Use bounded concurrency for independent I/O; never unbounded `gather` over
  user input.
- Use `BackgroundTasks` only for small, loss-tolerant work after the response.
  Use a durable queue (Celery, Dramatiq, ARQ, SQS) for retries, scheduling, or
  anything that must not be lost.
- Don't pass ORM objects or request-scoped sessions to background tasks; pass
  IDs and reload in a new scope.

## Testing

Use `httpx.AsyncClient` with `ASGITransport` and run the lifespan explicitly.
Prefer a real test database; override only external boundaries.

```python
async with LifespanManager(application):
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/orders", json=payload, headers=auth)
```

- Inject test `Settings` into `create_app`; do not mutate global settings.
- Create the schema from migrations or metadata in a fixture; isolate tests with
  rollback or a fresh database per worker.
- Override dependencies for third-party clients and clocks, not for your own
  services.
- Clear `app.dependency_overrides` in fixture teardown.
- Assert status, content type, and the contract fields clients depend on.
- Test `401`, `403`, `404`, `409`, `422`, and idempotent retries, not just 200.
- See `python-testing` for general pytest strategy.

## Production

- Run `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers N` behind a
  proxy; never use `--reload` in production.
- Set `--proxy-headers --forwarded-allow-ips` correctly; otherwise client IPs
  and scheme are wrong.
- Add liveness (`/health/live`) and readiness (`/health/ready`) endpoints; keep
  them cheap and unauthenticated.
- Restrict CORS to explicit origins; never combine `*` with credentials.
- Add trusted hosts, request size limits, timeouts, and rate limits at the proxy
  or gateway.
- Emit structured logs with request IDs, latency, status, and route; never log
  bodies, tokens, or PII.
- Instrument with OpenTelemetry for traces and RED metrics.
- Protect or disable `/docs` in public production if the API is not public.
- Gracefully drain in-flight requests; dispose pools and clients in lifespan.
- See `references/production-checklist.md`.

## Anti-patterns

- Business logic, SQL, or authorization in route functions.
- Global engine/session, or a new engine per request.
- Returning ORM models and accidentally exposing columns.
- One Pydantic model reused for create, update, and read.
- `async def` route calling sync I/O or CPU-heavy code.
- `except Exception` returning `200` or hiding errors.
- `HTTPException` raised deep in the domain layer.
- `Base.metadata.create_all` in production instead of migrations.
- `allow_origins=["*"]` with `allow_credentials=True`.
- JWT decoded without signature/audience/issuer checks.
- Unbounded `limit`, deep offset pagination on large tables, or N+1 queries.
- Durable work in `BackgroundTasks`.
- Tests hitting a shared database or the real network.
- `@app.on_event("startup")` and import-time side effects.
- Dependency overrides leaking across tests.
- Versioning by breaking clients and calling it "v1".

## Checklist

- [ ] App is created by a factory and imports without side effects.
- [ ] Resources are built in lifespan and disposed on shutdown.
- [ ] Settings are typed, validated, and injected.
- [ ] Dependencies use `Annotated` and own one resource each.
- [ ] Request and response schemas are separate; ORM never leaks.
- [ ] Handlers are thin; services own rules and transaction boundaries.
- [ ] Async routes never block the event loop.
- [ ] Errors use one Problem Details envelope with stable codes and no leaks.
- [ ] Auth verifies signatures and checks object-level authorization.
- [ ] Pagination is capped; PATCH distinguishes absent from `null`.
- [ ] Mutating retries are protected by idempotency keys where required.
- [ ] Tests run against a real DB and assert failure statuses.
- [ ] OpenAPI is accurate, versioned, and used to generate clients.
- [ ] Health checks, logs, metrics, timeouts, and limits are configured.
- [ ] Migrations run in deploy, with a rollback path.

## References

- `references/app-skeleton.md` — complete file-by-file starter.
- `references/api-recipes.md` — pagination, idempotency, auth, background jobs,
  streaming, uploads, middleware, deprecation.
- `references/fastapi-testing.md` — async test fixtures and overrides.
- `references/production-checklist.md` — deployment and operations review.

# Testing FastAPI services

Test the HTTP contract plus the business behavior behind it. Use a real app,
real routing, real serialization, and a real (test) database; fake only external
systems.

## Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = "-ra --strict-markers --strict-config"
testpaths = ["tests"]
filterwarnings = ["error"]
```

If the project uses AnyIO instead, replace `asyncio_mode` with a `pytest.mark.anyio`
marker and an `anyio_backend` fixture. Pick one runner; do not mix.

## Fixtures

```python
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.base import Base
from app.db.models.order import Order  # noqa: F401  registers the table
from app.factory import create_app


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        jwt_secret="test-secret-that-is-at-least-32-bytes",
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with LifespanManager(application):
        async with application.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as http_client:
        yield http_client


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


def make_auth_headers(settings: Settings, subject: UUID) -> dict[str, str]:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(subject),
            "scope": "orders:read orders:write",
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(settings: Settings, user_id: UUID) -> dict[str, str]:
    return make_auth_headers(settings, user_id)


@pytest.fixture
def other_auth_headers(settings: Settings) -> dict[str, str]:
    return make_auth_headers(settings, uuid4())


@pytest.fixture
def overrides(app: FastAPI) -> dict:
    yield app.dependency_overrides
    app.dependency_overrides.clear()
```

Key points:

- `create_app(settings)` means no global settings mutation and no shared engine
  between tests.
- `LifespanManager` runs startup/shutdown, so engine creation and disposal are
  exercised.
- `tmp_path` gives each test a fresh SQLite database. For Postgres, see below.
- Clear dependency overrides in teardown; a leaked override causes bizarre,
  order-dependent failures.

## A test

```python
async def test_create_order(
    client: AsyncClient,
    auth_headers: dict[str, str],
    user_id: UUID,
) -> None:
    response = await client.post(
        "/v1/orders",
        headers=auth_headers,
        json={
            "lines": [
                {"sku": "SKU-1", "quantity": 2, "unit_price_cents": 500}
            ]
        },
    )

    assert response.status_code == 201
    assert response.headers["location"].startswith("/v1/orders/")
    body = response.json()
    assert body["total_cents"] == 1_000
    assert body["customer_id"] == str(user_id)
    assert body["status"] == "pending"
```

Test failures and boundaries, not only the happy path:

```python
async def test_requires_token(client: AsyncClient) -> None:
    response = await client.post("/v1/orders", json={"lines": []})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_rejects_unknown_field(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/v1/orders",
        headers=auth_headers,
        json={"lines": [], "total_cents": 1},
    )
    assert response.status_code == 422


async def test_cannot_read_another_users_order(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_auth_headers: dict[str, str],
) -> None:
    created = await client.post(
        "/v1/orders",
        headers=auth_headers,
        json={"lines": [{"sku": "A", "quantity": 1, "unit_price_cents": 100}]},
    )
    order_id = created.json()["id"]

    response = await client.get(
        f"/v1/orders/{order_id}", headers=other_auth_headers
    )
    assert response.status_code == 404
```

## Overriding external boundaries

Override the dependency, not the module global:

```python
from app.api.deps import get_payment_gateway

class FakeGateway:
    async def charge(self, *, customer_id: UUID, amount_cents: int) -> str:
        return "fake-charge-id"


async def test_payment_uses_gateway(
    client: AsyncClient,
    auth_headers: dict[str, str],
    overrides: dict,
) -> None:
    overrides[get_payment_gateway] = lambda: FakeGateway()
    response = await client.post(
        "/v1/orders/checkout",
        headers=auth_headers,
        json={"order_id": "..."},
    )
    assert response.status_code == 200
```

Do not override your own service or repository for integration tests; use the
real implementation against the test database. Unit-test pure domain logic
directly without FastAPI.

## Testing a 500 handler

By default, ASGI transports re-raise application exceptions so failures are not
hidden. Disable that only for the test that asserts the error response:

```python
transport = ASGITransport(app=app, raise_app_exceptions=False)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.get("/v1/boom")
assert response.status_code == 500
assert response.json()["title"] == "Internal server error"
```

Keep a test that verifies the exception is logged, using `caplog`.

## Postgres test database

SQLite hides differences in types, constraints, transactions, and `FOR UPDATE`.
Run integration tests against the same engine as production.

Recommended setup:

- One database per CI job or per pytest worker (`pytest-xdist`).
- Run Alembic migrations once per session.
- Truncate all tables between tests, or wrap each test in a rolled-back
  transaction.
- Never share a database across parallel workers without isolation.

Truncation between tests:

```python
@pytest.fixture(autouse=True)
async def clean_tables(app: FastAPI) -> AsyncIterator[None]:
    yield
    async with app.state.engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
```

Transaction rollback per test is faster but requires binding the app's session
to the same connection and setting `join_transaction_mode="create_savepoint"`.
Use it only if the team understands the semantics; truncation is harder to get
wrong.

## Streaming responses

```python
async def test_stream(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    async with client.stream(
        "GET", "/v1/orders/123/events", headers=auth_headers
    ) as response:
        assert response.status_code == 200
        chunks = [chunk async for chunk in response.aiter_bytes()]
    assert b"event: started" in b"".join(chunks)
```

Bound the test with `asyncio.timeout` so a broken stream fails instead of
hanging CI.

## File uploads

```python
async def test_upload(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.post(
        "/v1/attachments",
        headers=auth_headers,
        files={"file": ("invoice.pdf", b"%PDF-1.7 ...", "application/pdf")},
    )
    assert response.status_code == 201
```

Add tests for oversized files, wrong content type, empty files, and filenames
with traversal characters.

## OpenAPI contract

```python
async def test_openapi_contains_orders(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert "/v1/orders" in schema["paths"]
    assert "OrderRead" in schema["components"]["schemas"]
```

Generate clients from this document in CI. A breaking schema diff should fail
the build or require an explicit version bump.

## Avoid

- A shared session-scoped database without isolation.
- Hitting real third-party APIs in the default suite.
- `time.sleep()` to wait for background work; inject a fake task or assert the
  enqueued message.
- Overriding the database dependency for tests that are supposed to validate SQL.
- Asserting on entire JSON bodies; assert the contract fields.
- Using `TestClient` and an async client against the same global app in parallel.
- Leaving `app.dependency_overrides` populated after a test.
- Treating a green happy path as coverage of authorization.

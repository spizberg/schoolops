# FastAPI API recipes

Patterns for the parts that are easy to get subtly wrong. Keep handlers thin and
push policy into services or dependencies.

## Cursor pagination

Offset pagination is fine for small admin lists. Use a keyset cursor for large
or changing feeds.

```python
import base64
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order import Order


@dataclass(frozen=True, slots=True)
class Cursor:
    created_at: datetime
    id: UUID


def encode_cursor(order: Order) -> str:
    raw = json.dumps(
        {"created_at": order.created_at.isoformat(), "id": str(order.id)},
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str) -> Cursor:
    padded = value + "=" * (-len(value) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(padded))
        return Cursor(
            created_at=datetime.fromisoformat(data["created_at"]),
            id=UUID(data["id"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidCursor("Invalid pagination cursor") from exc


async def list_page(
    session: AsyncSession,
    *,
    customer_id: UUID,
    cursor: Cursor | None,
    limit: int,
) -> tuple[list[Order], str | None]:
    statement = select(Order).where(Order.customer_id == customer_id)
    if cursor is not None:
        statement = statement.where(
            tuple_(Order.created_at, Order.id)
            < tuple_(cursor.created_at, cursor.id)
        )
    statement = statement.order_by(
        Order.created_at.desc(), Order.id.desc()
    ).limit(limit + 1)

    rows = list((await session.scalars(statement)).all())
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1]) if has_more and items else None
    return items, next_cursor
```

- Fetch `limit + 1` to know whether another page exists.
- Always include a unique tiebreaker (`id`) in the cursor and sort.
- Treat the cursor as untrusted input: decode defensively and return `422` on
  malformed values.
- Do not put SQL, secrets, or internal filters in the cursor. Signing is only
  needed if tampering changes authorization, which it must not.
- Cursors are opaque to clients; document that they must not be constructed.
- Add `InvalidCursor(DomainError)` with status `422`; never leak decode errors.

## Idempotent creates

Clients retry. Protect unsafe endpoints that create money, orders, or side
effects with an `Idempotency-Key` header.

```python
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int | None]
    response_body: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

Flow:

1. Require the header for the endpoint (`Header(alias="Idempotency-Key")`), with
   a length bound.
2. Hash the canonical request body plus route and user ID.
3. Try to insert a record in a `pending` state. A unique constraint resolves
   races: the loser reads the existing row.
4. If a `completed` record exists with the same hash, return its stored response.
5. If the hash differs, return `409`/`422` — the key was reused for a different
   request.
6. If the first request is still running, return `409` with `Retry-After`, or
   wait briefly.
7. Complete the record in the same transaction as the side effect when possible.
8. Expire records after 24 hours; clean them up in a job.

Do not store secret or oversized response bodies. If the endpoint is not
idempotent by design (for example, a random nonce), do not pretend it is.

## Token issuance

Use the OAuth2 password flow only for first-party clients. For third-party
clients, use authorization code + PKCE through an identity provider.

```python
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.api.deps import SettingsDep, UowDep
from app.core.errors import Unauthorized
from app.core.security import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    uow: UowDep,
    settings: SettingsDep,
) -> TokenResponse:
    user = await authenticate_user(uow, form.username, form.password)
    if user is None:
        raise Unauthorized("Invalid username or password")

    now = datetime.now(UTC)
    granted = sorted(set(form.scopes) & user.allowed_scopes)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "scope": " ".join(granted),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_ttl_seconds,
    )
```

`authenticate_user` must:

- Hash passwords with Argon2id (`argon2-cffi` or `pwdlib`), never SHA-256 alone.
- Verify a dummy hash for unknown users so response time does not reveal whether
  the account exists.
- Compare with a constant-time function provided by the hashing library.
- Never log the password or the raw token.

Scopes requested by the client must be intersected with the user's allowed
scopes. Never trust `form.scopes` as authorization.

`authenticate_user` is a service function you provide; it should return a small
user object with `id` and `allowed_scopes`, or `None` on failure. Keep it free of
FastAPI imports.

## Authorization dependency

```python
from typing import Annotated

from fastapi import Depends

from app.core.security import CurrentUser, require_scope

AdminUser = Annotated[CurrentUser, Depends(require_scope("admin"))]
OrderWriter = Annotated[CurrentUser, Depends(require_scope("orders:write"))]


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: UUID,
    uow: UowDep,
    user: OrderWriter,
) -> None:
    await service.delete(uow, order_id, actor=user)
```

Scope checks answer "may this principal perform this class of action?".
Object-level checks ("does this user own this order?") still belong in the
service/query. Apply both.

## Background work

Use `BackgroundTasks` only for small work that may be lost:

```python
from fastapi import BackgroundTasks


@router.post("/orders", status_code=201)
async def create(
    payload: OrderCreate,
    background: BackgroundTasks,
    uow: UowDep,
    user: UserDep,
) -> OrderRead:
    order = await service.create(uow, payload, customer_id=user.id)
    background.add_task(send_confirmation, order_id=order.id)
    return OrderRead.model_validate(order)
```

For anything durable, use a queue and the transactional outbox:

1. Write the business change and an `outbox` row in the same transaction.
2. A publisher reads unpublished rows and publishes to the broker.
3. Mark rows published; retry with idempotent consumers.
4. Keep the outbox payload small and versioned.

Never pass an ORM object or the request's `AsyncSession` to a background task.
Pass IDs; the task creates its own session.

## Streaming and SSE

```python
from collections.abc import AsyncIterator
from fastapi.responses import StreamingResponse


async def event_stream(order_id: UUID) -> AsyncIterator[bytes]:
    yield b"event: started\ndata: {}\n\n"
    async for update in subscribe(order_id):
        yield f"event: update\ndata: {update.model_dump_json()}\n\n".encode()


@router.get("/{order_id}/events")
async def stream_events(order_id: UUID, user: UserDep) -> StreamingResponse:
    return StreamingResponse(
        event_stream(order_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
```

- The dependency with `yield` closes after the response by default, so a
  request-scoped session stays open during the stream. Do not hold a DB session
  for a long stream; acquire short-lived sessions inside the generator.
- Use `Depends(..., scope="function")` only when the resource is not needed
  during streaming.
- Handle client disconnect: the generator is cancelled; close subscriptions in
  `finally`.
- Disable proxy buffering for SSE (`X-Accel-Buffering: no` with nginx).
- Compression middleware may buffer streams; exclude streaming routes.
- FastAPI also provides `EventSourceResponse`/`ServerSentEvent`; use it if the
  project already targets that API.
- `subscribe` is your broker/DB subscription; ensure it is cancellable and closes
  in `finally`.

## File uploads

```python
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import aiofiles
from fastapi import File, UploadFile, status

MAX_BYTES = 5 * 1024 * 1024
CHUNK = 64 * 1024
UPLOAD_DIR = Path("/srv/uploads")


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
async def upload(
    file: Annotated[UploadFile, File()],
    user: UserDep,
) -> dict[str, str]:
    if file.content_type not in {"application/pdf", "image/png", "image/jpeg"}:
        raise InvalidUpload("Unsupported content type")

    target = UPLOAD_DIR / f"{uuid4().hex}.bin"
    written = 0
    succeeded = False
    try:
        async with aiofiles.open(target, "wb") as sink:
            while chunk := await file.read(CHUNK):
                written += len(chunk)
                if written > MAX_BYTES:
                    raise InvalidUpload("File is too large")
                await sink.write(chunk)
        succeeded = True
    finally:
        if not succeeded:
            target.unlink(missing_ok=True)

    return {"id": target.stem}
```

- Never trust the client filename or content type; validate the bytes when it
  matters.
- Enforce size limits while reading, not only with `Content-Length` (it can
  lie).
- Store outside the web root with a generated name; serve through an authorized
  endpoint or signed URL.
- Write files in a thread (`anyio.to_thread`) or use an async file library if
  the handler is `async` and files are large.
- Clean up partial files on every failure path.
- Run malware scanning/quarantine for untrusted uploads.
- Define `InvalidUpload(DomainError)` with a `400`/`422` status; do not return a
  raw exception message.

## Request IDs and logging

Prefer pure ASGI middleware over `BaseHTTPMiddleware` for hot paths; the latter
can interfere with streaming, background tasks, and context variables.

```python
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id")
        request_id = incoming or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
            await send(message)

        await self.app(scope, receive, send_with_id)
```

- Honor a trusted upstream `X-Request-ID`; generate one otherwise.
- Put it in a context variable so log records include it automatically.
- Log method, route template, status, duration, and request ID. Not bodies,
  Authorization headers, tokens, or PII.
- `asgi-correlation-id` is a maintained alternative.

## OpenAPI, versioning, and deprecation

- Set unique `operation_id`s so generated clients get stable method names.
- Add `summary`, `description`, and `responses` for every error status.
- Use `tags` per feature; keep the schema free of internal fields.
- Version in the path (`/v1`). Additive changes are safe; type changes, enum
  removals, and new required fields are breaking.
- Deprecate before removal:

```python
response.headers["Deprecation"] = "true"
response.headers["Sunset"] = "Wed, 01 Jul 2026 23:59:59 GMT"
response.headers["Link"] = '</v2/orders>; rel="successor-version"'
```

- Generate the OpenAPI document in CI and fail if it changes unexpectedly
  without a versioning note.
- Protect `/docs` or disable it in public production if the API is not public.

## Conditional requests

For cacheable GETs:

```python
etag = f'W/"{resource.updated_at.timestamp():.0f}"'
if request.headers.get("if-none-match") == etag:
    return Response(status_code=304, headers={"ETag": etag})
return JSONResponse(
    content=payload,
    headers={"ETag": etag, "Cache-Control": "private, max-age=30"},
)
```

Use strong ETags when byte-for-byte equality matters and weak ETags (`W/"..."`)
for semantically equivalent representations. Never cache authenticated responses
in shared caches.

## Rate limiting

- Put global limits at the gateway/reverse proxy.
- App-level limits need a shared store (Redis) so each worker does not grant its
  own quota.
- Key by authenticated principal, falling back to IP only for anonymous routes.
- Return `429` with `Retry-After` and a Problem Details body.
- Apply stricter limits to login, token, password reset, and expensive search.
- Do not let a limiter failure fail open on sensitive endpoints.

## Timeouts

- Every outbound HTTP/database call gets a connect and read timeout.
- Wrap multi-step work in `asyncio.timeout()` so a slow dependency cannot pin a
  worker.
- Set proxy read/send timeouts longer than the slowest legitimate request, but
  finite.
- Return `504` for upstream timeouts, not `500`.

## Health checks

```python
@router.get("/health/live", include_in_schema=False)
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
async def ready(request: Request) -> Response:
    try:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok"})
```

- Liveness checks the process only. Readiness checks critical dependencies.
- Cache readiness for a few seconds; do not hit the DB on every probe if probes
  are frequent.
- Keep details private; return a generic status publicly.

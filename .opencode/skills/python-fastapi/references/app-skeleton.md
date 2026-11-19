# FastAPI app skeleton

A complete, minimal starter that demonstrates the patterns in the skill. Adapt
names and features; keep the boundaries.

## Tree

```text
src/app/
├── __init__.py
├── main.py
├── factory.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── errors.py
│   └── security.py
├── db/
│   ├── __init__.py
│   ├── base.py
│   ├── session.py
│   └── models/
│       ├── __init__.py
│       └── order.py
├── domain/
│   ├── __init__.py
│   └── orders.py
└── api/
    ├── __init__.py
    ├── deps.py
    └── v1/
        ├── __init__.py
        ├── router.py
        └── orders/
            ├── __init__.py
            ├── router.py
            ├── schemas.py
            ├── repository.py
            └── service.py
```

Dependencies:

```sh
uv add "fastapi[standard]" "sqlalchemy[asyncio]" asyncpg aiosqlite \
  pydantic-settings "pyjwt[crypto]"
uv add --dev pytest pytest-asyncio httpx asgi-lifespan
```

## `app/core/config.py`

```python
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "orders-api"
    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "orders-api"
    jwt_audience: str = "orders-api"
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    allowed_origins: list[str] = []
    enable_docs: bool = True

    @field_validator("database_url")
    @classmethod
    def _require_async_driver(cls, value: str) -> str:
        if not value.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError("database_url must use an async SQLAlchemy driver")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from env
```

Environment variables use the `APP_` prefix:

```dotenv
APP_DATABASE_URL=postgresql+asyncpg://app:secret@localhost:5432/app
APP_JWT_SECRET=replace-with-at-least-32-random-bytes
APP_ENVIRONMENT=local
```

Generate the secret with `openssl rand -hex 32`. HS256 requires at least 32
bytes; PyJWT warns (and strict test suites fail) on shorter keys.

## `app/core/errors.py`

```python
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    status_code = 400
    title = "Request failed"
    type_uri = "about:blank"


class InvalidOrder(DomainError):
    title = "Invalid order"
    type_uri = "https://errors.example.com/invalid-order"


class NotFound(DomainError):
    status_code = 404
    title = "Not found"
    type_uri = "https://errors.example.com/not-found"


class Conflict(DomainError):
    status_code = 409
    title = "Conflict"
    type_uri = "https://errors.example.com/conflict"


class Unauthorized(DomainError):
    status_code = 401
    title = "Unauthorized"
    type_uri = "https://errors.example.com/unauthorized"


class Forbidden(DomainError):
    status_code = 403
    title = "Forbidden"
    type_uri = "https://errors.example.com/forbidden"


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    errors: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if errors is not None:
        body["errors"] = errors
    if status == 401:
        headers = {"WWW-Authenticate": "Bearer", **(headers or {})}
    return JSONResponse(
        body,
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(
        request: Request, exc: DomainError
    ) -> JSONResponse:
        return problem_response(
            request,
            status=exc.status_code,
            title=exc.title,
            detail=str(exc),
            type_uri=exc.type_uri,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            request,
            status=422,
            title="Validation failed",
            detail="The request body or parameters are invalid.",
            type_uri="https://errors.example.com/validation",
            errors=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return problem_response(
            request,
            status=exc.status_code,
            title=detail,
            detail=detail,
            type_uri="https://errors.example.com/http",
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_error",
            exc_info=exc,
            extra={"path": request.url.path},
        )
        return problem_response(
            request,
            status=500,
            title="Internal server error",
            detail="An unexpected error occurred.",
            type_uri="https://errors.example.com/internal",
        )
```

## `app/core/security.py`

```python
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    scopes: frozenset[str]


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
) -> CurrentUser:
    settings: Settings = request.app.state.settings
    if credentials is None:
        raise Unauthorized("Missing bearer token")

    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired token") from exc

    try:
        user_id = UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise Unauthorized("Invalid token subject") from exc

    scopes = frozenset(str(claims.get("scope", "")).split())
    return CurrentUser(id=user_id, scopes=scopes)


UserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_scope(
    required: str,
) -> Callable[[UserDep], Coroutine[Any, Any, CurrentUser]]:
    async def dependency(user: UserDep) -> CurrentUser:
        if required not in user.scopes:
            raise Forbidden(f"Missing scope: {required}")
        return user

    return dependency
```

`HTTPBearer` is enough for provider-issued tokens. Use
`OAuth2PasswordBearer(tokenUrl="/v1/auth/token")` when you own the token
endpoint and want Swagger's Authorize button to request a token; keep the same
verification logic.

## `app/domain/orders.py`

```python
from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
```

## `app/db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

## `app/db/models/order.py`

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.orders import OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=OrderStatus.PENDING,
        index=True,
    )
    total_cents: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

`values_callable` stores `"pending"`, not `"PENDING"`. Set `lazy="raise"` on
relationships and load them explicitly with `selectinload`/`joinedload`.

## `app/db/session.py`

```python
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
```

## `app/api/deps.py`

```python
from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.orders.repository import OrderRepository
from app.core.config import Settings


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.orders = OrderRepository(session)


async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session, session.begin():
        yield UnitOfWork(session)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


UowDep = Annotated[UnitOfWork, Depends(get_uow, scope="function")]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
```

`session.begin()` commits on success and rolls back on exception. `scope="function"`
closes the transaction before the response is sent, so a failed commit cannot
produce a false `201`. Keep repositories commit-free; a use case that must not be
atomic gets its own session or transaction design.

## `app/api/v1/orders/schemas.py`

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.orders import OrderStatus


class OrderLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=1_000)
    unit_price_cents: int = Field(ge=0)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines: list[OrderLineCreate] = Field(min_length=1, max_length=100)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    status: OrderStatus
    total_cents: int
    created_at: datetime


class OrderPage(BaseModel):
    items: list[OrderRead]
    next_offset: int | None = None
```

## `app/api/v1/orders/repository.py`

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    async def list_for_customer(
        self,
        customer_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Order]:
        statement = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result.all())
```

## `app/api/v1/orders/service.py`

```python
import uuid

from app.api.deps import UnitOfWork
from app.api.v1.orders.schemas import OrderCreate
from app.core.errors import Conflict, InvalidOrder, NotFound
from app.db.models.order import Order
from app.domain.orders import OrderStatus


async def create(
    uow: UnitOfWork,
    payload: OrderCreate,
    *,
    customer_id: uuid.UUID,
) -> Order:
    total_cents = sum(
        line.quantity * line.unit_price_cents for line in payload.lines
    )
    if total_cents <= 0:
        raise InvalidOrder("Order total must be positive")

    order = Order(customer_id=customer_id, total_cents=total_cents)
    uow.session.add(order)
    await uow.session.flush()
    await uow.session.refresh(order)
    return order


async def cancel(
    uow: UnitOfWork,
    order_id: uuid.UUID,
    *,
    customer_id: uuid.UUID,
) -> Order:
    order = await get_for_customer(uow, order_id, customer_id=customer_id)
    if order.status is not OrderStatus.PENDING:
        raise Conflict("Only pending orders can be cancelled")

    order.status = OrderStatus.CANCELLED
    await uow.session.flush()
    return order


async def get_for_customer(
    uow: UnitOfWork,
    order_id: uuid.UUID,
    *,
    customer_id: uuid.UUID,
) -> Order:
    order = await uow.orders.get(order_id)
    if order is None or order.customer_id != customer_id:
        raise NotFound("Order not found")
    return order
```

## `app/api/v1/orders/router.py`

```python
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import UowDep
from app.api.v1.orders import service
from app.api.v1.orders.schemas import OrderCreate, OrderPage, OrderRead
from app.core.security import UserDep

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    response: Response,
    uow: UowDep,
    user: UserDep,
) -> OrderRead:
    order = await service.create(uow, payload, customer_id=user.id)
    response.headers["Location"] = f"/v1/orders/{order.id}"
    return OrderRead.model_validate(order)


@router.get("", response_model=OrderPage)
async def list_orders(
    uow: UowDep,
    user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrderPage:
    orders = await uow.orders.list_for_customer(
        user.id, limit=limit, offset=offset
    )
    next_offset = offset + len(orders) if len(orders) == limit else None
    return OrderPage(
        items=[OrderRead.model_validate(order) for order in orders],
        next_offset=next_offset,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: uuid.UUID,
    uow: UowDep,
    user: UserDep,
) -> OrderRead:
    order = await service.get_for_customer(
        uow, order_id, customer_id=user.id
    )
    return OrderRead.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: uuid.UUID,
    uow: UowDep,
    user: UserDep,
) -> OrderRead:
    order = await service.cancel(uow, order_id, customer_id=user.id)
    return OrderRead.model_validate(order)
```

The ownership check lives in the service so every caller gets it. Returning `404`
for another user's order avoids leaking that the order exists.

## `app/api/v1/router.py`

```python
from fastapi import APIRouter

from app.api.v1.orders.router import router as orders_router

api_router = APIRouter()
api_router.include_router(orders_router)
```

## `app/factory.py`

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import install_exception_handlers
from app.db.session import build_engine, build_sessionmaker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = build_engine(
        settings.database_url, echo=settings.environment == "local"
    )
    app.state.engine = engine
    app.state.sessionmaker = build_sessionmaker(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        )

    install_exception_handlers(app)
    app.include_router(api_router, prefix="/v1")

    @app.get("/health/live", tags=["health"], include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

## `app/main.py`

```python
from app.factory import create_app

app = create_app()
```

Tests import `create_app` from `app.factory`, so they never require production
environment variables at import time. The server imports `app.main:app`.

## Run

```sh
uv run fastapi dev src/app/main.py
```

Production: `uvicorn app.main:app --workers 4 --proxy-headers`, with migrations
run separately.

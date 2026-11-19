"""Shared test fixtures.

Health tests do not need a database. Integration tests use a dedicated PostgreSQL
database (``schoolops_test`` by default) that is created once per session and truncated
between tests. Each integration test gets an authenticated admin client unless it asks
for the anonymous one.
"""

import asyncio
import os
import re
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from schoolops.core.config import Settings
from schoolops.core.rate_limit import login_rate_limiter
from schoolops.core.security import hash_password
from schoolops.db import models  # noqa: F401  (registers every table)
from schoolops.db.base import Base
from schoolops.db.models import User
from schoolops.domain.enums import UserRole
from schoolops.factory import create_app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://schoolops:schoolops@localhost:5433/schoolops_test",
)

ADMIN_EMAIL = "admin@cbsg.org"
ADMIN_PASSWORD = "admin-password-123"
ADMIN_PASSWORD_HASH = hash_password(ADMIN_PASSWORD)


async def _create_database_if_missing() -> None:
    url = make_url(TEST_DATABASE_URL)
    database = url.database or ""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database):
        raise RuntimeError(f"Unsafe test database name: {database!r}")

    admin_engine = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": database},
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await admin_engine.dispose()


async def _prepare_database() -> None:
    await _create_database_if_missing()
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


async def _truncate_all_tables() -> None:
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()


async def insert_user(
    email: str,
    password_hash: str,
    role: UserRole,
    *,
    is_active: bool = True,
) -> None:
    """Insert a user directly; there is deliberately no public registration route."""
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        async with sessionmaker() as session:
            session.add(
                User(
                    email=email.lower(),
                    password_hash=password_hash,
                    role=role,
                    is_active=is_active,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_schema() -> None:
    """Create the test database and schema once per test session."""
    asyncio.run(_prepare_database())


@pytest.fixture
async def prepared_database(database_schema: None) -> None:
    """Clean the test schema and seed the admin account."""
    await _truncate_all_tables()
    login_rate_limiter.clear()
    await insert_user(ADMIN_EMAIL, ADMIN_PASSWORD_HASH, UserRole.ADMIN)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to a fresh app instance with lifespan running."""
    app = create_app(Settings(environment="test"))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


@pytest.fixture
async def anonymous_client(prepared_database: None) -> AsyncIterator[AsyncClient]:
    """A client with no Authorization header, for login and 401 contract tests."""
    app = create_app(Settings(environment="test", database_url=TEST_DATABASE_URL))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


@pytest.fixture
async def api_client(anonymous_client: AsyncClient) -> AsyncClient:
    """The admin client used by feature tests, already authenticated."""
    response = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    anonymous_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return anonymous_client


@pytest.fixture
async def db_session(prepared_database: None) -> AsyncIterator[AsyncSession]:
    """Direct database access for arranging users and other fixture data."""
    engine = create_async_engine(TEST_DATABASE_URL)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as session:
            yield session
    finally:
        await engine.dispose()

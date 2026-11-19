"""Async engine and session factories.

Engines are created once per process in the application lifespan, never at import time.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str) -> AsyncEngine:
    """Create the async engine with production-safe defaults."""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory that keeps objects usable after commit."""
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

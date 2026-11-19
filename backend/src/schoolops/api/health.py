"""Liveness and readiness probes (unauthenticated, cheap)."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    """Return 200 while the process can serve requests."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe", response_model=None)
async def ready(request: Request) -> dict[str, str] | JSONResponse:
    """Return 200 when the database is reachable, 503 otherwise."""
    try:
        async with request.app.state.sessionmaker() as session:
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        logger.warning("Readiness check failed: database unreachable", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}

"""Domain errors and RFC 9457 Problem Details exception handlers."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base class for expected business-rule failures."""

    status_code: int = 400
    title: str = "Bad request"
    type_uri: str = "about:blank"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class UnauthorizedError(DomainError):
    status_code = 401
    title = "Unauthorized"
    headers: dict[str, str] | None = {"WWW-Authenticate": "Bearer"}  # noqa: RUF012


class ForbiddenError(DomainError):
    status_code = 403
    title = "Forbidden"


class NotFoundError(DomainError):
    status_code = 404
    title = "Not found"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflict"


class UnprocessableError(DomainError):
    """Semantic validation failure that is not a field-format error."""

    status_code = 422
    title = "Unprocessable entity"


class TooManyRequestsError(DomainError):
    status_code = 429
    title = "Too many requests"

    def __init__(self, detail: str, *, retry_after: int) -> None:
        super().__init__(detail)
        self.headers = {"Retry-After": str(retry_after)}


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    errors: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build an ``application/problem+json`` response."""
    content: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if errors is not None:
        content["errors"] = errors
    return JSONResponse(
        status_code=status,
        content=content,
        media_type="application/problem+json",
        headers=headers,
    )


def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def install_exception_handlers(app: FastAPI) -> None:
    """Register handlers so every error uses one envelope."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return problem_response(
            request,
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            type_uri=exc.type_uri,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            request,
            status=422,
            title="Validation error",
            detail="Request validation failed.",
            errors=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else _status_title(exc.status_code)
        return problem_response(
            request,
            status=exc.status_code,
            title=_status_title(exc.status_code),
            detail=detail,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return problem_response(
            request,
            status=500,
            title="Internal server error",
            detail="An unexpected error occurred.",
        )

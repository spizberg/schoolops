"""HTTP hardening middleware: request context, security headers, and body limits."""

import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from schoolops.core.errors import problem_response
from schoolops.core.request_context import reset_request_id, set_request_id

logger = logging.getLogger("schoolops.http")

_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the request, and write one structured log line."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID_RE.fullmatch(supplied) else uuid4().hex
        set_request_id(request_id)
        request.state.request_id = request_id
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            logger.exception(
                "request.failed",
                extra={
                    "request_id": request_id,
                    "http": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": 500,
                        "duration_ms": duration_ms,
                    },
                },
            )
            reset_request_id()
            raise

        duration_ms = round((perf_counter() - started) * 1000, 2)
        http = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        if response.status_code >= 500:
            logger.error("request.completed", extra={"request_id": request_id, "http": http})
        elif response.status_code >= 400:
            logger.warning("request.completed", extra={"request_id": request_id, "http": http})
        else:
            logger.info("request.completed", extra={"request_id": request_id, "http": http})

        response.headers["X-Request-ID"] = request_id
        reset_request_id()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative headers to every API response."""

    def __init__(self, app: ASGIApp, *, environment: str) -> None:
        super().__init__(app)
        self.environment = environment

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(("/v1", "/health")):
            response.headers.setdefault("Cache-Control", "no-store")
        if self.environment == "production":
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            )
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the configured limit."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > self.max_bytes:
                return problem_response(
                    request,
                    status=413,
                    title="Payload too large",
                    detail="The request body is too large.",
                )
        return await call_next(request)


__all__ = [
    "SECURITY_HEADERS",
    "BodyLimitMiddleware",
    "RequestContextMiddleware",
    "SecurityHeadersMiddleware",
]

"""Hardening contracts: headers, request ids, body limits, and production settings."""

import logging
from typing import Any, cast

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from schoolops.core.config import Settings
from schoolops.factory import create_app


async def test_security_headers_and_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert "content-security-policy" not in response.headers


async def test_invalid_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "bad id with spaces"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad id with spaces"
    assert len(response.headers["x-request-id"]) == 32


async def test_request_log_is_structured_and_correlated(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="schoolops.http"):
        response = await client.get("/health/live?probe=1", headers={"X-Request-ID": "log-test"})

    assert response.status_code == 200
    record = next(item for item in caplog.records if item.message == "request.completed")
    captured = cast(Any, record)
    assert captured.request_id == "log-test"
    assert captured.http["method"] == "GET"
    assert captured.http["path"] == "/health/live"
    assert captured.http["status"] == 200
    assert captured.http["duration_ms"] >= 0


async def test_oversized_body_is_rejected() -> None:
    app = create_app(Settings(environment="test", max_request_body_bytes=10))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/login",
                content="x" * 11,
                headers={"content-type": "application/json"},
            )

    assert response.status_code == 413
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.json()["title"] == "Payload too large"


def test_production_requires_a_real_secret_and_no_debug() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")

    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="x" * 32, debug=True)

    settings = Settings(environment="production", jwt_secret="x" * 32)
    assert settings.environment == "production"
    assert settings.jwt_algorithm == "HS256"


async def test_production_security_headers() -> None:
    app = create_app(Settings(environment="production", jwt_secret="x" * 32))
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")

    assert response.status_code == 200
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "max-age=31536000" in response.headers["strict-transport-security"]

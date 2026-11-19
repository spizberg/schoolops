"""Authentication, authorization, and token contract tests."""

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core.config import Settings
from schoolops.core.security import create_access_token
from schoolops.db.models import User
from schoolops.domain.enums import UserRole
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_PASSWORD_HASH, insert_user


async def test_login_returns_a_bearer_token_and_me_returns_the_admin(
    anonymous_client: AsyncClient,
) -> None:
    response = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 8 * 60 * 60

    me = await anonymous_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    profile = me.json()
    assert profile["email"] == ADMIN_EMAIL
    assert profile["role"] == "admin"
    assert "password_hash" not in profile


async def test_login_rejects_wrong_password_without_leaking_details(
    anonymous_client: AsyncClient,
) -> None:
    response = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "Invalid email or password."


async def test_inactive_user_cannot_log_in(
    anonymous_client: AsyncClient, db_session: AsyncSession
) -> None:
    await insert_user(
        "inactive@cbsg.org",
        ADMIN_PASSWORD_HASH,
        UserRole.LEADER,
        is_active=False,
    )

    response = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": "inactive@cbsg.org", "password": ADMIN_PASSWORD},
    )

    assert response.status_code == 401


async def test_feature_routes_require_a_token(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.get("/v1/volunteers")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_invalid_and_unknown_tokens_are_rejected(
    anonymous_client: AsyncClient,
) -> None:
    malformed = await anonymous_client.get(
        "/v1/volunteers", headers={"Authorization": "Bearer not-a-token"}
    )
    assert malformed.status_code == 401

    settings = Settings(environment="test")
    token, _ = create_access_token(
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
        role=UserRole.ADMIN,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=60,
    )
    unknown = await anonymous_client.get(
        "/v1/volunteers", headers={"Authorization": f"Bearer {token}"}
    )
    assert unknown.status_code == 401


async def test_expired_tokens_are_rejected(
    anonymous_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await db_session.scalar(select(User).where(User.email == ADMIN_EMAIL))
    assert admin is not None

    settings = Settings(environment="test")
    token, _ = create_access_token(
        user_id=admin.id,
        role=admin.role,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=-1,
    )

    response = await anonymous_client.get(
        "/v1/volunteers", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


async def test_non_admin_roles_are_forbidden(
    anonymous_client: AsyncClient, db_session: AsyncSession
) -> None:
    await insert_user("leader@cbsg.org", ADMIN_PASSWORD_HASH, UserRole.LEADER)

    login = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": "leader@cbsg.org", "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = await anonymous_client.get(
        "/v1/volunteers", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This action requires the admin role."


async def test_login_is_rate_limited(anonymous_client: AsyncClient) -> None:
    payload = {"email": ADMIN_EMAIL, "password": "wrong-password"}
    for _ in range(5):
        response = await anonymous_client.post("/v1/auth/login", json=payload)
        assert response.status_code == 401

    blocked = await anonymous_client.post("/v1/auth/login", json=payload)

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0

    # Even the correct password is refused while the window is open.
    correct = await anonymous_client.post(
        "/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert correct.status_code == 429

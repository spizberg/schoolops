"""Login rules: credential checking, rate limiting, and token issuance."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core.config import Settings
from schoolops.core.errors import TooManyRequestsError, UnauthorizedError
from schoolops.core.rate_limit import login_rate_limiter
from schoolops.core.security import create_access_token, verify_password
from schoolops.db.models import User

from .schemas import LoginRequest, TokenResponse


async def _authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user


async def login(
    session: AsyncSession,
    payload: LoginRequest,
    *,
    client_ip: str,
    settings: Settings,
) -> TokenResponse:
    """Authenticate and issue a bearer token, with a generic failure message."""
    key = f"{client_ip}:{str(payload.email).lower()}"
    retry_after = login_rate_limiter.retry_after(key)
    if retry_after is not None:
        raise TooManyRequestsError(
            "Too many login attempts. Try again later.", retry_after=retry_after
        )

    user = await _authenticate(session, str(payload.email), payload.password)
    if user is None:
        login_rate_limiter.record_failure(key)
        raise UnauthorizedError("Invalid email or password.")

    login_rate_limiter.reset(key)
    token, expires_in = create_access_token(
        user_id=user.id,
        role=user.role,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        ttl_minutes=settings.access_token_ttl_minutes,
    )
    return TokenResponse(access_token=token, expires_in=expires_in)

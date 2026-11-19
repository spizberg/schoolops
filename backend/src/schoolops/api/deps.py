"""Shared FastAPI dependencies, including authentication and role checks."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core.audit import ACTOR_KEY
from schoolops.core.errors import ForbiddenError, UnauthorizedError
from schoolops.core.security import InvalidTokenError, decode_access_token
from schoolops.db.models import User
from schoolops.domain.enums import UserRole


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one session per request from the lifespan-owned factory."""
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

_bearer = HTTPBearer(auto_error=False, description="JWT returned by /v1/auth/login")


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    """Validate the bearer token and load the active user from the database."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication is required.")

    settings = request.app.state.settings
    try:
        token = decode_access_token(
            credentials.credentials,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired access token.")
    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
    session: SessionDep,
) -> User:
    """Only administrators are enabled in the MVP; other roles are modeled already."""
    if user.role is not UserRole.ADMIN:
        raise ForbiddenError("This action requires the admin role.")
    session.info[ACTOR_KEY] = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_current_admin)]

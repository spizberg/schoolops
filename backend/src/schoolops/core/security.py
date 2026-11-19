"""Password hashing and JWT helpers.

Passwords use Argon2id through ``pwdlib``. Tokens are HS256 JWTs carrying ``sub``,
``role``, ``iat``, and ``exp``; only the subject is trusted for identity, while the role
is reloaded from the database on every request.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from schoolops.domain.enums import UserRole

_password_hash = PasswordHash.recommended()


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired, or has the wrong claims."""


@dataclass(frozen=True)
class TokenData:
    user_id: UUID
    role: UserRole


def hash_password(password: str) -> str:
    """Return an Argon2id hash. The plaintext is never stored."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password without leaking failure details."""
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:  # a malformed hash must fail closed
        return False


def create_access_token(
    *,
    user_id: UUID,
    role: UserRole,
    secret: str,
    algorithm: str,
    ttl_minutes: int,
) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for an authenticated user."""
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": expires,
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token, ttl_minutes * 60


def decode_access_token(token: str, *, secret: str, algorithm: str) -> TokenData:
    """Validate signature and required claims, then return the token subject."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
        user_id = UUID(str(payload["sub"]))
        role = UserRole(str(payload["role"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidTokenError("Invalid or expired access token.") from exc
    return TokenData(user_id=user_id, role=role)

"""Application users and their roles."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schoolops.db.models._types import str_enum
from schoolops.domain.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An account that can authenticate. Passwords are stored only as Argon2id hashes."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.ADMIN,
        server_default=UserRole.ADMIN.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

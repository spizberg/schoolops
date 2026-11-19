"""Guardian contact details, optionally grouped into a household."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Guardian(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An adult who can be contacted about one or more children."""

    __tablename__ = "guardians"

    household_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

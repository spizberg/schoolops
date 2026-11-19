"""Households group siblings and share an address."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Household(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A family grouping. The name is optional; address and notes are free text."""

    __tablename__ = "households"

    name: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

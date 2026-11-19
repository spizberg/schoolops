"""Dates inside a ministry year on which classes do not meet."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schoolops.db.models._types import str_enum
from schoolops.domain.enums import NoClassDayKind


class NoClassDay(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Holiday, church closure, or other date with no classes."""

    __tablename__ = "no_class_days"

    ministry_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("ministry_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[NoClassDayKind] = mapped_column(
        str_enum(NoClassDayKind, name="no_class_day_kind"),
        nullable=False,
        default=NoClassDayKind.CLOSURE,
        server_default=NoClassDayKind.CLOSURE.value,
    )

    __table_args__ = (
        UniqueConstraint("ministry_year_id", "date", name="uq_no_class_days_year_date"),
    )

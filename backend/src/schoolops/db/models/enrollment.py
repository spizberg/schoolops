"""Dated association between a child and a class."""

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from schoolops.db.models.child import Child


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A child's membership in a class; ended rather than deleted."""

    __tablename__ = "enrollments"

    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)

    child: Mapped["Child"] = orm_relationship(lazy="raise")

    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_not_before_start"),
        Index(
            "uq_enrollments_open_child_class",
            "child_id",
            "class_id",
            unique=True,
            postgresql_where=text("end_date IS NULL"),
        ),
    )

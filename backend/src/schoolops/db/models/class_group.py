"""Age-band classes within a ministry year."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClassGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A class belongs to one ministry year and may have a lead volunteer."""

    __tablename__ = "classes"

    ministry_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("ministry_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age_band: Mapped[str] = mapped_column(String(50), nullable=False)
    age_min: Mapped[int | None] = mapped_column(SmallInteger)
    age_max: Mapped[int | None] = mapped_column(SmallInteger)
    lead_volunteer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("volunteers.id", ondelete="SET NULL"), index=True
    )
    room: Mapped[str | None] = mapped_column(String(50))
    capacity: Mapped[int | None] = mapped_column(SmallInteger)
    curriculum: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("ministry_year_id", "name", name="uq_classes_year_name"),
        CheckConstraint(
            "age_min IS NULL OR age_max IS NULL OR age_min <= age_max",
            name="age_range_valid",
        ),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="capacity_positive"),
    )

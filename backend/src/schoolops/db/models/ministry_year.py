"""Ministry years and their meeting-week configuration."""

from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MinistryYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named period that scopes classes and defines the meeting week."""

    __tablename__ = "ministry_years"

    label: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    meeting_weekdays: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger),
        nullable=False,
        default=lambda: [7],
        server_default=text("'{7}'::smallint[]"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    __table_args__ = (
        CheckConstraint("start_date < end_date", name="start_before_end"),
        CheckConstraint("cardinality(meeting_weekdays) > 0", name="weekdays_not_empty"),
        Index(
            "uq_ministry_years_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

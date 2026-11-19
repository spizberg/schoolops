"""Class sessions, session volunteers, and attendance records."""

from datetime import date, time
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schoolops.db.models._types import str_enum
from schoolops.domain.enums import AttendanceStatus


class ClassSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One meeting of a class. Owns the lesson content and resources."""

    __tablename__ = "class_sessions"

    class_id: Mapped[UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    resources: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    __table_args__ = (
        UniqueConstraint("class_id", "date", "start_time", name="uq_sessions_class_date_start"),
        CheckConstraint("start_time < end_time", name="start_before_end"),
    )


class SessionVolunteer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A volunteer who served a particular session."""

    __tablename__ = "session_volunteers"

    class_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volunteer_id: Mapped[UUID] = mapped_column(
        ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("class_session_id", "volunteer_id", name="uq_session_volunteers_link"),
    )


class AttendanceRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A child's attendance for one session, or a named one-off visitor."""

    __tablename__ = "attendance_records"

    class_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("children.id", ondelete="RESTRICT"), index=True
    )
    visitor_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[AttendanceStatus] = mapped_column(
        str_enum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        CheckConstraint(
            "(child_id IS NOT NULL) <> (visitor_name IS NOT NULL)",
            name="child_or_visitor",
        ),
        Index(
            "uq_attendance_session_child",
            "class_session_id",
            "child_id",
            unique=True,
            postgresql_where=text("child_id IS NOT NULL"),
        ),
    )

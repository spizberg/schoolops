"""Children in the ministry, with the safety information needed on a Sunday."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schoolops.db.models._types import str_enum
from schoolops.domain.enums import ChildStatus, PhotoConsent


class Child(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A child. Date of birth is required for age-band grouping and promotion."""

    __tablename__ = "children"

    household_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="SET NULL"), index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(50))
    allergies: Mapped[str | None] = mapped_column(Text)
    medical_notes: Mapped[str | None] = mapped_column(Text)
    photo_consent: Mapped[PhotoConsent] = mapped_column(
        str_enum(PhotoConsent, name="photo_consent"),
        nullable=False,
        default=PhotoConsent.NOT_RECORDED,
        server_default=PhotoConsent.NOT_RECORDED.value,
    )
    status: Mapped[ChildStatus] = mapped_column(
        str_enum(ChildStatus, name="child_status"),
        nullable=False,
        default=ChildStatus.ACTIVE,
        server_default=ChildStatus.ACTIVE.value,
    )
    joined_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

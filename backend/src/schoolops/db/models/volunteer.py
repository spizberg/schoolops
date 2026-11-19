"""Volunteers who serve in the children's ministry."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from schoolops.db.models._types import str_enum
from schoolops.domain.enums import VolunteerStatus


class Volunteer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An adult volunteer. Phone is required; email is optional."""

    __tablename__ = "volunteers"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    joined_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[VolunteerStatus] = mapped_column(
        str_enum(VolunteerStatus, name="volunteer_status"),
        nullable=False,
        default=VolunteerStatus.ACTIVE,
        server_default=VolunteerStatus.ACTIVE.value,
    )

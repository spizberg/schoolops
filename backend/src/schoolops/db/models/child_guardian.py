"""Links between a child and a guardian."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from schoolops.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from schoolops.db.models.guardian import Guardian


class ChildGuardian(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A guardian's relationship to one child, with primary/emergency flags."""

    __tablename__ = "child_guardians"

    child_id: Mapped[UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guardian_id: Mapped[UUID] = mapped_column(
        ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_emergency: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    guardian: Mapped["Guardian"] = orm_relationship(lazy="raise")

    __table_args__ = (
        UniqueConstraint("child_id", "guardian_id", name="uq_child_guardians_link"),
        Index(
            "uq_child_guardians_one_primary",
            "child_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

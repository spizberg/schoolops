"""Volunteer rules. Deactivation preserves class and session history."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import Volunteer
from schoolops.domain.enums import VolunteerStatus

from .schemas import VolunteerCreate, VolunteerUpdate

_FIELDS = ("first_name", "last_name", "phone", "email", "joined_on", "status")


async def get_volunteer(session: AsyncSession, volunteer_id: UUID) -> Volunteer:
    volunteer = await session.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise NotFoundError(f"Volunteer {volunteer_id} was not found.")
    return volunteer


async def list_volunteers(
    session: AsyncSession,
    *,
    q: str | None,
    status: VolunteerStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[Volunteer], int]:
    stmt = select(Volunteer)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Volunteer.first_name.ilike(pattern),
                Volunteer.last_name.ilike(pattern),
                Volunteer.phone.ilike(pattern),
                Volunteer.email.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Volunteer.status == status)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    volunteers = (
        await session.scalars(
            stmt.order_by(Volunteer.last_name, Volunteer.first_name).limit(limit).offset(offset)
        )
    ).all()
    return list(volunteers), total


async def _assert_email_available(
    session: AsyncSession, email: str, *, exclude_id: UUID | None = None
) -> None:
    stmt = select(Volunteer.id).where(Volunteer.email == email)
    if exclude_id is not None:
        stmt = stmt.where(Volunteer.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError(f"A volunteer with email '{email}' already exists.")


async def create_volunteer(session: AsyncSession, payload: VolunteerCreate) -> Volunteer:
    email = str(payload.email).strip().lower() if payload.email is not None else None
    if email is not None:
        await _assert_email_available(session, email)

    volunteer = Volunteer(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=email,
        joined_on=payload.joined_on,
        status=payload.status,
    )
    session.add(volunteer)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="volunteer",
        entity_id=volunteer.id,
        changes={"after": audit.snapshot(volunteer, _FIELDS)},
    )
    await session.commit()
    return volunteer


async def update_volunteer(
    session: AsyncSession, volunteer: Volunteer, payload: VolunteerUpdate
) -> Volunteer:
    data = payload.model_dump(exclude_unset=True)
    for field in ("first_name", "last_name", "phone", "status"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    if "email" in data:
        email = str(data["email"]).strip().lower() if data["email"] is not None else None
        if email is not None:
            await _assert_email_available(session, email, exclude_id=volunteer.id)
        data["email"] = email

    before = audit.snapshot(volunteer, _FIELDS)
    for field, value in data.items():
        setattr(volunteer, field, value)
    changes = audit.diff(before, audit.snapshot(volunteer, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="volunteer",
            entity_id=volunteer.id,
            changes={"changes": changes},
        )
    await session.commit()
    return volunteer


async def deactivate_volunteer(session: AsyncSession, volunteer: Volunteer) -> None:
    """``DELETE`` archives the volunteer; history is preserved."""
    before = audit.snapshot(volunteer, _FIELDS)
    volunteer.status = VolunteerStatus.INACTIVE
    changes = audit.diff(before, audit.snapshot(volunteer, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="volunteer",
            entity_id=volunteer.id,
            changes={"changes": changes},
        )
    await session.commit()

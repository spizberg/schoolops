"""Guardian and child-guardian link rules."""

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import Child, ChildGuardian, Guardian, Household

from .schemas import (
    ChildGuardianCreate,
    ChildGuardianUpdate,
    GuardianCreate,
    GuardianUpdate,
)

_GUARDIAN_FIELDS = (
    "household_id",
    "first_name",
    "last_name",
    "phone",
    "email",
    "notes",
)
_LINK_FIELDS = ("child_id", "guardian_id", "relationship", "is_primary", "is_emergency")


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = str(email).strip().lower()
    return normalized or None


async def get_guardian(session: AsyncSession, guardian_id: UUID) -> Guardian:
    guardian = await session.get(Guardian, guardian_id)
    if guardian is None:
        raise NotFoundError(f"Guardian {guardian_id} was not found.")
    return guardian


async def list_guardians(
    session: AsyncSession,
    *,
    q: str | None,
    household_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Guardian], int]:
    stmt = select(Guardian)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Guardian.first_name.ilike(pattern),
                Guardian.last_name.ilike(pattern),
                Guardian.phone.ilike(pattern),
                Guardian.email.ilike(pattern),
            )
        )
    if household_id is not None:
        stmt = stmt.where(Guardian.household_id == household_id)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    guardians = (
        await session.scalars(
            stmt.order_by(Guardian.last_name, Guardian.first_name).limit(limit).offset(offset)
        )
    ).all()
    return list(guardians), total


async def _assert_household_exists(session: AsyncSession, household_id: UUID | None) -> None:
    if household_id is None:
        return
    if await session.get(Household, household_id) is None:
        raise NotFoundError(f"Household {household_id} was not found.")


async def create_guardian(session: AsyncSession, payload: GuardianCreate) -> Guardian:
    await _assert_household_exists(session, payload.household_id)
    guardian = Guardian(
        household_id=payload.household_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=_normalize_email(payload.email),
        notes=payload.notes,
    )
    session.add(guardian)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="guardian",
        entity_id=guardian.id,
        changes={"after": audit.snapshot(guardian, _GUARDIAN_FIELDS)},
    )
    await session.commit()
    return guardian


async def update_guardian(
    session: AsyncSession, guardian: Guardian, payload: GuardianUpdate
) -> Guardian:
    data = payload.model_dump(exclude_unset=True)
    for field in ("first_name", "last_name", "phone"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    if "household_id" in data:
        await _assert_household_exists(session, data["household_id"])
    if "email" in data:
        data["email"] = _normalize_email(data["email"])
    before = audit.snapshot(guardian, _GUARDIAN_FIELDS)
    for field, value in data.items():
        setattr(guardian, field, value)
    changes = audit.diff(before, audit.snapshot(guardian, _GUARDIAN_FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="guardian",
            entity_id=guardian.id,
            changes={"changes": changes},
        )
    await session.commit()
    return guardian


async def delete_guardian(session: AsyncSession, guardian: Guardian) -> None:
    before = audit.snapshot(guardian, _GUARDIAN_FIELDS)
    await session.delete(guardian)
    await audit.record(
        session,
        action="delete",
        entity_type="guardian",
        entity_id=guardian.id,
        changes={"before": before},
    )
    await session.commit()


async def _attach_guardian(session: AsyncSession, link: ChildGuardian) -> ChildGuardian:
    guardian = await session.get(Guardian, link.guardian_id)
    if guardian is not None:
        link.guardian = guardian
    return link


async def get_child_guardian(session: AsyncSession, link_id: UUID) -> ChildGuardian:
    link = await session.get(ChildGuardian, link_id)
    if link is None:
        raise NotFoundError(f"Child guardian link {link_id} was not found.")
    return await _attach_guardian(session, link)


async def list_child_guardians(session: AsyncSession, child_id: UUID) -> list[ChildGuardian]:
    links = (
        await session.scalars(
            select(ChildGuardian)
            .where(ChildGuardian.child_id == child_id)
            .options(selectinload(ChildGuardian.guardian))
            .order_by(
                ChildGuardian.is_primary.desc(),
                ChildGuardian.is_emergency.desc(),
            )
        )
    ).all()
    return list(links)


async def _clear_primary(
    session: AsyncSession, child_id: UUID, *, exclude_id: UUID | None = None
) -> None:
    stmt = update(ChildGuardian).where(
        ChildGuardian.child_id == child_id,
        ChildGuardian.is_primary.is_(True),
    )
    if exclude_id is not None:
        stmt = stmt.where(ChildGuardian.id != exclude_id)
    await session.execute(stmt.values(is_primary=False))


async def create_child_guardian(
    session: AsyncSession, child: Child, payload: ChildGuardianCreate
) -> ChildGuardian:
    guardian = await get_guardian(session, payload.guardian_id)
    duplicate = await session.scalar(
        select(ChildGuardian.id).where(
            ChildGuardian.child_id == child.id,
            ChildGuardian.guardian_id == guardian.id,
        )
    )
    if duplicate is not None:
        raise ConflictError("This guardian is already linked to the child.")

    if payload.is_primary:
        await _clear_primary(session, child.id)

    link = ChildGuardian(
        child_id=child.id,
        guardian_id=guardian.id,
        relationship=payload.relationship,
        is_primary=payload.is_primary,
        is_emergency=payload.is_emergency,
    )
    session.add(link)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="child_guardian",
        entity_id=link.id,
        changes={"after": audit.snapshot(link, _LINK_FIELDS)},
    )
    await session.commit()
    return await _attach_guardian(session, link)


async def update_child_guardian(
    session: AsyncSession, link: ChildGuardian, payload: ChildGuardianUpdate
) -> ChildGuardian:
    data = payload.model_dump(exclude_unset=True)
    for field in ("relationship", "is_primary", "is_emergency"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    if data.get("is_primary") is True:
        await _clear_primary(session, link.child_id, exclude_id=link.id)
    before = audit.snapshot(link, _LINK_FIELDS)
    for field, value in data.items():
        setattr(link, field, value)
    changes = audit.diff(before, audit.snapshot(link, _LINK_FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="child_guardian",
            entity_id=link.id,
            changes={"changes": changes},
        )
    await session.commit()
    return await _attach_guardian(session, link)


async def set_primary(session: AsyncSession, link: ChildGuardian) -> ChildGuardian:
    await _clear_primary(session, link.child_id, exclude_id=link.id)
    before = audit.snapshot(link, _LINK_FIELDS)
    link.is_primary = True
    changes = audit.diff(before, audit.snapshot(link, _LINK_FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="child_guardian",
            entity_id=link.id,
            changes={"changes": changes},
        )
    await session.commit()
    return await _attach_guardian(session, link)


async def delete_child_guardian(session: AsyncSession, link: ChildGuardian) -> None:
    before = audit.snapshot(link, _LINK_FIELDS)
    await session.delete(link)
    await audit.record(
        session,
        action="delete",
        entity_type="child_guardian",
        entity_id=link.id,
        changes={"before": before},
    )
    await session.commit()

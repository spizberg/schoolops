"""Household rules."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import NotFoundError
from schoolops.db.models import Household

from .schemas import HouseholdCreate, HouseholdUpdate

_FIELDS = ("name", "address", "notes")


async def get_household(session: AsyncSession, household_id: UUID) -> Household:
    household = await session.get(Household, household_id)
    if household is None:
        raise NotFoundError(f"Household {household_id} was not found.")
    return household


async def list_households(
    session: AsyncSession,
    *,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Household], int]:
    stmt = select(Household)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Household.name.ilike(pattern), Household.address.ilike(pattern)))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    households = (
        await session.scalars(
            stmt.order_by(Household.name, Household.id).limit(limit).offset(offset)
        )
    ).all()
    return list(households), total


async def create_household(session: AsyncSession, payload: HouseholdCreate) -> Household:
    household = Household(
        name=payload.name,
        address=payload.address,
        notes=payload.notes,
    )
    session.add(household)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="household",
        entity_id=household.id,
        changes={"after": audit.snapshot(household, _FIELDS)},
    )
    await session.commit()
    return household


async def update_household(
    session: AsyncSession, household: Household, payload: HouseholdUpdate
) -> Household:
    before = audit.snapshot(household, _FIELDS)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(household, field, value)
    changes = audit.diff(before, audit.snapshot(household, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="household",
            entity_id=household.id,
            changes={"changes": changes},
        )
    await session.commit()
    return household

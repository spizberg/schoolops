"""Class rules: year scoping, unique names, and lead volunteer assignment."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import (
    ClassGroup,
    ClassSession,
    Enrollment,
    MinistryYear,
    Volunteer,
)
from schoolops.domain.enums import VolunteerStatus

from .schemas import ClassCreate, ClassUpdate

_FIELDS = (
    "ministry_year_id",
    "name",
    "age_band",
    "age_min",
    "age_max",
    "lead_volunteer_id",
    "room",
    "capacity",
    "curriculum",
)


async def get_class(session: AsyncSession, class_id: UUID) -> ClassGroup:
    school_class = await session.get(ClassGroup, class_id)
    if school_class is None:
        raise NotFoundError(f"Class {class_id} was not found.")
    return school_class


async def list_classes(
    session: AsyncSession,
    *,
    ministry_year_id: UUID | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ClassGroup], int]:
    stmt = select(ClassGroup)
    if ministry_year_id is not None:
        stmt = stmt.where(ClassGroup.ministry_year_id == ministry_year_id)
    if q:
        stmt = stmt.where(ClassGroup.name.ilike(f"%{q.strip()}%"))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    classes = (
        await session.scalars(stmt.order_by(ClassGroup.name).limit(limit).offset(offset))
    ).all()
    return list(classes), total


async def _assert_year_exists(session: AsyncSession, year_id: UUID) -> None:
    if await session.get(MinistryYear, year_id) is None:
        raise NotFoundError(f"Ministry year {year_id} was not found.")


async def _assert_volunteer_assignable(session: AsyncSession, volunteer_id: UUID | None) -> None:
    if volunteer_id is None:
        return
    volunteer = await session.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise NotFoundError(f"Volunteer {volunteer_id} was not found.")
    if volunteer.status is not VolunteerStatus.ACTIVE:
        raise UnprocessableError("An inactive volunteer cannot lead a class.")


def _assert_age_range(age_min: int | None, age_max: int | None) -> None:
    if age_min is not None and age_max is not None and age_min > age_max:
        raise UnprocessableError("Minimum age must not be greater than maximum age.")


async def _assert_name_available(
    session: AsyncSession,
    *,
    ministry_year_id: UUID,
    name: str,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(ClassGroup.id).where(
        ClassGroup.ministry_year_id == ministry_year_id,
        ClassGroup.name == name,
    )
    if exclude_id is not None:
        stmt = stmt.where(ClassGroup.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError(f"A class named '{name}' already exists in this ministry year.")


async def create_class(session: AsyncSession, payload: ClassCreate) -> ClassGroup:
    await _assert_year_exists(session, payload.ministry_year_id)
    await _assert_name_available(
        session, ministry_year_id=payload.ministry_year_id, name=payload.name
    )
    await _assert_volunteer_assignable(session, payload.lead_volunteer_id)
    _assert_age_range(payload.age_min, payload.age_max)

    school_class = ClassGroup(
        ministry_year_id=payload.ministry_year_id,
        name=payload.name,
        age_band=payload.age_band,
        age_min=payload.age_min,
        age_max=payload.age_max,
        lead_volunteer_id=payload.lead_volunteer_id,
        room=payload.room,
        capacity=payload.capacity,
        curriculum=payload.curriculum,
    )
    session.add(school_class)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="class",
        entity_id=school_class.id,
        changes={"after": audit.snapshot(school_class, _FIELDS)},
    )
    await session.commit()
    return school_class


async def update_class(
    session: AsyncSession, school_class: ClassGroup, payload: ClassUpdate
) -> ClassGroup:
    data = payload.model_dump(exclude_unset=True)
    for field in ("ministry_year_id", "name", "age_band"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    year_id = data.get("ministry_year_id", school_class.ministry_year_id)
    name = data.get("name", school_class.name)
    if "ministry_year_id" in data:
        await _assert_year_exists(session, year_id)
    if "ministry_year_id" in data or "name" in data:
        await _assert_name_available(
            session, ministry_year_id=year_id, name=name, exclude_id=school_class.id
        )
    if "lead_volunteer_id" in data:
        await _assert_volunteer_assignable(session, data["lead_volunteer_id"])

    _assert_age_range(
        data.get("age_min", school_class.age_min),
        data.get("age_max", school_class.age_max),
    )
    before = audit.snapshot(school_class, _FIELDS)
    for field, value in data.items():
        setattr(school_class, field, value)
    changes = audit.diff(before, audit.snapshot(school_class, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="class",
            entity_id=school_class.id,
            changes={"changes": changes},
        )
    await session.commit()
    return school_class


async def delete_class(session: AsyncSession, school_class: ClassGroup) -> None:
    enrolled = await session.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.class_id == school_class.id)
    )
    has_sessions = await session.scalar(
        select(func.count())
        .select_from(ClassSession)
        .where(ClassSession.class_id == school_class.id)
    )
    if enrolled or has_sessions:
        raise ConflictError("This class has enrollment or session history and cannot be deleted.")
    before = audit.snapshot(school_class, _FIELDS)
    await session.delete(school_class)
    await audit.record(
        session,
        action="delete",
        entity_type="class",
        entity_id=school_class.id,
        changes={"before": before},
    )
    await session.commit()

"""Enrollment rules: one active class per child per ministry year."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import Child, ClassGroup, Enrollment

from .schemas import EnrollmentCreate, EnrollmentUpdate

_FIELDS = ("child_id", "class_id", "start_date", "end_date")


async def get_enrollment(session: AsyncSession, enrollment_id: UUID) -> Enrollment:
    enrollment = await session.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise NotFoundError(f"Enrollment {enrollment_id} was not found.")
    return enrollment


async def _assert_no_overlap(
    session: AsyncSession,
    *,
    child_id: UUID,
    class_id: UUID,
    start_date: date,
    end_date: date | None,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(Enrollment.id).where(
        Enrollment.child_id == child_id,
        Enrollment.class_id == class_id,
        or_(Enrollment.end_date.is_(None), Enrollment.end_date >= start_date),
    )
    if end_date is not None:
        stmt = stmt.where(Enrollment.start_date <= end_date)
    if exclude_id is not None:
        stmt = stmt.where(Enrollment.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError("The child already has an enrollment in this class for that period.")


async def _assert_one_class_per_year(
    session: AsyncSession,
    *,
    child_id: UUID,
    ministry_year_id: UUID,
    start_date: date,
    exclude_id: UUID | None = None,
) -> None:
    stmt = (
        select(Enrollment.id)
        .join(ClassGroup, ClassGroup.id == Enrollment.class_id)
        .where(
            Enrollment.child_id == child_id,
            ClassGroup.ministry_year_id == ministry_year_id,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= start_date),
        )
    )
    if exclude_id is not None:
        stmt = stmt.where(Enrollment.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError("The child already has an active class in this ministry year.")


async def enroll_child(
    session: AsyncSession, school_class: ClassGroup, payload: EnrollmentCreate
) -> Enrollment:
    child = await session.get(Child, payload.child_id)
    if child is None:
        raise NotFoundError(f"Child {payload.child_id} was not found.")
    if payload.end_date is not None and payload.end_date < payload.start_date:
        raise UnprocessableError("The end date must not be before the start date.")

    await _assert_no_overlap(
        session,
        child_id=payload.child_id,
        class_id=school_class.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    await _assert_one_class_per_year(
        session,
        child_id=payload.child_id,
        ministry_year_id=school_class.ministry_year_id,
        start_date=payload.start_date,
    )

    enrollment = Enrollment(
        child_id=payload.child_id,
        class_id=school_class.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    session.add(enrollment)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="enrollment",
        entity_id=enrollment.id,
        changes={"after": audit.snapshot(enrollment, _FIELDS)},
    )
    await session.commit()
    return enrollment


async def list_roster(
    session: AsyncSession,
    school_class: ClassGroup,
    *,
    on_date: date,
    limit: int,
    offset: int,
) -> tuple[list[Enrollment], int]:
    """Enrollments active on ``on_date`` (inclusive)."""
    active = (
        Enrollment.class_id == school_class.id,
        Enrollment.start_date <= on_date,
        or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on_date),
    )
    total = await session.scalar(select(func.count()).select_from(Enrollment).where(*active)) or 0
    enrollments = (
        await session.scalars(
            select(Enrollment)
            .where(*active)
            .options(selectinload(Enrollment.child))
            .order_by(Enrollment.start_date)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(enrollments), total


async def update_enrollment(
    session: AsyncSession, enrollment: Enrollment, payload: EnrollmentUpdate
) -> Enrollment:
    data = payload.model_dump(exclude_unset=True)
    if "end_date" not in data:
        return enrollment

    end_date = data["end_date"]
    if end_date is not None:
        if end_date < enrollment.start_date:
            raise UnprocessableError("The end date must not be before the start date.")
        await _assert_no_overlap(
            session,
            child_id=enrollment.child_id,
            class_id=enrollment.class_id,
            start_date=enrollment.start_date,
            end_date=end_date,
            exclude_id=enrollment.id,
        )
    else:
        await _assert_no_overlap(
            session,
            child_id=enrollment.child_id,
            class_id=enrollment.class_id,
            start_date=enrollment.start_date,
            end_date=None,
            exclude_id=enrollment.id,
        )

    before = audit.snapshot(enrollment, _FIELDS)
    enrollment.end_date = end_date
    changes = audit.diff(before, audit.snapshot(enrollment, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="enrollment",
            entity_id=enrollment.id,
            changes={"changes": changes},
        )
    await session.commit()
    return enrollment


async def end_enrollment(session: AsyncSession, enrollment: Enrollment) -> None:
    """Remove a child from a class without deleting the historical record."""
    if enrollment.end_date is None:
        before = audit.snapshot(enrollment, _FIELDS)
        enrollment.end_date = max(date.today(), enrollment.start_date)
        changes = audit.diff(before, audit.snapshot(enrollment, _FIELDS))
        if changes:
            await audit.record(
                session,
                action="update",
                entity_type="enrollment",
                entity_id=enrollment.id,
                changes={"changes": changes},
            )
        await session.commit()

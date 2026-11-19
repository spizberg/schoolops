"""Child rules and guardian-count projection."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import NotFoundError, UnprocessableError
from schoolops.db.models import Child, ChildGuardian, ClassGroup, Enrollment, Household
from schoolops.domain.enums import ChildStatus

from .schemas import ChildCreate, ChildUpdate

_FIELDS = (
    "household_id",
    "first_name",
    "last_name",
    "date_of_birth",
    "grade",
    "allergies",
    "medical_notes",
    "photo_consent",
    "status",
    "joined_on",
    "notes",
)


async def _attach_guardian_counts(session: AsyncSession, children: list[Child]) -> None:
    if not children:
        return
    rows = (
        await session.execute(
            select(ChildGuardian.child_id, func.count())
            .where(ChildGuardian.child_id.in_([child.id for child in children]))
            .group_by(ChildGuardian.child_id)
        )
    ).all()
    counts = {child_id: count for child_id, count in rows}
    for child in children:
        setattr(child, "guardian_count", counts.get(child.id, 0))  # noqa: B010


async def get_child(session: AsyncSession, child_id: UUID) -> Child:
    child = await session.get(Child, child_id)
    if child is None:
        raise NotFoundError(f"Child {child_id} was not found.")
    await _attach_guardian_counts(session, [child])
    return child


async def list_children(
    session: AsyncSession,
    *,
    q: str | None,
    status: ChildStatus | None,
    household_id: UUID | None,
    class_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Child], int]:
    stmt = select(Child)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Child.first_name.ilike(pattern),
                Child.last_name.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Child.status == status)
    if household_id is not None:
        stmt = stmt.where(Child.household_id == household_id)
    if class_id is not None:
        stmt = stmt.where(
            Child.id.in_(
                select(Enrollment.child_id)
                .join(ClassGroup, ClassGroup.id == Enrollment.class_id)
                .where(ClassGroup.id == class_id)
            )
        )

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    children = (
        await session.scalars(
            stmt.order_by(Child.last_name, Child.first_name).limit(limit).offset(offset)
        )
    ).all()
    await _attach_guardian_counts(session, list(children))
    return list(children), total


async def _assert_household_exists(session: AsyncSession, household_id: UUID | None) -> None:
    if household_id is None:
        return
    if await session.get(Household, household_id) is None:
        raise NotFoundError(f"Household {household_id} was not found.")


async def create_child(session: AsyncSession, payload: ChildCreate) -> Child:
    await _assert_household_exists(session, payload.household_id)
    child = Child(
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        household_id=payload.household_id,
        grade=payload.grade,
        allergies=payload.allergies,
        medical_notes=payload.medical_notes,
        photo_consent=payload.photo_consent,
        status=payload.status,
        joined_on=payload.joined_on,
        notes=payload.notes,
    )
    session.add(child)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="child",
        entity_id=child.id,
        changes={"after": audit.snapshot(child, _FIELDS)},
    )
    await session.commit()
    setattr(child, "guardian_count", 0)  # noqa: B010
    return child


async def update_child(session: AsyncSession, child: Child, payload: ChildUpdate) -> Child:
    data = payload.model_dump(exclude_unset=True)
    for field in (
        "first_name",
        "last_name",
        "date_of_birth",
        "photo_consent",
        "status",
    ):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    if "household_id" in data:
        await _assert_household_exists(session, data["household_id"])

    before = audit.snapshot(child, _FIELDS)
    for field, value in data.items():
        setattr(child, field, value)
    changes = audit.diff(before, audit.snapshot(child, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="child",
            entity_id=child.id,
            changes={"changes": changes},
        )
    await session.commit()
    await _attach_guardian_counts(session, [child])
    return child

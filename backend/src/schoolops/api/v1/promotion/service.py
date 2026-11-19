"""Reviewed source-class to target-class promotion."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import NotFoundError, UnprocessableError
from schoolops.db.models import Child, ClassGroup, Enrollment, MinistryYear
from schoolops.domain.enums import ChildStatus

from .schemas import (
    PromotionAlreadyEnrolled,
    PromotionApplyRead,
    PromotionAssignment,
    PromotionCounts,
    PromotionPreviewRead,
    PromotionRequest,
    PromotionUnmatched,
)


@dataclass(frozen=True)
class _PromotionContext:
    source: MinistryYear
    target: MinistryYear
    source_classes: dict[UUID, ClassGroup]
    target_classes: dict[UUID, ClassGroup]
    mapping: dict[UUID, UUID]


def _age_on(birth_date: date, day: date) -> int:
    years = day.year - birth_date.year
    if (day.month, day.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


async def _load_context(session: AsyncSession, payload: PromotionRequest) -> _PromotionContext:
    if payload.source_year_id == payload.target_year_id:
        raise UnprocessableError("Source and target ministry years must differ.")

    source = await session.get(MinistryYear, payload.source_year_id)
    if source is None:
        raise NotFoundError(f"Ministry year {payload.source_year_id} was not found.")
    target = await session.get(MinistryYear, payload.target_year_id)
    if target is None:
        raise NotFoundError(f"Ministry year {payload.target_year_id} was not found.")

    source_ids = [mapping.source_class_id for mapping in payload.mappings]
    target_ids = [mapping.target_class_id for mapping in payload.mappings]
    if len(set(source_ids)) != len(source_ids):
        raise UnprocessableError("A source class may only be mapped once.")

    source_rows = (
        await session.scalars(select(ClassGroup).where(ClassGroup.id.in_(source_ids)))
    ).all()
    target_rows = (
        await session.scalars(select(ClassGroup).where(ClassGroup.id.in_(target_ids)))
    ).all()
    source_classes = {item.id: item for item in source_rows}
    target_classes = {item.id: item for item in target_rows}
    if len(source_classes) != len(set(source_ids)):
        raise NotFoundError("One or more source classes were not found.")
    if len(target_classes) != len(set(target_ids)):
        raise NotFoundError("One or more target classes were not found.")
    if any(item.ministry_year_id != source.id for item in source_classes.values()):
        raise UnprocessableError("Every source class must belong to the source year.")
    if any(item.ministry_year_id != target.id for item in target_classes.values()):
        raise UnprocessableError("Every target class must belong to the target year.")

    return _PromotionContext(
        source=source,
        target=target,
        source_classes=source_classes,
        target_classes=target_classes,
        mapping={mapping.source_class_id: mapping.target_class_id for mapping in payload.mappings},
    )


async def _source_children(
    session: AsyncSession, context: _PromotionContext
) -> list[tuple[Child, ClassGroup]]:
    """Active children enrolled in the source year at its end date."""
    rows = (
        await session.execute(
            select(Child, ClassGroup)
            .join(Enrollment, Enrollment.child_id == Child.id)
            .join(ClassGroup, ClassGroup.id == Enrollment.class_id)
            .where(
                ClassGroup.ministry_year_id == context.source.id,
                Child.status == ChildStatus.ACTIVE,
                Enrollment.start_date <= context.source.end_date,
                or_(
                    Enrollment.end_date.is_(None),
                    Enrollment.end_date >= context.source.end_date,
                ),
            )
            .order_by(Child.last_name, Child.first_name)
        )
    ).all()
    seen: set[UUID] = set()
    result: list[tuple[Child, ClassGroup]] = []
    for child, school_class in rows:
        if child.id not in seen:
            seen.add(child.id)
            result.append((child, school_class))
    return result


async def _target_enrollments(
    session: AsyncSession, context: _PromotionContext
) -> dict[UUID, ClassGroup]:
    rows = (
        await session.execute(
            select(Enrollment.child_id, ClassGroup)
            .join(ClassGroup, ClassGroup.id == Enrollment.class_id)
            .where(
                ClassGroup.ministry_year_id == context.target.id,
                or_(
                    Enrollment.end_date.is_(None),
                    Enrollment.end_date >= context.target.start_date,
                ),
            )
        )
    ).all()
    return {child_id: school_class for child_id, school_class in rows}


async def preview_promotion(
    session: AsyncSession, payload: PromotionRequest
) -> PromotionPreviewRead:
    context = await _load_context(session, payload)
    source_children = await _source_children(session, context)
    target_enrollments = await _target_enrollments(session, context)

    assignments: list[PromotionAssignment] = []
    unmatched: list[PromotionUnmatched] = []
    already_enrolled: list[PromotionAlreadyEnrolled] = []

    for child, source_class in source_children:
        target_class_id = context.mapping.get(source_class.id)
        if target_class_id is None:
            unmatched.append(
                PromotionUnmatched(
                    child_id=child.id,
                    child_name=f"{child.first_name} {child.last_name}",
                    source_class_id=source_class.id,
                    source_class_name=source_class.name,
                    reason="Source class is not mapped.",
                )
            )
            continue

        existing = target_enrollments.get(child.id)
        if existing is not None:
            already_enrolled.append(
                PromotionAlreadyEnrolled(
                    child_id=child.id,
                    child_name=f"{child.first_name} {child.last_name}",
                    target_class_id=existing.id,
                    target_class_name=existing.name,
                )
            )
            continue

        target_class = context.target_classes[target_class_id]
        assignments.append(
            PromotionAssignment(
                child_id=child.id,
                child_name=f"{child.first_name} {child.last_name}",
                source_class_id=source_class.id,
                source_class_name=source_class.name,
                target_class_id=target_class.id,
                target_class_name=target_class.name,
                age_at_target_start=_age_on(child.date_of_birth, context.target.start_date),
                target_age_band=target_class.age_band,
            )
        )

    return PromotionPreviewRead(
        assignments=assignments,
        unmatched=unmatched,
        already_enrolled=already_enrolled,
        counts=PromotionCounts(
            assign=len(assignments),
            unmatched=len(unmatched),
            already_enrolled=len(already_enrolled),
        ),
    )


async def apply_promotion(session: AsyncSession, payload: PromotionRequest) -> PromotionApplyRead:
    context = await _load_context(session, payload)
    preview = await preview_promotion(session, payload)

    enrollments = [
        Enrollment(
            child_id=assignment.child_id,
            class_id=assignment.target_class_id,
            start_date=context.target.start_date,
        )
        for assignment in preview.assignments
    ]
    session.add_all(enrollments)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="promotion",
        entity_id=context.target.id,
        changes={
            "after": {
                "source_year_id": str(context.source.id),
                "target_year_id": str(context.target.id),
                "children": [str(item.child_id) for item in preview.assignments],
                "mappings": [
                    {
                        "source_class_id": str(source_id),
                        "target_class_id": str(target_id),
                    }
                    for source_id, target_id in context.mapping.items()
                ],
            }
        },
    )
    await session.commit()
    return PromotionApplyRead(
        created=len(enrollments),
        skipped=preview.counts.already_enrolled,
        enrollment_ids=[enrollment.id for enrollment in enrollments],
    )

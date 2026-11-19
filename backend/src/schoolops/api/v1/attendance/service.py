"""Attendance rules: enrolled children, named visitors, and bulk upsert."""

from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from schoolops.api.v1.children.schemas import ChildSummary
from schoolops.api.v1.guardians.schemas import GuardianSummary
from schoolops.api.v1.sessions.schemas import SessionRead
from schoolops.api.v1.sessions.service import assert_meeting_day
from schoolops.core import audit
from schoolops.core.errors import NotFoundError, UnprocessableError
from schoolops.db.models import (
    AttendanceRecord,
    ChildGuardian,
    ClassGroup,
    ClassSession,
    Enrollment,
    Guardian,
)
from schoolops.domain.enums import AttendanceStatus

from .schemas import (
    AttendanceBulkUpdate,
    AttendanceEntryRead,
    AttendanceSummary,
    SessionAttendanceRead,
    VisitorAttendanceRead,
)


async def _roster(session: AsyncSession, class_session: ClassSession) -> list[Enrollment]:
    enrollments = (
        await session.scalars(
            select(Enrollment)
            .where(
                Enrollment.class_id == class_session.class_id,
                Enrollment.start_date <= class_session.date,
                or_(
                    Enrollment.end_date.is_(None),
                    Enrollment.end_date >= class_session.date,
                ),
            )
            .options(selectinload(Enrollment.child))
        )
    ).all()
    return sorted(
        enrollments,
        key=lambda item: (item.child.last_name.lower(), item.child.first_name.lower()),
    )


async def _guardians_by_child(
    session: AsyncSession, child_ids: list[UUID]
) -> dict[UUID, list[GuardianSummary]]:
    if not child_ids:
        return {}
    rows = (
        await session.execute(
            select(ChildGuardian, Guardian)
            .join(Guardian, Guardian.id == ChildGuardian.guardian_id)
            .where(ChildGuardian.child_id.in_(child_ids))
            .order_by(ChildGuardian.is_primary.desc(), Guardian.last_name)
        )
    ).all()
    result: dict[UUID, list[GuardianSummary]] = {}
    for link, guardian in rows:
        result.setdefault(link.child_id, []).append(
            GuardianSummary(
                id=guardian.id,
                first_name=guardian.first_name,
                last_name=guardian.last_name,
                phone=guardian.phone,
                email=guardian.email,
                relationship=link.relationship,
                is_primary=link.is_primary,
                is_emergency=link.is_emergency,
            )
        )
    return result


def _summary(
    entries: list[AttendanceEntryRead], visitors: list[VisitorAttendanceRead]
) -> AttendanceSummary:
    counts = {AttendanceStatus.PRESENT: 0, AttendanceStatus.ABSENT: 0}
    for entry in entries:
        if entry.status is not None:
            counts[entry.status] += 1
    recorded = sum(counts.values())
    visitors_present = sum(1 for visitor in visitors if visitor.status is AttendanceStatus.PRESENT)
    visitors_absent = len(visitors) - visitors_present
    return AttendanceSummary(
        present=counts[AttendanceStatus.PRESENT],
        absent=counts[AttendanceStatus.ABSENT],
        not_recorded=len(entries) - recorded,
        recorded=recorded,
        visitors_present=visitors_present,
        visitors_absent=visitors_absent,
        rate=(round(counts[AttendanceStatus.PRESENT] / recorded, 4) if recorded else None),
    )


async def get_attendance(
    session: AsyncSession, class_session: ClassSession
) -> SessionAttendanceRead:
    roster = await _roster(session, class_session)
    child_ids = [enrollment.child_id for enrollment in roster]
    guardians = await _guardians_by_child(session, child_ids)
    records = {
        record.child_id: record
        for record in (
            await session.scalars(
                select(AttendanceRecord).where(
                    AttendanceRecord.class_session_id == class_session.id,
                    AttendanceRecord.child_id.is_not(None),
                )
            )
        ).all()
        if record.child_id is not None
    }
    visitors = [
        VisitorAttendanceRead(
            id=record.id,
            visitor_name=record.visitor_name or "",
            status=record.status,
            note=record.note,
        )
        for record in (
            await session.scalars(
                select(AttendanceRecord)
                .where(
                    AttendanceRecord.class_session_id == class_session.id,
                    AttendanceRecord.visitor_name.is_not(None),
                )
                .order_by(AttendanceRecord.visitor_name)
            )
        ).all()
    ]

    entries = [
        AttendanceEntryRead(
            child=ChildSummary.model_validate(enrollment.child),
            guardians=guardians.get(enrollment.child_id, []),
            status=record.status if record is not None else None,
            note=record.note if record is not None else None,
            recorded=record is not None,
        )
        for enrollment in roster
        for record in [records.get(enrollment.child_id)]
    ]
    return SessionAttendanceRead(
        session=SessionRead.model_validate(class_session),
        entries=entries,
        visitors=visitors,
        summary=_summary(entries, visitors),
    )


async def put_attendance(
    session: AsyncSession,
    class_session: ClassSession,
    payload: AttendanceBulkUpdate,
    *,
    actor_id: UUID,
) -> SessionAttendanceRead:
    school_class = await session.get(ClassGroup, class_session.class_id)
    if school_class is None:
        raise NotFoundError("The class for this session was not found.")

    await assert_meeting_day(session, school_class, class_session.date)

    child_ids = [record.child_id for record in payload.records]
    if len(set(child_ids)) != len(child_ids):
        raise UnprocessableError("Each child may appear only once in the request.")

    allowed = {enrollment.child_id for enrollment in await _roster(session, class_session)}
    if any(child_id not in allowed for child_id in child_ids):
        raise UnprocessableError(
            "Attendance can only be recorded for children enrolled on the session date."
        )

    existing_children = {
        record.child_id: {
            "status": record.status.value,
            "note": record.note,
        }
        for record in (
            await session.scalars(
                select(AttendanceRecord).where(
                    AttendanceRecord.class_session_id == class_session.id,
                    AttendanceRecord.child_id.is_not(None),
                )
            )
        ).all()
        if record.child_id is not None
    }
    existing_visitors = (
        await session.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.class_session_id == class_session.id,
                AttendanceRecord.visitor_name.is_not(None),
            )
        )
    ).all()
    before_visitors = [
        {
            "name": visitor.visitor_name,
            "status": visitor.status.value,
            "note": visitor.note,
        }
        for visitor in existing_visitors
    ]

    if payload.records:
        statement = pg_insert(AttendanceRecord).values(
            [
                {
                    "class_session_id": class_session.id,
                    "child_id": record.child_id,
                    "visitor_name": None,
                    "status": record.status,
                    "note": record.note,
                    "recorded_by": actor_id,
                }
                for record in payload.records
            ]
        )
        statement = statement.on_conflict_do_update(
            index_elements=["class_session_id", "child_id"],
            index_where=text("child_id IS NOT NULL"),
            set_={
                "status": statement.excluded.status,
                "note": statement.excluded.note,
                "recorded_by": statement.excluded.recorded_by,
                "updated_at": func.now(),
            },
        )
        await session.execute(statement)

    for visitor in existing_visitors:
        await session.delete(visitor)

    session.add_all(
        [
            AttendanceRecord(
                class_session_id=class_session.id,
                visitor_name=visitor.name,
                status=visitor.status,
                note=visitor.note,
                recorded_by=actor_id,
            )
            for visitor in payload.visitors
        ]
    )

    after_children = {
        record.child_id: {
            "status": record.status.value,
            "note": record.note,
        }
        for record in payload.records
    }
    after_visitors = [
        {
            "name": visitor.name,
            "status": visitor.status.value,
            "note": visitor.note,
        }
        for visitor in payload.visitors
    ]
    child_changes = {
        str(child_id): {"from": existing_children.get(child_id), "to": after_value}
        for child_id, after_value in after_children.items()
        if existing_children.get(child_id) != after_value
    }
    if child_changes or before_visitors != after_visitors:
        await audit.record(
            session,
            action="update",
            entity_type="attendance",
            entity_id=class_session.id,
            changes={
                "children": child_changes,
                "visitors": {
                    "from": before_visitors,
                    "to": after_visitors,
                },
            },
            actor_id=actor_id,
        )
    await session.commit()

    return await get_attendance(session, class_session)

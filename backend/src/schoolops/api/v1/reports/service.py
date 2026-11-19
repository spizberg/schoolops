"""Attendance aggregation, not-seen reporting, dashboard, and CSV export."""

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.api.v1.children.schemas import ChildSummary
from schoolops.api.v1.ministry_years.schemas import MinistryYearRead
from schoolops.core.errors import UnprocessableError
from schoolops.db.models import (
    AttendanceRecord,
    Child,
    ClassGroup,
    ClassSession,
    Enrollment,
    MinistryYear,
    SessionVolunteer,
    Volunteer,
)
from schoolops.domain.enums import AttendanceStatus, ChildStatus, VolunteerStatus

from .schemas import (
    AttendanceReportRead,
    DashboardCounts,
    DashboardRead,
    DashboardSession,
    NotSeenEntry,
    NotSeenReportRead,
)

RECENT_DAYS = 30


async def _present_dates(session: AsyncSession, child_ids: list[UUID]) -> dict[UUID, date]:
    if not child_ids:
        return {}
    rows = (
        await session.execute(
            select(AttendanceRecord.child_id, func.max(ClassSession.date))
            .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
            .where(
                AttendanceRecord.child_id.in_(child_ids),
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
            .group_by(AttendanceRecord.child_id)
        )
    ).all()
    return {child_id: last_date for child_id, last_date in rows if child_id is not None}


async def _expected_slots(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    class_id: UUID | None,
    child_id: UUID | None,
) -> int:
    if class_id is not None:
        session_dates = (
            await session.scalars(
                select(ClassSession.date).where(
                    ClassSession.class_id == class_id,
                    ClassSession.date >= from_date,
                    ClassSession.date <= to_date,
                )
            )
        ).all()
        enrollment_stmt = select(
            Enrollment.child_id, Enrollment.start_date, Enrollment.end_date
        ).where(Enrollment.class_id == class_id)
        if child_id is not None:
            enrollment_stmt = enrollment_stmt.where(Enrollment.child_id == child_id)
        enrollments = (await session.execute(enrollment_stmt)).all()
        return sum(
            1
            for session_date in session_dates
            for enrollment in enrollments
            if enrollment.start_date <= session_date
            and (enrollment.end_date is None or enrollment.end_date >= session_date)
        )

    if child_id is None:
        return 0
    enrollments = (
        await session.execute(
            select(Enrollment.class_id, Enrollment.start_date, Enrollment.end_date).where(
                Enrollment.child_id == child_id
            )
        )
    ).all()
    class_ids = {enrollment.class_id for enrollment in enrollments}
    if not class_ids:
        return 0
    sessions = (
        await session.execute(
            select(ClassSession.class_id, ClassSession.date).where(
                ClassSession.class_id.in_(class_ids),
                ClassSession.date >= from_date,
                ClassSession.date <= to_date,
            )
        )
    ).all()
    return sum(
        1
        for class_session in sessions
        for enrollment in enrollments
        if enrollment.class_id == class_session.class_id
        and enrollment.start_date <= class_session.date
        and (enrollment.end_date is None or enrollment.end_date >= class_session.date)
    )


async def attendance_report(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    class_id: UUID | None,
    child_id: UUID | None,
) -> AttendanceReportRead:
    if from_date > to_date:
        raise UnprocessableError("The start of the range must not be after its end.")
    if class_id is None and child_id is None:
        raise UnprocessableError("Provide a class_id or a child_id (or both).")

    counts: dict[AttendanceStatus, int] = {
        AttendanceStatus.PRESENT: 0,
        AttendanceStatus.ABSENT: 0,
    }
    statement = (
        select(AttendanceRecord.status, func.count())
        .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
        .where(
            ClassSession.date >= from_date,
            ClassSession.date <= to_date,
            AttendanceRecord.child_id.is_not(None),
        )
        .group_by(AttendanceRecord.status)
    )
    if class_id is not None:
        statement = statement.where(ClassSession.class_id == class_id)
    if child_id is not None:
        statement = statement.where(AttendanceRecord.child_id == child_id)
    for status, count in (await session.execute(statement)).all():
        counts[status] = count

    visitor_counts = {status: 0 for status in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT)}
    if child_id is None:
        visitor_statement = (
            select(AttendanceRecord.status, func.count())
            .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
            .where(
                ClassSession.date >= from_date,
                ClassSession.date <= to_date,
                AttendanceRecord.visitor_name.is_not(None),
            )
            .group_by(AttendanceRecord.status)
        )
        if class_id is not None:
            visitor_statement = visitor_statement.where(ClassSession.class_id == class_id)
        for status, count in (await session.execute(visitor_statement)).all():
            visitor_counts[status] = count

    recorded = sum(counts.values())
    expected = await _expected_slots(
        session,
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
    )
    return AttendanceReportRead(
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
        present=counts[AttendanceStatus.PRESENT],
        absent=counts[AttendanceStatus.ABSENT],
        not_recorded=max(0, expected - recorded),
        recorded=recorded,
        visitors_present=visitor_counts[AttendanceStatus.PRESENT],
        visitors_absent=visitor_counts[AttendanceStatus.ABSENT],
        rate=(round(counts[AttendanceStatus.PRESENT] / recorded, 4) if recorded else None),
    )


async def not_seen_report(
    session: AsyncSession,
    *,
    since: date,
    class_id: UUID | None,
) -> NotSeenReportRead:
    today = date.today()
    if since > today:
        raise UnprocessableError("The 'since' date must not be in the future.")

    children_stmt = select(Child).where(Child.status == ChildStatus.ACTIVE)
    if class_id is not None:
        children_stmt = children_stmt.where(
            Child.id.in_(select(Enrollment.child_id).where(Enrollment.class_id == class_id))
        )
    children = (
        await session.scalars(children_stmt.order_by(Child.last_name, Child.first_name))
    ).all()
    child_ids = [child.id for child in children]
    if not child_ids:
        return NotSeenReportRead(since=since, class_id=class_id, items=[], total=0)

    sessions_stmt = select(ClassSession.id, ClassSession.class_id, ClassSession.date).where(
        ClassSession.date >= since,
        ClassSession.date <= today,
    )
    if class_id is not None:
        sessions_stmt = sessions_stmt.where(ClassSession.class_id == class_id)
    sessions = (await session.execute(sessions_stmt)).all()

    enrollment_stmt = select(
        Enrollment.child_id, Enrollment.class_id, Enrollment.start_date, Enrollment.end_date
    ).where(Enrollment.child_id.in_(child_ids))
    enrollments = (await session.execute(enrollment_stmt)).all()
    by_child: dict[UUID, list[tuple[UUID, date, date | None]]] = defaultdict(list)
    for enrollment in enrollments:
        by_child[enrollment.child_id].append(
            (enrollment.class_id, enrollment.start_date, enrollment.end_date)
        )

    present_stmt = (
        select(AttendanceRecord.child_id, AttendanceRecord.class_session_id)
        .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
        .where(
            AttendanceRecord.child_id.in_(child_ids),
            AttendanceRecord.status == AttendanceStatus.PRESENT,
            ClassSession.date >= since,
            ClassSession.date <= today,
        )
    )
    present_pairs = {
        (child_id, session_id)
        for child_id, session_id in (await session.execute(present_stmt)).all()
    }
    last_present = await _present_dates(session, child_ids)

    items: list[NotSeenEntry] = []
    for child in children:
        child_enrollments = by_child.get(child.id, [])
        enrolled_sessions = [
            row
            for row in sessions
            if any(
                class_id == row.class_id
                and start_date <= row.date
                and (end_date is None or end_date >= row.date)
                for class_id, start_date, end_date in child_enrollments
            )
        ]
        has_present = any((child.id, row.id) in present_pairs for row in enrolled_sessions)
        if has_present:
            continue
        items.append(
            NotSeenEntry(
                child=ChildSummary.model_validate(child),
                last_present_on=last_present.get(child.id),
                missed_sessions=len(enrolled_sessions),
            )
        )
    return NotSeenReportRead(since=since, class_id=class_id, items=items, total=len(items))


async def dashboard_summary(session: AsyncSession) -> DashboardRead:
    active_year = await session.scalar(select(MinistryYear).where(MinistryYear.is_active.is_(True)))
    children = (
        await session.scalar(
            select(func.count()).select_from(Child).where(Child.status == ChildStatus.ACTIVE)
        )
        or 0
    )
    volunteers = (
        await session.scalar(
            select(func.count())
            .select_from(Volunteer)
            .where(Volunteer.status == VolunteerStatus.ACTIVE)
        )
        or 0
    )

    classes_statement = select(func.count()).select_from(ClassGroup)
    if active_year is not None:
        classes_statement = classes_statement.where(ClassGroup.ministry_year_id == active_year.id)
    classes = await session.scalar(classes_statement) or 0

    today = date.today()
    sessions_statement = (
        select(ClassSession, ClassGroup.name)
        .join(ClassGroup, ClassGroup.id == ClassSession.class_id)
        .where(ClassSession.date == today)
    )
    if active_year is not None:
        sessions_statement = sessions_statement.where(ClassGroup.ministry_year_id == active_year.id)
    rows = (await session.execute(sessions_statement.order_by(ClassSession.start_time))).all()
    session_volunteer_counts = dict(
        (
            await session.execute(
                select(
                    SessionVolunteer.class_session_id,
                    func.count(),
                ).group_by(SessionVolunteer.class_session_id)
            )
        ).all()
    )
    todays_sessions = [
        DashboardSession(
            id=class_session.id,
            class_id=class_session.class_id,
            class_name=class_name,
            date=class_session.date,
            start_time=class_session.start_time.strftime("%H:%M:%S"),
            end_time=class_session.end_time.strftime("%H:%M:%S"),
            topic=class_session.topic,
            volunteers=session_volunteer_counts.get(class_session.id, 0),
        )
        for class_session, class_name in rows
    ]

    attendance_statement = (
        select(func.count())
        .select_from(AttendanceRecord)
        .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
        .join(ClassGroup, ClassGroup.id == ClassSession.class_id)
        .where(ClassSession.date == today)
    )
    if active_year is not None:
        attendance_statement = attendance_statement.where(
            ClassGroup.ministry_year_id == active_year.id
        )
    attendance_recorded = await session.scalar(attendance_statement) or 0

    not_seen = await not_seen_report(
        session, since=today - timedelta(days=RECENT_DAYS), class_id=None
    )

    return DashboardRead(
        active_year=(
            MinistryYearRead.model_validate(active_year) if active_year is not None else None
        ),
        today=today,
        counts=DashboardCounts(children=children, volunteers=volunteers, classes=classes),
        todays_sessions=todays_sessions,
        attendance_recorded_today=attendance_recorded,
        not_seen_recently=not_seen.total,
    )


@dataclass(frozen=True)
class _ChildLine:
    full_name: str
    last_present_on: date | None
    present: int
    absent: int
    not_recorded: int
    recorded: int
    rate: float | None


async def _child_lines(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    class_id: UUID | None,
    child_id: UUID | None,
) -> list[_ChildLine]:
    if from_date > to_date:
        raise UnprocessableError("The start of the range must not be after its end.")
    if class_id is None and child_id is None:
        raise UnprocessableError("Provide a class_id or a child_id (or both).")

    children_stmt = select(Child)
    if child_id is not None:
        children_stmt = children_stmt.where(Child.id == child_id)
    elif class_id is not None:
        children_stmt = children_stmt.where(
            Child.id.in_(select(Enrollment.child_id).where(Enrollment.class_id == class_id))
        )
    children = (
        await session.scalars(children_stmt.order_by(Child.last_name, Child.first_name))
    ).all()
    if not children:
        return []
    child_ids = [child.id for child in children]

    sessions_stmt = select(ClassSession.id, ClassSession.class_id, ClassSession.date).where(
        ClassSession.date >= from_date,
        ClassSession.date <= to_date,
    )
    if class_id is not None:
        sessions_stmt = sessions_stmt.where(ClassSession.class_id == class_id)
    elif child_id is not None:
        sessions_stmt = sessions_stmt.where(
            ClassSession.class_id.in_(
                select(Enrollment.class_id).where(Enrollment.child_id == child_id)
            )
        )
    sessions = (await session.execute(sessions_stmt)).all()

    enrollments_stmt = select(
        Enrollment.child_id, Enrollment.class_id, Enrollment.start_date, Enrollment.end_date
    ).where(Enrollment.child_id.in_(child_ids))
    if class_id is not None:
        enrollments_stmt = enrollments_stmt.where(Enrollment.class_id == class_id)
    enrollments = (await session.execute(enrollments_stmt)).all()

    counts_stmt = (
        select(AttendanceRecord.child_id, AttendanceRecord.status, func.count())
        .join(ClassSession, ClassSession.id == AttendanceRecord.class_session_id)
        .where(
            ClassSession.date >= from_date,
            ClassSession.date <= to_date,
            AttendanceRecord.child_id.in_(child_ids),
        )
        .group_by(AttendanceRecord.child_id, AttendanceRecord.status)
    )
    if class_id is not None:
        counts_stmt = counts_stmt.where(ClassSession.class_id == class_id)
    if child_id is not None:
        counts_stmt = counts_stmt.where(AttendanceRecord.child_id == child_id)
    counts: dict[UUID, dict[AttendanceStatus, int]] = defaultdict(dict)
    for record_child_id, status, count in (await session.execute(counts_stmt)).all():
        if record_child_id is not None:
            counts[record_child_id][status] = count

    last_present = await _present_dates(session, child_ids)
    lines: list[_ChildLine] = []
    for child in children:
        child_counts = counts.get(child.id, {})
        child_enrollments = [
            enrollment for enrollment in enrollments if enrollment.child_id == child.id
        ]
        expected = sum(
            1
            for class_session in sessions
            if any(
                enrollment.class_id == class_session.class_id
                and enrollment.start_date <= class_session.date
                and (enrollment.end_date is None or enrollment.end_date >= class_session.date)
                for enrollment in child_enrollments
            )
        )
        recorded = sum(child_counts.values())
        present = child_counts.get(AttendanceStatus.PRESENT, 0)
        lines.append(
            _ChildLine(
                full_name=f"{child.first_name} {child.last_name}",
                last_present_on=last_present.get(child.id),
                present=present,
                absent=child_counts.get(AttendanceStatus.ABSENT, 0),
                not_recorded=max(0, expected - recorded),
                recorded=recorded,
                rate=round(present / recorded, 4) if recorded else None,
            )
        )
    return lines


async def attendance_csv(
    session: AsyncSession,
    *,
    from_date: date,
    to_date: date,
    class_id: UUID | None,
    child_id: UUID | None,
) -> str:
    lines = await _child_lines(
        session,
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "child",
            "last_present_on",
            "present",
            "absent",
            "not_recorded",
            "recorded",
            "rate",
        ]
    )
    for line in lines:
        writer.writerow(
            [
                line.full_name,
                "" if line.last_present_on is None else line.last_present_on.isoformat(),
                line.present,
                line.absent,
                line.not_recorded,
                line.recorded,
                "" if line.rate is None else f"{line.rate:.4f}",
            ]
        )
    return output.getvalue()

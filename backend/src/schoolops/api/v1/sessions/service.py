"""Class-session rules, session volunteers, and bulk generation."""

from datetime import date, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.api.v1.volunteers.schemas import VolunteerSummary
from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import (
    ClassGroup,
    ClassSession,
    MinistryYear,
    NoClassDay,
    SessionVolunteer,
    Volunteer,
)
from schoolops.domain.calendar import list_meeting_days
from schoolops.domain.enums import VolunteerStatus

from .schemas import (
    SessionCreate,
    SessionGenerateRequest,
    SessionGenerateResult,
    SessionRead,
    SessionUpdate,
    SessionVolunteerRead,
    SessionVolunteersRead,
)

_FIELDS = (
    "date",
    "start_time",
    "end_time",
    "topic",
    "notes",
    "content_markdown",
    "resources",
)


async def get_session(session: AsyncSession, session_id: UUID) -> ClassSession:
    class_session = await session.get(ClassSession, session_id)
    if class_session is None:
        raise NotFoundError(f"Class session {session_id} was not found.")
    return class_session


async def _year_for_class(session: AsyncSession, school_class: ClassGroup) -> MinistryYear:
    year = await session.get(MinistryYear, school_class.ministry_year_id)
    if year is None:
        raise NotFoundError(f"Ministry year {school_class.ministry_year_id} was not found.")
    return year


async def assert_meeting_day(session: AsyncSession, school_class: ClassGroup, day: date) -> None:
    year = await _year_for_class(session, school_class)
    if not (year.start_date <= day <= year.end_date):
        raise UnprocessableError("A session must fall inside the class's ministry year.")
    closure = await session.scalar(
        select(NoClassDay.id).where(
            NoClassDay.ministry_year_id == year.id,
            NoClassDay.date == day,
        )
    )
    if closure is not None or day.isoweekday() not in year.meeting_weekdays:
        raise UnprocessableError(f"{day.isoformat()} is not a meeting day.")


def _assert_times(start_time: time, end_time: time) -> None:
    if start_time >= end_time:
        raise UnprocessableError("The start time must be before the end time.")


async def _assert_unique(
    session: AsyncSession,
    *,
    class_id: UUID,
    day: date,
    start_time: time,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(ClassSession.id).where(
        ClassSession.class_id == class_id,
        ClassSession.date == day,
        ClassSession.start_time == start_time,
    )
    if exclude_id is not None:
        stmt = stmt.where(ClassSession.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError("This class already has a session at that date and start time.")


async def list_sessions(
    session: AsyncSession,
    school_class: ClassGroup,
    *,
    from_date: date | None,
    to_date: date | None,
    limit: int,
    offset: int,
) -> tuple[list[ClassSession], int]:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise UnprocessableError("The start of the range must not be after its end.")

    stmt = select(ClassSession).where(ClassSession.class_id == school_class.id)
    if from_date is not None:
        stmt = stmt.where(ClassSession.date >= from_date)
    if to_date is not None:
        stmt = stmt.where(ClassSession.date <= to_date)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    sessions = (
        await session.scalars(
            stmt.order_by(ClassSession.date, ClassSession.start_time).limit(limit).offset(offset)
        )
    ).all()
    return list(sessions), total


async def create_session(
    session: AsyncSession, school_class: ClassGroup, payload: SessionCreate
) -> ClassSession:
    _assert_times(payload.start_time, payload.end_time)
    await assert_meeting_day(session, school_class, payload.date)
    await _assert_unique(
        session,
        class_id=school_class.id,
        day=payload.date,
        start_time=payload.start_time,
    )

    class_session = ClassSession(
        class_id=school_class.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        topic=payload.topic,
        notes=payload.notes,
        content_markdown=payload.content_markdown,
        resources=[resource.model_dump() for resource in payload.resources],
    )
    session.add(class_session)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="class_session",
        entity_id=class_session.id,
        changes={"after": audit.snapshot(class_session, _FIELDS)},
    )
    await session.commit()
    return class_session


async def update_session(
    session: AsyncSession, class_session: ClassSession, payload: SessionUpdate
) -> ClassSession:
    data = payload.model_dump(exclude_unset=True)
    for field in ("date", "start_time", "end_time", "resources"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    day = data.get("date", class_session.date)
    start_time = data.get("start_time", class_session.start_time)
    end_time = data.get("end_time", class_session.end_time)
    _assert_times(start_time, end_time)

    school_class = await session.get(ClassGroup, class_session.class_id)
    if school_class is None:
        raise NotFoundError("The class for this session was not found.")
    await assert_meeting_day(session, school_class, day)
    await _assert_unique(
        session,
        class_id=class_session.class_id,
        day=day,
        start_time=start_time,
        exclude_id=class_session.id,
    )

    before = audit.snapshot(class_session, _FIELDS)
    for field, value in data.items():
        setattr(class_session, field, value)
    changes = audit.diff(before, audit.snapshot(class_session, _FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="class_session",
            entity_id=class_session.id,
            changes={"changes": changes},
        )
    await session.commit()
    return class_session


async def delete_session(session: AsyncSession, class_session: ClassSession) -> None:
    before = audit.snapshot(class_session, _FIELDS)
    await session.delete(class_session)
    await audit.record(
        session,
        action="delete",
        entity_type="class_session",
        entity_id=class_session.id,
        changes={"before": before},
    )
    await session.commit()


async def generate_sessions(
    session: AsyncSession,
    school_class: ClassGroup,
    payload: SessionGenerateRequest,
) -> SessionGenerateResult:
    _assert_times(payload.start_time, payload.end_time)
    if payload.start_date > payload.end_date:
        raise UnprocessableError("The start of the range must not be after its end.")

    year = await _year_for_class(session, school_class)
    if payload.start_date < year.start_date or payload.end_date > year.end_date:
        raise UnprocessableError("The range must fall inside the class's ministry year.")

    weekdays = payload.weekdays or year.meeting_weekdays
    closures = set(
        (
            await session.scalars(
                select(NoClassDay.date).where(
                    NoClassDay.ministry_year_id == year.id,
                    NoClassDay.date >= payload.start_date,
                    NoClassDay.date <= payload.end_date,
                )
            )
        ).all()
    )
    meeting_days = list_meeting_days(
        payload.start_date,
        payload.end_date,
        year.meeting_weekdays,
        closures,
    )
    requested_days = [day for day in meeting_days if day.isoweekday() in weekdays]
    existing = set(
        (
            await session.scalars(
                select(ClassSession.date).where(
                    ClassSession.class_id == school_class.id,
                    ClassSession.start_time == payload.start_time,
                    ClassSession.date >= payload.start_date,
                    ClassSession.date <= payload.end_date,
                )
            )
        ).all()
    )
    missing = [day for day in requested_days if day not in existing]

    sessions = [
        ClassSession(
            class_id=school_class.id,
            date=day,
            start_time=payload.start_time,
            end_time=payload.end_time,
            resources=[],
        )
        for day in missing
    ]
    session.add_all(sessions)
    await session.flush()
    await audit.record(
        session,
        action="generate",
        entity_type="class",
        entity_id=school_class.id,
        changes={
            "after": {
                "dates": [item.date.isoformat() for item in sessions],
                "start_time": payload.start_time.isoformat(),
                "end_time": payload.end_time.isoformat(),
            }
        },
    )
    await session.commit()
    return SessionGenerateResult(
        created=len(sessions),
        skipped=len(requested_days) - len(sessions),
        session_ids=[item.id for item in sessions],
    )


async def list_session_volunteers(
    session: AsyncSession, class_session: ClassSession
) -> SessionVolunteersRead:
    rows = (
        await session.execute(
            select(SessionVolunteer, Volunteer)
            .join(Volunteer, Volunteer.id == SessionVolunteer.volunteer_id)
            .where(SessionVolunteer.class_session_id == class_session.id)
            .order_by(Volunteer.last_name, Volunteer.first_name)
        )
    ).all()
    return SessionVolunteersRead(
        class_session_id=class_session.id,
        volunteers=[
            SessionVolunteerRead(
                id=link.id,
                class_session_id=link.class_session_id,
                volunteer_id=link.volunteer_id,
                volunteer=VolunteerSummary.model_validate(volunteer),
            )
            for link, volunteer in rows
        ],
    )


async def replace_session_volunteers(
    session: AsyncSession,
    class_session: ClassSession,
    volunteer_ids: list[UUID],
) -> SessionVolunteersRead:
    volunteers = (
        await session.scalars(select(Volunteer).where(Volunteer.id.in_(volunteer_ids)))
    ).all()
    if len(volunteers) != len(set(volunteer_ids)):
        raise NotFoundError("One or more volunteers were not found.")
    if any(volunteer.status is not VolunteerStatus.ACTIVE for volunteer in volunteers):
        raise UnprocessableError("Only active volunteers can serve a session.")

    existing = (
        await session.scalars(
            select(SessionVolunteer).where(SessionVolunteer.class_session_id == class_session.id)
        )
    ).all()
    before_ids = [str(link.volunteer_id) for link in existing]
    for link in existing:
        await session.delete(link)
    await session.flush()
    await audit.record(
        session,
        action="update",
        entity_type="class_session",
        entity_id=class_session.id,
        changes={
            "volunteers": {
                "from": sorted(before_ids),
                "to": sorted(str(volunteer_id) for volunteer_id in volunteer_ids),
            }
        },
    )
    session.add_all(
        [
            SessionVolunteer(
                class_session_id=class_session.id,
                volunteer_id=volunteer_id,
            )
            for volunteer_id in volunteer_ids
        ]
    )
    await session.commit()
    return await list_session_volunteers(session, class_session)


__all__ = [
    "SessionRead",
    "assert_meeting_day",
    "create_session",
    "delete_session",
    "generate_sessions",
    "get_session",
    "list_session_volunteers",
    "list_sessions",
    "replace_session_volunteers",
    "update_session",
]

"""Ministry year and calendar rules."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.core import audit
from schoolops.core.errors import ConflictError, NotFoundError, UnprocessableError
from schoolops.db.models import MinistryYear, NoClassDay
from schoolops.domain.calendar import list_meeting_days as compute_meeting_days

from .schemas import MinistryYearCreate, MinistryYearUpdate, NoClassDayCreate

_YEAR_FIELDS = ("label", "start_date", "end_date", "meeting_weekdays", "is_active")
_DAY_FIELDS = ("ministry_year_id", "date", "name", "kind")


async def get_year(session: AsyncSession, year_id: UUID) -> MinistryYear:
    year = await session.get(MinistryYear, year_id)
    if year is None:
        raise NotFoundError(f"Ministry year {year_id} was not found.")
    return year


async def list_years(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[MinistryYear], int]:
    total = await session.scalar(select(func.count()).select_from(MinistryYear)) or 0
    years = (
        await session.scalars(
            select(MinistryYear)
            .order_by(MinistryYear.start_date.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(years), total


def _assert_dates(start: date, end: date) -> None:
    if start >= end:
        raise UnprocessableError("The start date must be strictly before the end date.")


async def _assert_label_available(
    session: AsyncSession, label: str, *, exclude_id: UUID | None = None
) -> None:
    stmt = select(MinistryYear.id).where(MinistryYear.label == label)
    if exclude_id is not None:
        stmt = stmt.where(MinistryYear.id != exclude_id)
    if await session.scalar(stmt) is not None:
        raise ConflictError(f"A ministry year labelled '{label}' already exists.")


async def _deactivate_others(session: AsyncSession, *, keep_id: UUID | None = None) -> None:
    stmt = update(MinistryYear).where(MinistryYear.is_active.is_(True))
    if keep_id is not None:
        stmt = stmt.where(MinistryYear.id != keep_id)
    await session.execute(stmt.values(is_active=False))


async def create_year(session: AsyncSession, payload: MinistryYearCreate) -> MinistryYear:
    _assert_dates(payload.start_date, payload.end_date)
    await _assert_label_available(session, payload.label)

    if payload.is_active:
        await _deactivate_others(session)

    year = MinistryYear(
        label=payload.label,
        start_date=payload.start_date,
        end_date=payload.end_date,
        meeting_weekdays=payload.meeting_weekdays,
        is_active=payload.is_active,
    )
    session.add(year)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="ministry_year",
        entity_id=year.id,
        changes={"after": audit.snapshot(year, _YEAR_FIELDS)},
    )
    await session.commit()
    return year


async def update_year(
    session: AsyncSession, year: MinistryYear, payload: MinistryYearUpdate
) -> MinistryYear:
    data = payload.model_dump(exclude_unset=True)
    for field in ("label", "start_date", "end_date", "meeting_weekdays", "is_active"):
        if field in data and data[field] is None:
            raise UnprocessableError(f"'{field}' cannot be null.")

    start = data.get("start_date", year.start_date)
    end = data.get("end_date", year.end_date)
    _assert_dates(start, end)

    if "label" in data:
        await _assert_label_available(session, data["label"], exclude_id=year.id)
    if data.get("is_active") is True:
        await _deactivate_others(session, keep_id=year.id)

    before = audit.snapshot(year, _YEAR_FIELDS)
    for field, value in data.items():
        setattr(year, field, value)
    changes = audit.diff(before, audit.snapshot(year, _YEAR_FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="ministry_year",
            entity_id=year.id,
            changes={"changes": changes},
        )
    await session.commit()
    return year


async def activate_year(session: AsyncSession, year: MinistryYear) -> MinistryYear:
    await _deactivate_others(session, keep_id=year.id)
    before = audit.snapshot(year, _YEAR_FIELDS)
    year.is_active = True
    changes = audit.diff(before, audit.snapshot(year, _YEAR_FIELDS))
    if changes:
        await audit.record(
            session,
            action="update",
            entity_type="ministry_year",
            entity_id=year.id,
            changes={"changes": changes},
        )
    await session.commit()
    return year


async def create_no_class_day(
    session: AsyncSession, year: MinistryYear, payload: NoClassDayCreate
) -> NoClassDay:
    if not (year.start_date <= payload.date <= year.end_date):
        raise UnprocessableError("A no-class day must fall inside its ministry year.")

    duplicate = await session.scalar(
        select(NoClassDay.id).where(
            NoClassDay.ministry_year_id == year.id,
            NoClassDay.date == payload.date,
        )
    )
    if duplicate is not None:
        raise ConflictError(f"{payload.date.isoformat()} is already a no-class day.")

    day = NoClassDay(
        ministry_year_id=year.id,
        date=payload.date,
        name=payload.name,
        kind=payload.kind,
    )
    session.add(day)
    await session.flush()
    await audit.record(
        session,
        action="create",
        entity_type="no_class_day",
        entity_id=day.id,
        changes={"after": audit.snapshot(day, _DAY_FIELDS)},
    )
    await session.commit()
    return day


async def list_no_class_days(session: AsyncSession, year: MinistryYear) -> list[NoClassDay]:
    days = (
        await session.scalars(
            select(NoClassDay)
            .where(NoClassDay.ministry_year_id == year.id)
            .order_by(NoClassDay.date)
        )
    ).all()
    return list(days)


async def delete_no_class_day(session: AsyncSession, day_id: UUID) -> None:
    day = await session.get(NoClassDay, day_id)
    if day is None:
        raise NotFoundError(f"No-class day {day_id} was not found.")
    before = audit.snapshot(day, _DAY_FIELDS)
    await session.delete(day)
    await audit.record(
        session,
        action="delete",
        entity_type="no_class_day",
        entity_id=day.id,
        changes={"before": before},
    )
    await session.commit()


async def meeting_days_in_range(
    session: AsyncSession, year: MinistryYear, start: date, end: date
) -> list[date]:
    if start > end:
        raise UnprocessableError("The start of the range must not be after its end.")

    closures = set(
        (
            await session.scalars(
                select(NoClassDay.date).where(
                    NoClassDay.ministry_year_id == year.id,
                    NoClassDay.date >= start,
                    NoClassDay.date <= end,
                )
            )
        ).all()
    )
    bounded_start = max(start, year.start_date)
    bounded_end = min(end, year.end_date)
    return compute_meeting_days(bounded_start, bounded_end, year.meeting_weekdays, closures)

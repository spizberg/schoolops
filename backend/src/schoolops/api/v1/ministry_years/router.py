"""HTTP routes for ministry years, no-class days, and meeting-day queries."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.core.pagination import Page

from . import service
from .schemas import (
    MeetingDaysRead,
    MinistryYearCreate,
    MinistryYearRead,
    MinistryYearUpdate,
    NoClassDayCreate,
    NoClassDayRead,
)

router = APIRouter(prefix="/ministry-years", tags=["ministry years"])
calendar_router = APIRouter(tags=["calendar"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[MinistryYearRead], summary="List ministry years")
async def list_ministry_years(
    session: SessionDep, limit: Limit = 50, offset: Offset = 0
) -> Page[MinistryYearRead]:
    years, total = await service.list_years(session, limit=limit, offset=offset)
    return Page(
        items=[MinistryYearRead.model_validate(year) for year in years],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=MinistryYearRead, status_code=201, summary="Create a year")
async def create_ministry_year(
    payload: MinistryYearCreate, session: SessionDep, response: Response
) -> MinistryYearRead:
    year = await service.create_year(session, payload)
    response.headers["Location"] = f"/v1/ministry-years/{year.id}"
    return MinistryYearRead.model_validate(year)


@router.get("/{year_id}", response_model=MinistryYearRead, summary="Get a year")
async def get_ministry_year(year_id: UUID, session: SessionDep) -> MinistryYearRead:
    year = await service.get_year(session, year_id)
    return MinistryYearRead.model_validate(year)


@router.patch("/{year_id}", response_model=MinistryYearRead, summary="Update a year")
async def update_ministry_year(
    year_id: UUID, payload: MinistryYearUpdate, session: SessionDep
) -> MinistryYearRead:
    year = await service.get_year(session, year_id)
    updated = await service.update_year(session, year, payload)
    return MinistryYearRead.model_validate(updated)


@router.post("/{year_id}/activate", response_model=MinistryYearRead, summary="Activate a year")
async def activate_ministry_year(year_id: UUID, session: SessionDep) -> MinistryYearRead:
    year = await service.get_year(session, year_id)
    activated = await service.activate_year(session, year)
    return MinistryYearRead.model_validate(activated)


@router.get(
    "/{year_id}/no-class-days",
    response_model=list[NoClassDayRead],
    summary="List no-class days",
)
async def list_no_class_days(year_id: UUID, session: SessionDep) -> list[NoClassDayRead]:
    year = await service.get_year(session, year_id)
    days = await service.list_no_class_days(session, year)
    return [NoClassDayRead.model_validate(day) for day in days]


@router.post(
    "/{year_id}/no-class-days",
    response_model=NoClassDayRead,
    status_code=201,
    summary="Add a no-class day",
)
async def create_no_class_day(
    year_id: UUID, payload: NoClassDayCreate, session: SessionDep, response: Response
) -> NoClassDayRead:
    year = await service.get_year(session, year_id)
    day = await service.create_no_class_day(session, year, payload)
    response.headers["Location"] = f"/v1/no-class-days/{day.id}"
    return NoClassDayRead.model_validate(day)


@router.get(
    "/{year_id}/meeting-days",
    response_model=MeetingDaysRead,
    summary="List meeting days in a date range",
)
async def list_meeting_days(
    year_id: UUID,
    session: SessionDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> MeetingDaysRead:
    year = await service.get_year(session, year_id)
    days = await service.meeting_days_in_range(session, year, from_date, to_date)
    return MeetingDaysRead(items=days)


@calendar_router.delete("/no-class-days/{day_id}", status_code=204, summary="Remove a no-class day")
async def delete_no_class_day(day_id: UUID, session: SessionDep) -> Response:
    await service.delete_no_class_day(session, day_id)
    return Response(status_code=204)

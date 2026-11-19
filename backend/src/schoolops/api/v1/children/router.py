"""HTTP routes for children."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.api.v1.reports import service as report_service
from schoolops.api.v1.reports.schemas import AttendanceReportRead
from schoolops.core.pagination import Page
from schoolops.domain.enums import ChildStatus

from . import service
from .schemas import ChildCreate, ChildRead, ChildUpdate

router = APIRouter(prefix="/children", tags=["children"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[ChildRead], summary="List and search children")
async def list_children(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: ChildStatus | None = None,
    household_id: UUID | None = None,
    class_id: UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[ChildRead]:
    children, total = await service.list_children(
        session,
        q=q,
        status=status,
        household_id=household_id,
        class_id=class_id,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[ChildRead.model_validate(child) for child in children],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ChildRead, status_code=201, summary="Create a child")
async def create_child(payload: ChildCreate, session: SessionDep, response: Response) -> ChildRead:
    child = await service.create_child(session, payload)
    response.headers["Location"] = f"/v1/children/{child.id}"
    _warn_if_no_guardian(response, child)
    return ChildRead.model_validate(child)


@router.get("/{child_id}", response_model=ChildRead, summary="Get a child")
async def get_child(child_id: UUID, session: SessionDep) -> ChildRead:
    child = await service.get_child(session, child_id)
    return ChildRead.model_validate(child)


@router.patch("/{child_id}", response_model=ChildRead, summary="Update a child")
async def update_child(
    child_id: UUID, payload: ChildUpdate, session: SessionDep, response: Response
) -> ChildRead:
    child = await service.get_child(session, child_id)
    updated = await service.update_child(session, child, payload)
    _warn_if_no_guardian(response, updated)
    return ChildRead.model_validate(updated)


@router.get(
    "/{child_id}/attendance",
    response_model=AttendanceReportRead,
    summary="Attendance summary for one child",
)
async def child_attendance(
    child_id: UUID,
    session: SessionDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    class_id: UUID | None = None,
) -> AttendanceReportRead:
    await service.get_child(session, child_id)
    return await report_service.attendance_report(
        session,
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
    )


def _warn_if_no_guardian(response: Response, child: object) -> None:
    status = getattr(child, "status", None)
    count = getattr(child, "guardian_count", 0)
    if status is ChildStatus.ACTIVE and count == 0:
        response.headers["X-CBSG-Warning"] = "This active child has no guardian contact."

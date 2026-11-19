"""HTTP routes for dashboard, attendance reports, not-seen report, and CSV."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep

from . import service
from .schemas import AttendanceReportRead, DashboardRead, NotSeenReportRead

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/dashboard",
    response_model=DashboardRead,
    summary="Active-year counts, today's sessions, and children not seen recently",
)
async def dashboard(session: SessionDep) -> DashboardRead:
    return await service.dashboard_summary(session)


@router.get(
    "/attendance",
    response_model=AttendanceReportRead,
    summary="Attendance counts and rate for a class and/or child",
)
async def attendance_report(
    session: SessionDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    class_id: UUID | None = None,
    child_id: UUID | None = None,
) -> AttendanceReportRead:
    return await service.attendance_report(
        session,
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
    )


@router.get(
    "/not-seen",
    response_model=NotSeenReportRead,
    summary="Active children with no present attendance since a date",
)
async def not_seen_report(
    session: SessionDep,
    since: Annotated[date, Query()],
    class_id: UUID | None = None,
) -> NotSeenReportRead:
    return await service.not_seen_report(session, since=since, class_id=class_id)


@router.get(
    "/attendance.csv",
    summary="Export per-child attendance totals as CSV",
    responses={200: {"content": {"text/csv": {}}, "description": "CSV export"}},
)
async def export_attendance_csv(
    session: SessionDep,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    class_id: UUID | None = None,
    child_id: UUID | None = None,
) -> Response:
    content = await service.attendance_csv(
        session,
        from_date=from_date,
        to_date=to_date,
        class_id=class_id,
        child_id=child_id,
    )
    filename = f"attendance_{from_date.isoformat()}_{to_date.isoformat()}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

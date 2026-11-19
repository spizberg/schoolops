"""Report and dashboard contracts."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from schoolops.api.v1.children.schemas import ChildSummary
from schoolops.api.v1.ministry_years.schemas import MinistryYearRead


class AttendanceReportRead(BaseModel):
    """Attendance counts for a class and/or child over an inclusive date range."""

    from_date: date
    to_date: date
    class_id: UUID | None
    child_id: UUID | None
    present: int
    absent: int
    not_recorded: int
    recorded: int
    visitors_present: int
    visitors_absent: int
    rate: float | None


class NotSeenEntry(BaseModel):
    child: ChildSummary
    last_present_on: date | None
    missed_sessions: int


class NotSeenReportRead(BaseModel):
    since: date
    class_id: UUID | None
    items: list[NotSeenEntry]
    total: int


class DashboardCounts(BaseModel):
    children: int
    volunteers: int
    classes: int


class DashboardSession(BaseModel):
    id: UUID
    class_id: UUID
    class_name: str
    date: date
    start_time: str
    end_time: str
    topic: str | None
    volunteers: int


class DashboardRead(BaseModel):
    active_year: MinistryYearRead | None
    today: date
    counts: DashboardCounts
    todays_sessions: list[DashboardSession]
    attendance_recorded_today: int
    not_seen_recently: int

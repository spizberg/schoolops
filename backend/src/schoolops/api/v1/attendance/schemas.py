"""Request and response contracts for session attendance."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from schoolops.api.v1.children.schemas import ChildSummary
from schoolops.api.v1.guardians.schemas import GuardianSummary
from schoolops.api.v1.sessions.schemas import SessionRead
from schoolops.domain.enums import AttendanceStatus


class AttendanceRecordInput(BaseModel):
    child_id: UUID
    status: AttendanceStatus
    note: str | None = None

    @field_validator("note")
    @classmethod
    def _strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class VisitorInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    status: AttendanceStatus = AttendanceStatus.PRESENT
    note: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class AttendanceBulkUpdate(BaseModel):
    records: list[AttendanceRecordInput] = Field(default_factory=list)
    visitors: list[VisitorInput] = Field(default_factory=list)


class AttendanceEntryRead(BaseModel):
    child: ChildSummary
    guardians: list[GuardianSummary]
    status: AttendanceStatus | None
    note: str | None
    recorded: bool


class VisitorAttendanceRead(BaseModel):
    id: UUID
    visitor_name: str
    status: AttendanceStatus
    note: str | None


class AttendanceSummary(BaseModel):
    present: int
    absent: int
    not_recorded: int
    recorded: int
    visitors_present: int
    visitors_absent: int
    rate: float | None


class SessionAttendanceRead(BaseModel):
    session: SessionRead
    entries: list[AttendanceEntryRead]
    visitors: list[VisitorAttendanceRead]
    summary: AttendanceSummary

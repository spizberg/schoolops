"""Request and response contracts for enrollments and class rosters."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from schoolops.api.v1.children.schemas import ChildSummary


class EnrollmentCreate(BaseModel):
    child_id: UUID
    start_date: date
    end_date: date | None = None


class EnrollmentUpdate(BaseModel):
    """Only the end date can be corrected; use ``null`` to reopen an enrollment."""

    end_date: date | None = None


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_id: UUID
    child_id: UUID
    start_date: date
    end_date: date | None
    created_at: datetime
    updated_at: datetime


class RosterEntryRead(EnrollmentRead):
    child: ChildSummary

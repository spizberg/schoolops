"""Request and response contracts for children."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schoolops.domain.enums import ChildStatus, PhotoConsent


class ChildCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    household_id: UUID | None = None
    grade: str | None = Field(default=None, max_length=50)
    allergies: str | None = None
    medical_notes: str | None = None
    photo_consent: PhotoConsent = PhotoConsent.NOT_RECORDED
    status: ChildStatus = ChildStatus.ACTIVE
    joined_on: date | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class ChildUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    household_id: UUID | None = None
    grade: str | None = Field(default=None, max_length=50)
    allergies: str | None = None
    medical_notes: str | None = None
    photo_consent: PhotoConsent | None = None
    status: ChildStatus | None = None
    joined_on: date | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ChildSummary(BaseModel):
    """Compact child data used on rosters and reports."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    allergies: str | None
    medical_notes: str | None
    photo_consent: PhotoConsent
    status: ChildStatus


class ChildRead(ChildSummary):
    household_id: UUID | None
    grade: str | None
    joined_on: date | None
    notes: str | None
    guardian_count: int = 0
    created_at: datetime
    updated_at: datetime

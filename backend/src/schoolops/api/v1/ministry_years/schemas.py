"""Request and response contracts for ministry years and the calendar."""

from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schoolops.domain.enums import NoClassDayKind


def _validate_weekdays(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("At least one meeting weekday is required.")
    if any(day < 1 or day > 7 for day in value):
        raise ValueError("Meeting weekdays are ISO weekday numbers from 1 (Monday) to 7 (Sunday).")
    return sorted(set(value))


class MinistryYearCreate(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    start_date: Date
    end_date: Date
    meeting_weekdays: list[int] = Field(default_factory=lambda: [7])
    is_active: bool = False

    @field_validator("label")
    @classmethod
    def _strip_label(cls, value: str) -> str:
        return value.strip()

    @field_validator("meeting_weekdays")
    @classmethod
    def _check_weekdays(cls, value: list[int]) -> list[int]:
        return _validate_weekdays(value)


class MinistryYearUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    start_date: Date | None = None
    end_date: Date | None = None
    meeting_weekdays: list[int] | None = None
    is_active: bool | None = None

    @field_validator("label")
    @classmethod
    def _strip_label(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("meeting_weekdays")
    @classmethod
    def _check_weekdays(cls, value: list[int] | None) -> list[int] | None:
        return _validate_weekdays(value) if value is not None else None


class MinistryYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    start_date: Date
    end_date: Date
    meeting_weekdays: list[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NoClassDayCreate(BaseModel):
    date: Date
    name: str = Field(min_length=1, max_length=120)
    kind: NoClassDayKind = NoClassDayKind.CLOSURE

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class NoClassDayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ministry_year_id: UUID
    date: Date
    name: str
    kind: NoClassDayKind
    created_at: datetime
    updated_at: datetime


class MeetingDaysRead(BaseModel):
    items: list[Date]

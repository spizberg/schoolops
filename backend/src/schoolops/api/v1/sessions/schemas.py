"""Request and response contracts for class sessions and lesson content."""

from datetime import date as Date
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schoolops.api.v1.volunteers.schemas import VolunteerSummary


class ResourceLink(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2000)

    @field_validator("label", "url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class SessionCreate(BaseModel):
    date: Date
    start_time: time
    end_time: time
    topic: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    content_markdown: str | None = None
    resources: list[ResourceLink] = Field(default_factory=list)

    @field_validator("topic")
    @classmethod
    def _strip_topic(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class SessionUpdate(BaseModel):
    date: Date | None = None
    start_time: time | None = None
    end_time: time | None = None
    topic: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    content_markdown: str | None = None
    resources: list[ResourceLink] | None = None

    @field_validator("topic")
    @classmethod
    def _strip_topic(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_id: UUID
    date: Date
    start_time: time
    end_time: time
    topic: str | None
    notes: str | None
    content_markdown: str | None
    resources: list[ResourceLink]
    created_at: datetime
    updated_at: datetime


class SessionGenerateRequest(BaseModel):
    start_date: Date
    end_date: Date
    start_time: time
    end_time: time
    weekdays: list[int] = Field(default_factory=list)

    @field_validator("weekdays")
    @classmethod
    def _check_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("Weekdays are ISO weekday numbers from 1 (Monday) to 7 (Sunday).")
        return sorted(set(value))


class SessionGenerateResult(BaseModel):
    created: int
    skipped: int
    session_ids: list[UUID]


class SessionVolunteersUpdate(BaseModel):
    volunteer_ids: list[UUID] = Field(default_factory=list)

    @field_validator("volunteer_ids")
    @classmethod
    def _dedupe(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("A volunteer may appear only once.")
        return value


class SessionVolunteerRead(BaseModel):
    id: UUID
    class_session_id: UUID
    volunteer_id: UUID
    volunteer: VolunteerSummary


class SessionVolunteersRead(BaseModel):
    class_session_id: UUID
    volunteers: list[SessionVolunteerRead]

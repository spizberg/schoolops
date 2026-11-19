"""Request and response contracts for volunteers."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schoolops.domain.enums import VolunteerStatus


class VolunteerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=40)
    email: EmailStr | None = None
    joined_on: date | None = None
    status: VolunteerStatus = VolunteerStatus.ACTIVE

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class VolunteerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=40)
    email: EmailStr | None = None
    joined_on: date | None = None
    status: VolunteerStatus | None = None

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class VolunteerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    phone: str
    email: str | None
    joined_on: date | None
    status: VolunteerStatus
    created_at: datetime
    updated_at: datetime


class VolunteerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    phone: str
    status: VolunteerStatus

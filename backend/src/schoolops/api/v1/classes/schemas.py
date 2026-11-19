"""Request and response contracts for classes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClassCreate(BaseModel):
    ministry_year_id: UUID
    name: str = Field(min_length=1, max_length=100)
    age_band: str = Field(min_length=1, max_length=50)
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    lead_volunteer_id: UUID | None = None
    room: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, gt=0)
    curriculum: str | None = None

    @field_validator("name", "age_band")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class ClassUpdate(BaseModel):
    ministry_year_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age_band: str | None = Field(default=None, min_length=1, max_length=50)
    age_min: int | None = Field(default=None, ge=0, le=120)
    age_max: int | None = Field(default=None, ge=0, le=120)
    lead_volunteer_id: UUID | None = None
    room: str | None = Field(default=None, max_length=50)
    capacity: int | None = Field(default=None, gt=0)
    curriculum: str | None = None

    @field_validator("name", "age_band")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ministry_year_id: UUID
    name: str
    age_band: str
    age_min: int | None
    age_max: int | None
    lead_volunteer_id: UUID | None
    room: str | None
    capacity: int | None
    curriculum: str | None
    created_at: datetime
    updated_at: datetime

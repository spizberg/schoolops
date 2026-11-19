"""Request and response contracts for households."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HouseholdCreate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    address: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class HouseholdUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    address: str | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class HouseholdRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

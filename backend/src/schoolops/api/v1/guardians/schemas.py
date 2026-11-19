"""Request and response contracts for guardians and child links."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class GuardianCreate(BaseModel):
    household_id: UUID | None = None
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=40)
    email: EmailStr | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class GuardianUpdate(BaseModel):
    household_id: UUID | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=40)
    email: EmailStr | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name", "phone")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class GuardianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    household_id: UUID | None
    first_name: str
    last_name: str
    phone: str
    email: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ChildGuardianCreate(BaseModel):
    guardian_id: UUID
    relationship: str = Field(min_length=1, max_length=50)
    is_primary: bool = False
    is_emergency: bool = False

    @field_validator("relationship")
    @classmethod
    def _strip_relationship(cls, value: str) -> str:
        return value.strip()


class ChildGuardianUpdate(BaseModel):
    relationship: str | None = Field(default=None, min_length=1, max_length=50)
    is_primary: bool | None = None
    is_emergency: bool | None = None

    @field_validator("relationship")
    @classmethod
    def _strip_relationship(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ChildGuardianRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    child_id: UUID
    guardian_id: UUID
    relationship: str
    is_primary: bool
    is_emergency: bool
    guardian: GuardianRead
    created_at: datetime
    updated_at: datetime


class GuardianSummary(BaseModel):
    """Compact guardian data used on the session roster."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    phone: str
    email: str | None
    relationship: str
    is_primary: bool
    is_emergency: bool

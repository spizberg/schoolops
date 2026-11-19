"""Request and response contracts for annual promotion."""

from uuid import UUID

from pydantic import BaseModel, Field


class ClassMapping(BaseModel):
    source_class_id: UUID
    target_class_id: UUID


class PromotionRequest(BaseModel):
    source_year_id: UUID
    target_year_id: UUID
    mappings: list[ClassMapping] = Field(min_length=1)


class PromotionAssignment(BaseModel):
    child_id: UUID
    child_name: str
    source_class_id: UUID
    source_class_name: str
    target_class_id: UUID
    target_class_name: str
    age_at_target_start: int
    target_age_band: str


class PromotionUnmatched(BaseModel):
    child_id: UUID
    child_name: str
    source_class_id: UUID | None
    source_class_name: str | None
    reason: str


class PromotionAlreadyEnrolled(BaseModel):
    child_id: UUID
    child_name: str
    target_class_id: UUID
    target_class_name: str


class PromotionCounts(BaseModel):
    assign: int
    unmatched: int
    already_enrolled: int


class PromotionPreviewRead(BaseModel):
    assignments: list[PromotionAssignment]
    unmatched: list[PromotionUnmatched]
    already_enrolled: list[PromotionAlreadyEnrolled]
    counts: PromotionCounts


class PromotionApplyRead(BaseModel):
    created: int
    skipped: int
    enrollment_ids: list[UUID]

"""HTTP routes for annual promotion."""

from fastapi import APIRouter

from schoolops.api.deps import SessionDep

from . import service
from .schemas import PromotionApplyRead, PromotionPreviewRead, PromotionRequest

router = APIRouter(prefix="/promotions", tags=["promotion"])


@router.post(
    "/preview",
    response_model=PromotionPreviewRead,
    summary="Preview a source-to-target class promotion",
)
async def preview_promotion(payload: PromotionRequest, session: SessionDep) -> PromotionPreviewRead:
    return await service.preview_promotion(session, payload)


@router.post(
    "/apply",
    response_model=PromotionApplyRead,
    summary="Apply a reviewed promotion mapping",
)
async def apply_promotion(payload: PromotionRequest, session: SessionDep) -> PromotionApplyRead:
    return await service.apply_promotion(session, payload)

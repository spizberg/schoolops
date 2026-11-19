"""HTTP routes for households."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.core.pagination import Page

from . import service
from .schemas import HouseholdCreate, HouseholdRead, HouseholdUpdate

router = APIRouter(prefix="/households", tags=["households"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[HouseholdRead], summary="List households")
async def list_households(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[HouseholdRead]:
    households, total = await service.list_households(session, q=q, limit=limit, offset=offset)
    return Page(
        items=[HouseholdRead.model_validate(household) for household in households],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=HouseholdRead, status_code=201, summary="Create a household")
async def create_household(
    payload: HouseholdCreate, session: SessionDep, response: Response
) -> HouseholdRead:
    household = await service.create_household(session, payload)
    response.headers["Location"] = f"/v1/households/{household.id}"
    return HouseholdRead.model_validate(household)


@router.get("/{household_id}", response_model=HouseholdRead, summary="Get a household")
async def get_household(household_id: UUID, session: SessionDep) -> HouseholdRead:
    household = await service.get_household(session, household_id)
    return HouseholdRead.model_validate(household)


@router.patch("/{household_id}", response_model=HouseholdRead, summary="Update a household")
async def update_household(
    household_id: UUID, payload: HouseholdUpdate, session: SessionDep
) -> HouseholdRead:
    household = await service.get_household(session, household_id)
    updated = await service.update_household(session, household, payload)
    return HouseholdRead.model_validate(updated)

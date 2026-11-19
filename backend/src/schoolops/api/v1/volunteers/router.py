"""HTTP routes for volunteers."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.core.pagination import Page
from schoolops.domain.enums import VolunteerStatus

from . import service
from .schemas import VolunteerCreate, VolunteerRead, VolunteerUpdate

router = APIRouter(prefix="/volunteers", tags=["volunteers"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[VolunteerRead], summary="List volunteers")
async def list_volunteers(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status: VolunteerStatus | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[VolunteerRead]:
    volunteers, total = await service.list_volunteers(
        session, q=q, status=status, limit=limit, offset=offset
    )
    return Page(
        items=[VolunteerRead.model_validate(volunteer) for volunteer in volunteers],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=VolunteerRead, status_code=201, summary="Create a volunteer")
async def create_volunteer(
    payload: VolunteerCreate, session: SessionDep, response: Response
) -> VolunteerRead:
    volunteer = await service.create_volunteer(session, payload)
    response.headers["Location"] = f"/v1/volunteers/{volunteer.id}"
    return VolunteerRead.model_validate(volunteer)


@router.get("/{volunteer_id}", response_model=VolunteerRead, summary="Get a volunteer")
async def get_volunteer(volunteer_id: UUID, session: SessionDep) -> VolunteerRead:
    volunteer = await service.get_volunteer(session, volunteer_id)
    return VolunteerRead.model_validate(volunteer)


@router.patch("/{volunteer_id}", response_model=VolunteerRead, summary="Update a volunteer")
async def update_volunteer(
    volunteer_id: UUID, payload: VolunteerUpdate, session: SessionDep
) -> VolunteerRead:
    volunteer = await service.get_volunteer(session, volunteer_id)
    updated = await service.update_volunteer(session, volunteer, payload)
    return VolunteerRead.model_validate(updated)


@router.delete(
    "/{volunteer_id}",
    status_code=204,
    summary="Deactivate a volunteer (history is preserved)",
)
async def deactivate_volunteer(volunteer_id: UUID, session: SessionDep) -> Response:
    volunteer = await service.get_volunteer(session, volunteer_id)
    await service.deactivate_volunteer(session, volunteer)
    return Response(status_code=204)

"""HTTP routes for guardians and child-guardian links."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.api.v1.children.service import get_child
from schoolops.core.pagination import Page

from . import service
from .schemas import (
    ChildGuardianCreate,
    ChildGuardianRead,
    ChildGuardianUpdate,
    GuardianCreate,
    GuardianRead,
    GuardianUpdate,
)

router = APIRouter(prefix="/guardians", tags=["guardians"])
child_guardians_router = APIRouter(prefix="/children", tags=["guardians"])
links_router = APIRouter(prefix="/child-guardians", tags=["guardians"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[GuardianRead], summary="Search guardians")
async def list_guardians(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    household_id: UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[GuardianRead]:
    guardians, total = await service.list_guardians(
        session, q=q, household_id=household_id, limit=limit, offset=offset
    )
    return Page(
        items=[GuardianRead.model_validate(guardian) for guardian in guardians],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=GuardianRead, status_code=201, summary="Create a guardian")
async def create_guardian(
    payload: GuardianCreate, session: SessionDep, response: Response
) -> GuardianRead:
    guardian = await service.create_guardian(session, payload)
    response.headers["Location"] = f"/v1/guardians/{guardian.id}"
    return GuardianRead.model_validate(guardian)


@router.get("/{guardian_id}", response_model=GuardianRead, summary="Get a guardian")
async def get_guardian(guardian_id: UUID, session: SessionDep) -> GuardianRead:
    guardian = await service.get_guardian(session, guardian_id)
    return GuardianRead.model_validate(guardian)


@router.patch("/{guardian_id}", response_model=GuardianRead, summary="Update a guardian")
async def update_guardian(
    guardian_id: UUID, payload: GuardianUpdate, session: SessionDep
) -> GuardianRead:
    guardian = await service.get_guardian(session, guardian_id)
    updated = await service.update_guardian(session, guardian, payload)
    return GuardianRead.model_validate(updated)


@router.delete("/{guardian_id}", status_code=204, summary="Delete a guardian")
async def delete_guardian(guardian_id: UUID, session: SessionDep) -> Response:
    guardian = await service.get_guardian(session, guardian_id)
    await service.delete_guardian(session, guardian)
    return Response(status_code=204)


@child_guardians_router.get(
    "/{child_id}/guardians",
    response_model=list[ChildGuardianRead],
    summary="List a child's guardians",
)
async def list_child_guardians(child_id: UUID, session: SessionDep) -> list[ChildGuardianRead]:
    await get_child(session, child_id)
    links = await service.list_child_guardians(session, child_id)
    return [ChildGuardianRead.model_validate(link) for link in links]


@child_guardians_router.post(
    "/{child_id}/guardians",
    response_model=ChildGuardianRead,
    status_code=201,
    summary="Link a guardian to a child",
)
async def create_child_guardian(
    child_id: UUID,
    payload: ChildGuardianCreate,
    session: SessionDep,
    response: Response,
) -> ChildGuardianRead:
    child = await get_child(session, child_id)
    link = await service.create_child_guardian(session, child, payload)
    response.headers["Location"] = f"/v1/child-guardians/{link.id}"
    return ChildGuardianRead.model_validate(link)


@links_router.patch(
    "/{link_id}", response_model=ChildGuardianRead, summary="Update a guardian link"
)
async def update_child_guardian(
    link_id: UUID, payload: ChildGuardianUpdate, session: SessionDep
) -> ChildGuardianRead:
    link = await service.get_child_guardian(session, link_id)
    updated = await service.update_child_guardian(session, link, payload)
    return ChildGuardianRead.model_validate(updated)


@links_router.post(
    "/{link_id}/set-primary",
    response_model=ChildGuardianRead,
    summary="Make a guardian the primary contact",
)
async def set_primary(link_id: UUID, session: SessionDep) -> ChildGuardianRead:
    link = await service.get_child_guardian(session, link_id)
    updated = await service.set_primary(session, link)
    return ChildGuardianRead.model_validate(updated)


@links_router.delete("/{link_id}", status_code=204, summary="Remove a guardian link")
async def delete_child_guardian(link_id: UUID, session: SessionDep) -> Response:
    link = await service.get_child_guardian(session, link_id)
    await service.delete_child_guardian(session, link)
    return Response(status_code=204)

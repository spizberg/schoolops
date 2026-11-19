"""HTTP routes for classes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.core.pagination import Page

from . import service
from .schemas import ClassCreate, ClassRead, ClassUpdate

router = APIRouter(prefix="/classes", tags=["classes"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[ClassRead], summary="List classes")
async def list_classes(
    session: SessionDep,
    ministry_year_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[ClassRead]:
    classes, total = await service.list_classes(
        session,
        ministry_year_id=ministry_year_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[ClassRead.model_validate(school_class) for school_class in classes],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ClassRead, status_code=201, summary="Create a class")
async def create_class(payload: ClassCreate, session: SessionDep, response: Response) -> ClassRead:
    school_class = await service.create_class(session, payload)
    response.headers["Location"] = f"/v1/classes/{school_class.id}"
    return ClassRead.model_validate(school_class)


@router.get("/{class_id}", response_model=ClassRead, summary="Get a class")
async def get_class(class_id: UUID, session: SessionDep) -> ClassRead:
    school_class = await service.get_class(session, class_id)
    return ClassRead.model_validate(school_class)


@router.patch("/{class_id}", response_model=ClassRead, summary="Update a class")
async def update_class(class_id: UUID, payload: ClassUpdate, session: SessionDep) -> ClassRead:
    school_class = await service.get_class(session, class_id)
    updated = await service.update_class(session, school_class, payload)
    return ClassRead.model_validate(updated)


@router.delete("/{class_id}", status_code=204, summary="Delete an empty class")
async def delete_class(class_id: UUID, session: SessionDep) -> Response:
    school_class = await service.get_class(session, class_id)
    await service.delete_class(session, school_class)
    return Response(status_code=204)

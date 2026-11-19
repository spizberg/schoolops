"""HTTP routes for changing or ending an enrollment."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.api.v1.classes.service import get_class
from schoolops.core.pagination import Page

from . import service
from .schemas import EnrollmentCreate, EnrollmentRead, EnrollmentUpdate, RosterEntryRead

router = APIRouter(prefix="/enrollments", tags=["enrollments"])
class_enrollments_router = APIRouter(prefix="/classes", tags=["enrollments"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@class_enrollments_router.get(
    "/{class_id}/enrollments",
    response_model=Page[RosterEntryRead],
    summary="List the roster active on a date",
)
async def list_roster(
    class_id: UUID,
    session: SessionDep,
    on_date: Annotated[date | None, Query()] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[RosterEntryRead]:
    school_class = await get_class(session, class_id)
    enrollments, total = await service.list_roster(
        session,
        school_class,
        on_date=on_date or date.today(),
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[RosterEntryRead.model_validate(enrollment) for enrollment in enrollments],
        total=total,
        limit=limit,
        offset=offset,
    )


@class_enrollments_router.post(
    "/{class_id}/enrollments",
    response_model=EnrollmentRead,
    status_code=201,
    summary="Enroll a child",
)
async def enroll_child(
    class_id: UUID,
    payload: EnrollmentCreate,
    session: SessionDep,
    response: Response,
) -> EnrollmentRead:
    school_class = await get_class(session, class_id)
    enrollment = await service.enroll_child(session, school_class, payload)
    response.headers["Location"] = f"/v1/enrollments/{enrollment.id}"
    return EnrollmentRead.model_validate(enrollment)


@router.patch("/{enrollment_id}", response_model=EnrollmentRead, summary="Update an enrollment")
async def update_enrollment(
    enrollment_id: UUID, payload: EnrollmentUpdate, session: SessionDep
) -> EnrollmentRead:
    enrollment = await service.get_enrollment(session, enrollment_id)
    updated = await service.update_enrollment(session, enrollment, payload)
    return EnrollmentRead.model_validate(updated)


@router.delete(
    "/{enrollment_id}",
    status_code=204,
    summary="End an enrollment without deleting its history",
)
async def end_enrollment(enrollment_id: UUID, session: SessionDep) -> Response:
    enrollment = await service.get_enrollment(session, enrollment_id)
    await service.end_enrollment(session, enrollment)
    return Response(status_code=204)

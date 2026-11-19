"""HTTP routes for class sessions and session volunteers."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from schoolops.api.deps import SessionDep
from schoolops.api.v1.classes.service import get_class
from schoolops.core.pagination import Page

from . import service
from .schemas import (
    SessionCreate,
    SessionGenerateRequest,
    SessionGenerateResult,
    SessionRead,
    SessionUpdate,
    SessionVolunteersRead,
    SessionVolunteersUpdate,
)

class_sessions_router = APIRouter(prefix="/classes", tags=["sessions"])
sessions_router = APIRouter(prefix="/class-sessions", tags=["sessions"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@class_sessions_router.get(
    "/{class_id}/sessions",
    response_model=Page[SessionRead],
    summary="List class sessions",
)
async def list_sessions(
    class_id: UUID,
    session: SessionDep,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[SessionRead]:
    school_class = await get_class(session, class_id)
    sessions, total = await service.list_sessions(
        session,
        school_class,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[SessionRead.model_validate(item) for item in sessions],
        total=total,
        limit=limit,
        offset=offset,
    )


@class_sessions_router.post(
    "/{class_id}/sessions",
    response_model=SessionRead,
    status_code=201,
    summary="Create a session",
)
async def create_session(
    class_id: UUID,
    payload: SessionCreate,
    session: SessionDep,
    response: Response,
) -> SessionRead:
    school_class = await get_class(session, class_id)
    created = await service.create_session(session, school_class, payload)
    response.headers["Location"] = f"/v1/class-sessions/{created.id}"
    return SessionRead.model_validate(created)


@class_sessions_router.post(
    "/{class_id}/sessions/generate",
    response_model=SessionGenerateResult,
    summary="Generate sessions for a weekday pattern",
)
async def generate_sessions(
    class_id: UUID, payload: SessionGenerateRequest, session: SessionDep
) -> SessionGenerateResult:
    school_class = await get_class(session, class_id)
    return await service.generate_sessions(session, school_class, payload)


@sessions_router.get("/{session_id}", response_model=SessionRead, summary="Get a session")
async def get_session(session_id: UUID, session: SessionDep) -> SessionRead:
    class_session = await service.get_session(session, session_id)
    return SessionRead.model_validate(class_session)


@sessions_router.patch("/{session_id}", response_model=SessionRead, summary="Update a session")
async def update_session(
    session_id: UUID, payload: SessionUpdate, session: SessionDep
) -> SessionRead:
    class_session = await service.get_session(session, session_id)
    updated = await service.update_session(session, class_session, payload)
    return SessionRead.model_validate(updated)


@sessions_router.delete("/{session_id}", status_code=204, summary="Delete a session")
async def delete_session(session_id: UUID, session: SessionDep) -> Response:
    class_session = await service.get_session(session, session_id)
    await service.delete_session(session, class_session)
    return Response(status_code=204)


@sessions_router.get(
    "/{session_id}/volunteers",
    response_model=SessionVolunteersRead,
    summary="List volunteers who served a session",
)
async def list_session_volunteers(session_id: UUID, session: SessionDep) -> SessionVolunteersRead:
    class_session = await service.get_session(session, session_id)
    return await service.list_session_volunteers(session, class_session)


@sessions_router.put(
    "/{session_id}/volunteers",
    response_model=SessionVolunteersRead,
    summary="Replace the volunteers who served a session",
)
async def replace_session_volunteers(
    session_id: UUID, payload: SessionVolunteersUpdate, session: SessionDep
) -> SessionVolunteersRead:
    class_session = await service.get_session(session, session_id)
    return await service.replace_session_volunteers(session, class_session, payload.volunteer_ids)

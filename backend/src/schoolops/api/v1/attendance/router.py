"""HTTP routes for session attendance."""

from uuid import UUID

from fastapi import APIRouter

from schoolops.api.deps import AdminUser, SessionDep
from schoolops.api.v1.sessions.service import get_session

from . import service
from .schemas import AttendanceBulkUpdate, SessionAttendanceRead

router = APIRouter(prefix="/class-sessions", tags=["attendance"])


@router.get(
    "/{session_id}/attendance",
    response_model=SessionAttendanceRead,
    summary="Get the roster, visitors, and attendance for a session",
)
async def get_attendance(session_id: UUID, session: SessionDep) -> SessionAttendanceRead:
    class_session = await get_session(session, session_id)
    return await service.get_attendance(session, class_session)


@router.put(
    "/{session_id}/attendance",
    response_model=SessionAttendanceRead,
    summary="Record or update attendance and visitors",
)
async def put_attendance(
    session_id: UUID,
    payload: AttendanceBulkUpdate,
    session: SessionDep,
    actor: AdminUser,
) -> SessionAttendanceRead:
    class_session = await get_session(session, session_id)
    return await service.put_attendance(session, class_session, payload, actor_id=actor.id)

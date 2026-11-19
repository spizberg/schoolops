"""HTTP routes for the read-only audit trail."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from schoolops.api.deps import SessionDep
from schoolops.core.pagination import Page

from . import service
from .schemas import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get("", response_model=Page[AuditLogRead], summary="Query audit records")
async def list_audit_logs(
    session: SessionDep,
    entity_type: Annotated[str | None, Query(max_length=50)] = None,
    entity_id: UUID | None = None,
    action: Annotated[str | None, Query(max_length=20)] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Page[AuditLogRead]:
    items, total = await service.list_logs(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)

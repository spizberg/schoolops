"""Read-only audit log queries."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.db.models import AuditLog, User

from .schemas import AuditLogRead


async def list_logs(
    session: AsyncSession,
    *,
    entity_type: str | None,
    entity_id: UUID | None,
    action: str | None,
    from_date: date | None,
    to_date: date | None,
    limit: int,
    offset: int,
) -> tuple[list[AuditLogRead], int]:
    stmt = select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if from_date is not None:
        stmt = stmt.where(func.date(AuditLog.created_at) >= from_date)
    if to_date is not None:
        stmt = stmt.where(func.date(AuditLog.created_at) <= to_date)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = (
        await session.execute(stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset))
    ).all()
    items = [
        AuditLogRead(
            id=entry.id,
            actor_user_id=entry.actor_user_id,
            actor_email=actor_email,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            changes=entry.changes,
            created_at=entry.created_at,
        )
        for entry, actor_email in rows
    ]
    return items, total

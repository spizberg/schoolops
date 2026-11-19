"""Helpers for writing audit entries alongside a mutation."""

from typing import Any, cast
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from schoolops.db.models import AuditLog

ACTOR_KEY = "audit_actor_id"


def snapshot(obj: object, fields: tuple[str, ...]) -> dict[str, Any]:
    """Return a JSON-safe snapshot of the selected model fields."""
    return cast(
        dict[str, Any],
        jsonable_encoder({field: getattr(obj, field) for field in fields}),
    )


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Return only the fields whose serialized values changed."""
    return {
        field: {"from": before.get(field), "to": value}
        for field, value in after.items()
        if before.get(field) != value
    }


async def record(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID,
    changes: dict[str, Any],
    actor_id: UUID | None = None,
) -> None:
    """Queue an audit row in the current transaction."""
    session.add(
        AuditLog(
            actor_user_id=actor_id or session.info.get(ACTOR_KEY),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=jsonable_encoder(changes),
        )
    )

"""Helpers for enum columns stored as PostgreSQL enum types."""

import enum

from sqlalchemy import Enum as SAEnum


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist the lowercase ``value`` rather than the member name."""
    return [str(member.value) for member in enum_cls]


def str_enum(enum_cls: type[enum.Enum], *, name: str) -> SAEnum:
    """Build an enum column type with a stable type name and value mapping."""
    return SAEnum(enum_cls, name=name, values_callable=_enum_values)

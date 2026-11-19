"""Generic pagination envelope for list endpoints."""

from pydantic import BaseModel


class Page[T](BaseModel):
    """One page of results plus the total number of matching rows."""

    items: list[T]
    total: int
    limit: int
    offset: int

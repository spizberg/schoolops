"""Per-request correlation id shared with the log formatter."""

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def reset_request_id() -> None:
    _request_id.set(None)


def current_request_id() -> str | None:
    return _request_id.get()

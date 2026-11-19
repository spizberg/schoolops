"""Structured JSON logging for application logs."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from schoolops.core.request_context import current_request_id


class JsonFormatter(logging.Formatter):
    """One JSON object per log record, with request correlation."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or current_request_id()
        if request_id:
            payload["request_id"] = request_id
        http = getattr(record, "http", None)
        if http is not None:
            payload["http"] = http
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Install a single JSON handler on the root logger."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == "cbsg-json":
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.set_name("cbsg-json")
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)

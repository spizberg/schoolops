"""In-process login rate limiting for the MVP.

One process keeps a small map of failed attempts per ``ip:email`` key. A gateway or
shared store replaces this when the API runs more than one worker.
"""

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class LoginRateLimiter:
    """Allow ``max_attempts`` failures per key inside a rolling time window."""

    max_attempts: int = 5
    window_seconds: float = 15 * 60
    _failures: dict[str, list[float]] = field(default_factory=dict)

    def retry_after(self, key: str, *, now: float | None = None) -> int | None:
        """Return seconds to wait when blocked, otherwise ``None``."""
        current = monotonic() if now is None else now
        attempts = self._recent(key, current)
        if len(attempts) < self.max_attempts:
            return None
        oldest = attempts[0]
        return max(1, int(self.window_seconds - (current - oldest)))

    def record_failure(self, key: str, *, now: float | None = None) -> None:
        current = monotonic() if now is None else now
        self._failures[key] = [*self._recent(key, current), current]

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def clear(self) -> None:
        """Drop all state. Used by tests and on process restart."""
        self._failures.clear()

    def _recent(self, key: str, now: float) -> list[float]:
        attempts = [
            attempt
            for attempt in self._failures.get(key, [])
            if now - attempt < self.window_seconds
        ]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts


login_rate_limiter = LoginRateLimiter()

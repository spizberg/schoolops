"""Ministry-calendar rules.

The meeting week is stored per ministry year as ISO weekday numbers (Monday = 1,
Sunday = 7). A date is a meeting day when its weekday is configured, it is inside the
year, and it is not listed as a no-class day. This deployment meets on Sunday only, but
the rule stays data-driven.
"""

from collections.abc import Iterable
from datetime import date, timedelta


def is_meeting_day(
    day: date,
    meeting_weekdays: Iterable[int],
    no_class_days: Iterable[date] = (),
) -> bool:
    """Return whether ``day`` is a configured meeting day."""
    return day.isoweekday() in meeting_weekdays and day not in set(no_class_days)


def list_meeting_days(
    start: date,
    end: date,
    meeting_weekdays: Iterable[int],
    no_class_days: Iterable[date] = (),
) -> list[date]:
    """List every meeting day in the inclusive range ``start``..``end``."""
    if start > end:
        return []

    weekdays = set(meeting_weekdays)
    closures = set(no_class_days)
    days: list[date] = []
    current = start
    while current <= end:
        if current.isoweekday() in weekdays and current not in closures:
            days.append(current)
        current += timedelta(days=1)
    return days

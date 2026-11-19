"""Enumerations shared by the database layer, services, and API schemas."""

from enum import StrEnum


class VolunteerStatus(StrEnum):
    """Lifecycle of a volunteer. Volunteers are never hard-deleted."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class ChildStatus(StrEnum):
    """Lifecycle of a child."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    VISITOR = "visitor"
    LEFT = "left"


class PhotoConsent(StrEnum):
    """Whether a household has consented to photos of the child."""

    GRANTED = "granted"
    DENIED = "denied"
    NOT_RECORDED = "not_recorded"


class NoClassDayKind(StrEnum):
    """Why a date is not a meeting day."""

    HOLIDAY = "holiday"
    CLOSURE = "closure"
    OTHER = "other"


class AttendanceStatus(StrEnum):
    """Attendance outcome for one child in one session."""

    PRESENT = "present"
    ABSENT = "absent"


class UserRole(StrEnum):
    """Roles are modeled from day one; only ``admin`` is enabled in the MVP."""

    ADMIN = "admin"
    LEADER = "leader"
    PARENT = "parent"

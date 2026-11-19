"""ORM model registry. Importing this module registers every table on ``Base``."""

from schoolops.db.models.audit_log import AuditLog
from schoolops.db.models.child import Child
from schoolops.db.models.child_guardian import ChildGuardian
from schoolops.db.models.class_group import ClassGroup
from schoolops.db.models.class_session import AttendanceRecord, ClassSession, SessionVolunteer
from schoolops.db.models.enrollment import Enrollment
from schoolops.db.models.guardian import Guardian
from schoolops.db.models.household import Household
from schoolops.db.models.ministry_year import MinistryYear
from schoolops.db.models.no_class_day import NoClassDay
from schoolops.db.models.user import User
from schoolops.db.models.volunteer import Volunteer

__all__ = [
    "AttendanceRecord",
    "AuditLog",
    "Child",
    "ChildGuardian",
    "ClassGroup",
    "ClassSession",
    "Enrollment",
    "Guardian",
    "Household",
    "MinistryYear",
    "NoClassDay",
    "SessionVolunteer",
    "User",
    "Volunteer",
]

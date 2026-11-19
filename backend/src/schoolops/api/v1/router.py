"""Versioned API router. Every route except health and login requires an admin token."""

from fastapi import APIRouter, Depends

from schoolops.api.deps import get_current_admin
from schoolops.api.v1.attendance.router import router as attendance_router
from schoolops.api.v1.audit.router import router as audit_router
from schoolops.api.v1.auth.router import protected_router as auth_protected_router
from schoolops.api.v1.auth.router import router as auth_router
from schoolops.api.v1.children.router import router as children_router
from schoolops.api.v1.classes.router import router as classes_router
from schoolops.api.v1.enrollments.router import class_enrollments_router
from schoolops.api.v1.enrollments.router import router as enrollments_router
from schoolops.api.v1.guardians.router import child_guardians_router
from schoolops.api.v1.guardians.router import links_router as guardian_links_router
from schoolops.api.v1.guardians.router import router as guardians_router
from schoolops.api.v1.households.router import router as households_router
from schoolops.api.v1.ministry_years.router import calendar_router
from schoolops.api.v1.ministry_years.router import router as ministry_years_router
from schoolops.api.v1.promotion.router import router as promotion_router
from schoolops.api.v1.reports.router import router as reports_router
from schoolops.api.v1.sessions.router import class_sessions_router, sessions_router
from schoolops.api.v1.volunteers.router import router as volunteers_router

api_router = APIRouter()
api_router.include_router(auth_router)

protected_router = APIRouter(dependencies=[Depends(get_current_admin)])
protected_router.include_router(auth_protected_router)
protected_router.include_router(ministry_years_router)
protected_router.include_router(calendar_router)
protected_router.include_router(volunteers_router)
protected_router.include_router(households_router)
protected_router.include_router(guardians_router)
protected_router.include_router(child_guardians_router)
protected_router.include_router(guardian_links_router)
protected_router.include_router(children_router)
protected_router.include_router(classes_router)
protected_router.include_router(class_enrollments_router)
protected_router.include_router(enrollments_router)
protected_router.include_router(promotion_router)
protected_router.include_router(class_sessions_router)
protected_router.include_router(sessions_router)
protected_router.include_router(attendance_router)
protected_router.include_router(reports_router)
protected_router.include_router(audit_router)

api_router.include_router(protected_router)

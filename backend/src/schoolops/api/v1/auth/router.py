"""Public login endpoint and the protected current-user endpoint."""

from fastapi import APIRouter, Request

from schoolops.api.deps import AdminUser, SessionDep

from . import service
from .schemas import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
protected_router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Log in")
async def login(payload: LoginRequest, request: Request, session: SessionDep) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    return await service.login(
        session,
        payload,
        client_ip=client_ip,
        settings=request.app.state.settings,
    )


@protected_router.get("/me", response_model=UserRead, summary="Get the current user")
async def read_current_user(user: AdminUser) -> UserRead:
    return UserRead.model_validate(user)

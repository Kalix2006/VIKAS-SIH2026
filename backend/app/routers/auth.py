"""Authentication endpoints.

Handles user registration, login, token refresh, and profile retrieval.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.limiter import limiter
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthError
from app.services.auth import get_me as svc_get_me
from app.services.auth import login as svc_login
from app.services.auth import refresh as svc_refresh
from app.services.auth import signup as svc_signup

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
@limiter.limit("5/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new user.

    Returns access and refresh tokens on success.
    """
    try:
        return await svc_signup(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role.value,
            district_id=payload.district_id,
            institute_id=payload.institute_id,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Authenticate and receive tokens."""
    try:
        return await svc_login(
            db=db,
            email=payload.email,
            password=payload.password,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    try:
        return await svc_refresh(
            db=db,
            raw_refresh_token=payload.refresh_token,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    try:
        user = await svc_get_me(db=db, user_id=current_user["sub"])
        return UserResponse.model_validate(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

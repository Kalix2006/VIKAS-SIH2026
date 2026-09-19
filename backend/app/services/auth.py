"""Authentication business logic.

Handles user registration, login, token refresh, and profile retrieval.
All DB operations use parameterized queries via SQLAlchemy ORM.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse


class AuthError(Exception):
    """Base exception for auth operations."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def signup(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    role: str,
    district_id: uuid.UUID,
    institute_id: uuid.UUID | None = None,
) -> TokenResponse:
    """Register a new user and issue tokens.

    Raises:
        AuthError: If email already exists.
    """
    # Check for existing user
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise AuthError("Email already registered", status_code=409)

    # Create user
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        district_id=district_id,
        institute_id=institute_id,
    )
    db.add(user)
    await db.flush()  # Get the generated UUID before commit

    # Issue tokens
    token_response = await _issue_tokens(db, user)
    await db.commit()
    return token_response


async def login(
    db: AsyncSession,
    email: str,
    password: str,
) -> TokenResponse:
    """Authenticate a user and issue tokens.

    Raises:
        AuthError: If credentials are invalid.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        # Deliberately vague to prevent user enumeration
        raise AuthError("Invalid email or password", status_code=401)

    token_response = await _issue_tokens(db, user)
    await db.commit()
    return token_response


async def refresh(
    db: AsyncSession,
    raw_refresh_token: str,
) -> TokenResponse:
    """Validate a refresh token and issue a new token pair.

    Implements token rotation: the old refresh token is revoked
    and a new one is issued. This limits the window of compromise
    if a refresh token is stolen.

    Raises:
        AuthError: If the refresh token is invalid, expired, or revoked.
    """
    token_hash = hash_refresh_token(raw_refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise AuthError("Invalid refresh token", status_code=401)
    if stored_token.revoked:
        raise AuthError("Refresh token has been revoked", status_code=401)
    if stored_token.expires_at < datetime.now(UTC):
        raise AuthError("Refresh token has expired", status_code=401)

    # Revoke the old token (rotation)
    stored_token.revoked = True

    # Load the user
    user_stmt = select(User).where(User.id == stored_token.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if user is None:
        raise AuthError("User not found", status_code=401)

    # Issue new token pair
    token_response = await _issue_tokens(db, user)
    await db.commit()
    return token_response


async def get_me(
    db: AsyncSession,
    user_id: str,
) -> User:
    """Retrieve the current user's profile.

    Raises:
        AuthError: If user not found (should not happen for valid JWTs).
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError("User not found", status_code=404)
    return user


async def _issue_tokens(
    db: AsyncSession,
    user: User,
) -> TokenResponse:
    """Create an access + refresh token pair for a user."""
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        district_id=str(user.district_id),
        institute_id=(str(user.institute_id) if user.institute_id else None),
    )

    raw_refresh = generate_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=datetime.now(UTC)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_record)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
    )

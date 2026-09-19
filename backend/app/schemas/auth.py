"""Pydantic schemas for authentication endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class SignupRequest(BaseModel):
    """POST /auth/signup request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(
        max_length=320,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    district_id: uuid.UUID
    institute_id: uuid.UUID | None = None


class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """POST /auth/refresh request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    refresh_token: str = Field(min_length=10, max_length=512)


class TokenResponse(BaseModel):
    """Token pair returned on signup, login, and refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """GET /auth/me response body."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    district_id: uuid.UUID
    institute_id: uuid.UUID | None
    created_at: datetime

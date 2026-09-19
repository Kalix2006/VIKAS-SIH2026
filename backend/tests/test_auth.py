"""Tests for authentication endpoints.

Covers /auth/signup, /auth/login, /auth/refresh, /auth/me.
"""

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.district import District
from app.models.enums import UserRole


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, test_district: District) -> None:
    """Verify signup creates a new user and returns JWT token pair."""
    unique_email = f"signup_{uuid.uuid4().hex[:8]}@test.vikas"
    payload = {
        "email": unique_email,
        "password": "securepassword123",
        "full_name": "New Trainee User",
        "role": "trainee",
        "district_id": str(test_district.id),
    }
    response = await client.post("/auth/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_signup_duplicate_email(
    client: AsyncClient, test_district: District
) -> None:
    """Verify signup with an existing email returns 409 Conflict."""
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@test.vikas"
    payload = {
        "email": unique_email,
        "password": "securepassword123",
        "full_name": "Duplicate User",
        "role": "trainee",
        "district_id": str(test_district.id),
    }
    # First signup
    res1 = await client.post("/auth/signup", json=payload)
    assert res1.status_code == 200

    # Second signup with same email
    res2 = await client.post("/auth/signup", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(
    client: AsyncClient, test_district: District, create_test_user
) -> None:
    """Verify login with correct credentials returns token pair."""
    email = f"login_{uuid.uuid4().hex[:8]}@test.vikas"
    password = "correctpassword123"
    await create_test_user(
        email=email,
        role=UserRole.PLANNER,
        district_id=test_district.id,
        password=password,
    )

    response = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(
    client: AsyncClient, test_district: District, create_test_user
) -> None:
    """Verify login with invalid password returns 401."""
    email = f"wrong_pass_{uuid.uuid4().hex[:8]}@test.vikas"
    await create_test_user(
        email=email,
        role=UserRole.EMPLOYER,
        district_id=test_district.id,
        password="correctpassword123",
    )

    response = await client.post(
        "/auth/login",
        json={"email": email, "password": "wrongpassword!"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """Verify login with unknown email returns 401."""
    response = await client.post(
        "/auth/login",
        json={
            "email": f"nonexistent_{uuid.uuid4().hex[:8]}@test.vikas",
            "password": "anypassword123",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success_and_rotation(
    client: AsyncClient, test_district: District
) -> None:
    """Verify refresh token exchanges for new pair and revokes the old one."""
    email = f"refresh_{uuid.uuid4().hex[:8]}@test.vikas"
    # 1. Signup to obtain initial refresh token
    signup_res = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "password12345",
            "full_name": "Refresh Test User",
            "role": "trainee",
            "district_id": str(test_district.id),
        },
    )
    assert signup_res.status_code == 200
    old_refresh_token = signup_res.json()["refresh_token"]

    # 2. Use refresh token
    refresh_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    new_refresh_token = data["refresh_token"]
    assert new_refresh_token != old_refresh_token

    # 3. Attempting to reuse old refresh token must fail (revoked)
    reuse_res = await client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert reuse_res.status_code == 401
    assert "revoked" in reuse_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_me_endpoint_success(
    client: AsyncClient, test_district: District, create_test_user, auth_token_for
) -> None:
    """Verify GET /auth/me returns current user profile for valid token."""
    email = f"me_{uuid.uuid4().hex[:8]}@test.vikas"
    user = await create_test_user(
        email=email,
        role=UserRole.PANEL_MEMBER,
        district_id=test_district.id,
    )
    token = auth_token_for(user)

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["role"] == "panel_member"
    assert data["district_id"] == str(test_district.id)


@pytest.mark.asyncio
async def test_me_endpoint_unauthorized(client: AsyncClient) -> None:
    """Verify GET /auth/me without token returns 401/403."""
    response = await client.get("/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_expired_token_rejected(
    client: AsyncClient, test_district: District, create_test_user
) -> None:
    """Verify expired token is rejected with 401."""
    user = await create_test_user(
        email=f"expired_{uuid.uuid4().hex[:8]}@test.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )
    # Generate already-expired token (-5 minutes)
    expired_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        district_id=str(user.district_id),
        expires_delta=timedelta(minutes=-5),
    )

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401

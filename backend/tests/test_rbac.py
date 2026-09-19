"""Tests for RBAC (require_role) and Scope Enforcement (require_own_scope)."""

import uuid

import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient

from app.core.deps import require_own_scope, require_role
from app.main import app
from app.models.district import District
from app.models.enums import UserRole

# Temporary test router to verify require_role and require_own_scope
rbac_test_router = APIRouter(prefix="/test-rbac", tags=["test-rbac"])


@rbac_test_router.get(
    "/trainee-only",
    dependencies=[Depends(require_role("trainee"))],
)
async def trainee_only_route() -> dict[str, str]:
    return {"status": "ok", "role": "trainee"}


@rbac_test_router.get(
    "/institute-only",
    dependencies=[Depends(require_role("institute_admin"))],
)
async def institute_only_route() -> dict[str, str]:
    return {"status": "ok", "role": "institute_admin"}


@rbac_test_router.get(
    "/employer-only",
    dependencies=[Depends(require_role("employer"))],
)
async def employer_only_route() -> dict[str, str]:
    return {"status": "ok", "role": "employer"}


@rbac_test_router.get(
    "/planner-only",
    dependencies=[Depends(require_role("planner"))],
)
async def planner_only_route() -> dict[str, str]:
    return {"status": "ok", "role": "planner"}


@rbac_test_router.get(
    "/panel-only",
    dependencies=[Depends(require_role("panel_member"))],
)
async def panel_only_route() -> dict[str, str]:
    return {"status": "ok", "role": "panel_member"}


@rbac_test_router.get(
    "/district/{district_id}",
    dependencies=[Depends(require_own_scope("district_id"))],
)
async def scoped_district_route(district_id: uuid.UUID) -> dict[str, str]:
    return {"status": "ok", "district_id": str(district_id)}


# Register the temporary test router if not already registered
if not any(getattr(r, "prefix", None) == "/test-rbac" for r in app.routes):
    app.include_router(rbac_test_router)


@pytest.mark.asyncio
async def test_each_role_allowed_on_own_endpoint(
    client: AsyncClient,
    test_district: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Verify each role can successfully access its designated protected endpoint."""
    roles_and_endpoints = [
        (UserRole.TRAINEE, "/test-rbac/trainee-only"),
        (UserRole.INSTITUTE_ADMIN, "/test-rbac/institute-only"),
        (UserRole.EMPLOYER, "/test-rbac/employer-only"),
        (UserRole.PLANNER, "/test-rbac/planner-only"),
        (UserRole.PANEL_MEMBER, "/test-rbac/panel-only"),
    ]

    for role, endpoint in roles_and_endpoints:
        user = await create_test_user(
            email=f"user_{role.value}@test.vikas",
            role=role,
            district_id=test_district.id,
        )
        token = auth_token_for(user)
        response = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert (
            response.status_code == 200
        ), f"Role {role.value} failed to access {endpoint}"
        assert response.json()["role"] == role.value


@pytest.mark.asyncio
async def test_role_blocking(
    client: AsyncClient,
    test_district: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Verify unauthorized roles receive 403 Forbidden on protected endpoints."""
    trainee = await create_test_user(
        email="trainee_blocked@test.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )
    trainee_token = auth_token_for(trainee)

    # Trainee must be blocked from planner, institute, employer, panel endpoints
    forbidden_endpoints = [
        "/test-rbac/planner-only",
        "/test-rbac/institute-only",
        "/test-rbac/employer-only",
        "/test-rbac/panel-only",
    ]
    for endpoint in forbidden_endpoints:
        res = await client.get(
            endpoint,
            headers={"Authorization": f"Bearer {trainee_token}"},
        )
        assert res.status_code == 403
        assert "not authorized" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_employer_blocked_from_institute_endpoint(
    client: AsyncClient,
    test_district: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Verify employer cannot access institute_admin endpoint."""
    employer = await create_test_user(
        email="employer_blocked@test.vikas",
        role=UserRole.EMPLOYER,
        district_id=test_district.id,
    )
    token = auth_token_for(employer)
    res = await client.get(
        "/test-rbac/institute-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_require_own_scope_district_ownership(
    client: AsyncClient,
    test_district: District,
    test_district_beed: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Verify require_own_scope permits own district and blocks cross-district.

    Tests cross-district access blocking.
    """
    # User belonging to Pune
    pune_user = await create_test_user(
        email="pune_scope_user@test.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )
    token = auth_token_for(pune_user)

    # 1. Accessing own district (Pune) -> 200
    res_own = await client.get(
        f"/test-rbac/district/{test_district.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_own.status_code == 200

    # 2. Accessing different district (Beed) -> 403
    res_other = await client.get(
        f"/test-rbac/district/{test_district_beed.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_other.status_code == 403
    assert "mismatch" in res_other.json()["detail"].lower()


@pytest.mark.asyncio
async def test_require_own_scope_planner_bypass(
    client: AsyncClient,
    test_district: District,
    test_district_beed: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Verify planners bypass district scope check (cross-district oversight)."""
    planner = await create_test_user(
        email="planner_scope_bypass@test.vikas",
        role=UserRole.PLANNER,
        district_id=test_district.id,  # Planner is assigned to Pune
    )
    planner_token = auth_token_for(planner)

    # Planner accessing Beed district -> 200 OK (bypass granted)
    res = await client.get(
        f"/test-rbac/district/{test_district_beed.id}",
        headers={"Authorization": f"Bearer {planner_token}"},
    )
    assert res.status_code == 200

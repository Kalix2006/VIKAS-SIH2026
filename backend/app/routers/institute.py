"""Institute Admin API endpoints.

Handles flag reviews, acknowledgments, trainer refresher requests,
enrollment vs demand capacity analytics, and drift drill-downs.
All routes are role-gated to institute_admin and strictly scoped to
the admin's own institute_id.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_with_rls, require_role
from app.schemas.institute import (
    AcknowledgeFlagResponse,
    DriftDetailResponse,
    EnrollmentVsDemandResponse,
    InstituteFlagItem,
    TrainerRefresherRequestCreate,
    TrainerRefresherRequestResponse,
)
from app.services.institute import institute_service

router = APIRouter(prefix="/institute", tags=["institute"])

# Role dependency ensuring only institute_admin can access these endpoints
InstituteAdminUser = Annotated[dict[str, Any], Depends(require_role("institute_admin"))]


def _get_institute_id(user: dict[str, Any]) -> uuid.UUID:
    """Extract and validate institute_id from authenticated token."""
    inst_str = user.get("institute_id")
    if not inst_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an associated institute_id",
        )
    return uuid.UUID(str(inst_str))


@router.get("/flags", response_model=list[InstituteFlagItem])
async def get_flags(
    current_user: InstituteAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> list[InstituteFlagItem]:
    """Retrieve all flagged courses at the admin's own institute.

    Each course flag includes a one-line plain-language reason derived
    from its gap_type.
    """
    institute_id = _get_institute_id(current_user)
    return await institute_service.get_institute_flags(
        db=db,
        institute_id=institute_id,
    )


@router.post("/flags/{flag_id}/acknowledge", response_model=AcknowledgeFlagResponse)
async def acknowledge_flag(
    flag_id: uuid.UUID,
    current_user: InstituteAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> AcknowledgeFlagResponse:
    """Mark a flagged course as reviewed / acknowledged by the institute admin.

    Strictly scoped: rejects with 403 if the flag belongs to a course at
    another institute.
    """
    institute_id = _get_institute_id(current_user)
    user_id = uuid.UUID(current_user["sub"])
    return await institute_service.acknowledge_flag(
        db=db,
        flag_id=flag_id,
        user_id=user_id,
        institute_id=institute_id,
    )


@router.post(
    "/flags/{flag_id}/request-trainer-refresher",
    response_model=TrainerRefresherRequestResponse,
)
async def request_trainer_refresher(
    flag_id: uuid.UUID,
    payload: TrainerRefresherRequestCreate,
    current_user: InstituteAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> TrainerRefresherRequestResponse:
    """Submit a request for trainer upskilling / curriculum refresher.

    Creates a tracked database record and notifies district planners
    via in-app Alert.
    """
    institute_id = _get_institute_id(current_user)
    user_id = uuid.UUID(current_user["sub"])
    return await institute_service.request_trainer_refresher(
        db=db,
        flag_id=flag_id,
        user_id=user_id,
        institute_id=institute_id,
        notes=payload.notes,
    )


@router.get("/enrollment-vs-demand", response_model=EnrollmentVsDemandResponse)
async def get_enrollment_vs_demand(
    current_user: InstituteAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    course_id: Annotated[uuid.UUID | None, Query()] = None,
) -> EnrollmentVsDemandResponse:
    """Compare seats available vs local job posting volume for institute courses."""
    institute_id = _get_institute_id(current_user)
    return await institute_service.get_enrollment_vs_demand(
        db=db,
        institute_id=institute_id,
        course_id=course_id,
    )


@router.get("/flags/{flag_id}/detail", response_model=DriftDetailResponse)
async def get_flag_detail(
    flag_id: uuid.UUID,
    current_user: InstituteAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
) -> DriftDetailResponse:
    """Get score trend over time and specific skills that drove curriculum drift.

    Strictly scoped: returns 403 if flag belongs to another institute.
    """
    institute_id = _get_institute_id(current_user)
    return await institute_service.get_flag_drift_detail(
        db=db,
        flag_id=flag_id,
        institute_id=institute_id,
    )

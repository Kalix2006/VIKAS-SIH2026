"""Employer API endpoints.

Provides:
- GET /employer/skills-inferred: Inferred demand skills for quick validation
- POST /employer/validate: Skill confirmation and Groq-powered free text extraction
- POST /employer/hiring-signal: Structured hiring intent signaling
- GET /employer/aggregate-readiness: Strictly aggregate, privacy-preserving cohort readiness
- GET /employer/my-validations: Scoped list of employer's own submissions
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.enums import UserRole
from app.schemas.employer import (
    AggregateReadinessResponse,
    EmployerValidateRequest,
    EmployerValidateResponse,
    EmployerValidationListItem,
    HiringSignalRequest,
    HiringSignalResponse,
    SkillsInferredResponse,
)
from app.services.employer import employer_service

router = APIRouter(prefix="/employer", tags=["employer"])


@router.get(
    "/skills-inferred",
    response_model=SkillsInferredResponse,
    dependencies=[Depends(require_role(UserRole.EMPLOYER.value))],
)
async def get_skills_inferred(
    trade_id: Annotated[uuid.UUID, Query(..., description="Trade UUID")],
    district_id: Annotated[uuid.UUID, Query(..., description="District UUID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillsInferredResponse:
    """Return inferred skill demand for a trade/district, structured for 1-minute confirm/edit."""
    return await employer_service.get_inferred_skills(
        db=db, trade_id=trade_id, district_id=district_id
    )


@router.post(
    "/validate",
    response_model=EmployerValidateResponse,
    dependencies=[Depends(require_role(UserRole.EMPLOYER.value))],
)
async def validate_skills(
    payload: EmployerValidateRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployerValidateResponse:
    """Record employer confirmed skills and parse any free-text requirements.

    Uses Groq for free-text parsing with a guaranteed deterministic fallback.
    """
    employer_user_id = uuid.UUID(current_user["sub"])
    return await employer_service.save_validation(
        db=db, employer_user_id=employer_user_id, payload=payload
    )


@router.post(
    "/hiring-signal",
    response_model=HiringSignalResponse,
    dependencies=[Depends(require_role(UserRole.EMPLOYER.value))],
)
async def submit_hiring_signal(
    payload: HiringSignalRequest,
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HiringSignalResponse:
    """Submit a structured hiring intention record."""
    employer_user_id = uuid.UUID(current_user["sub"])
    return await employer_service.record_hiring_signal(
        db=db, employer_user_id=employer_user_id, payload=payload
    )


@router.get(
    "/aggregate-readiness",
    response_model=AggregateReadinessResponse,
    dependencies=[Depends(require_role(UserRole.EMPLOYER.value))],
)
async def get_aggregate_readiness(
    trade_id: Annotated[uuid.UUID, Query(..., description="Trade UUID")],
    district_id: Annotated[uuid.UUID, Query(..., description="District UUID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AggregateReadinessResponse:
    """Return strictly aggregated cohort readiness analytics.

    Zero candidate PII or individual trainee identifiers exposed.
    """
    return await employer_service.get_aggregate_readiness(
        db=db, trade_id=trade_id, district_id=district_id
    )


@router.get(
    "/my-validations",
    response_model=list[EmployerValidationListItem],
    dependencies=[Depends(require_role(UserRole.EMPLOYER.value))],
)
async def get_my_validations(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EmployerValidationListItem]:
    """Return past validations submitted by the authenticated employer only."""
    employer_user_id = uuid.UUID(current_user["sub"])
    return await employer_service.list_my_validations(
        db=db, employer_user_id=employer_user_id
    )

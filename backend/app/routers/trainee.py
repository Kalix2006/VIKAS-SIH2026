"""Trainee router for district course catalog, alternatives, skills, chat, and alerts.

All routes are strictly protected by role-based access control (UserRole.TRAINEE).
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.core.limiter import limiter
from app.models.enums import UserRole
from app.schemas.trainee import (
    AlternativesGuideResponse,
    ChatRequest,
    ChatResponse,
    ProficiencyExpectationsResponse,
    TraineeAlertResponse,
    TraineeCourseResponse,
)
from app.services.trainee import trainee_service

router = APIRouter(prefix="/trainee", tags=["trainee"])

TraineeUser = Annotated[dict[str, Any], Depends(require_role(UserRole.TRAINEE.value))]


@router.get("/courses", response_model=list[TraineeCourseResponse])
async def get_courses(
    current_user: TraineeUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    district_id: Annotated[
        uuid.UUID | None,
        Query(description="District ID filter (defaults to trainee district)"),
    ] = None,
) -> list[TraineeCourseResponse]:
    """Return courses in the trainee's district with plain demand labels."""
    target_district_id = district_id or uuid.UUID(current_user["district_id"])
    return await trainee_service.get_district_courses(
        db=db, district_id=target_district_id
    )


@router.get(
    "/courses/{course_id}/alternatives",
    response_model=AlternativesGuideResponse,
)
async def get_course_alternatives(
    course_id: uuid.UUID,
    current_user: TraineeUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AlternativesGuideResponse:
    """Return empathetic guidance and active alternatives if flagged/obsolete."""
    return await trainee_service.get_course_alternatives(db=db, course_id=course_id)


@router.get(
    "/proficiency-expectations",
    response_model=ProficiencyExpectationsResponse,
)
async def get_proficiency_expectations(
    trade_id: uuid.UUID,
    current_user: TraineeUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    district_id: Annotated[
        uuid.UUID | None,
        Query(description="District ID filter (defaults to trainee district)"),
    ] = None,
) -> ProficiencyExpectationsResponse:
    """Return plain-language market skill expectations for a trade."""
    target_district_id = district_id or uuid.UUID(current_user["district_id"])
    return await trainee_service.get_proficiency_expectations(
        db=db, trade_id=trade_id, district_id=target_district_id
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("15/minute")
async def chat_with_assistant(
    request: Request,
    payload: ChatRequest,
    current_user: TraineeUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatResponse:
    """Ask a question to the grounded career assistant."""
    user_id = uuid.UUID(current_user["sub"])
    district_id = uuid.UUID(current_user["district_id"])
    return await trainee_service.handle_chat(
        db=db,
        user_id=user_id,
        district_id=district_id,
        question=payload.question,
    )


@router.get("/alerts", response_model=list[TraineeAlertResponse])
async def get_alerts(
    current_user: TraineeUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TraineeAlertResponse]:
    """Fetch notifications for this trainee."""
    user_id = uuid.UUID(current_user["sub"])
    alerts = await trainee_service.get_trainee_alerts(db=db, user_id=user_id)
    return [TraineeAlertResponse.model_validate(a) for a in alerts]

"""Panel member review and voting endpoints.

Strictly role-gated to 'panel_member'.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_db, require_role
from app.models.district import District  # noqa: F401
from app.models.enums import ReviewDecision, UserRole
from app.models.panel_member import PanelMember
from app.models.panel_review import PanelReview
from app.models.panel_vote import PanelVote
from app.models.skill_gap import SkillGap
from app.models.trade import Trade  # noqa: F401
from app.models.user import User  # noqa: F401
from app.schemas.panel import (
    GovernanceResponse,
    GovernanceToggleRequest,
    PanelReviewResponse,
    PanelVoteResponse,
    ScoreBreakdownResponse,
    VoteRequest,
)
from app.services.panel import panel_service

router = APIRouter(prefix="/panel", tags=["panel"])

REVIEW_LOAD_OPTIONS = (
    selectinload(PanelReview.votes)
    .selectinload(PanelVote.panel_member)
    .selectinload(PanelMember.user),
    selectinload(PanelReview.skill_gap).selectinload(SkillGap.trade),
    selectinload(PanelReview.skill_gap).selectinload(SkillGap.district),
)


def _build_review_response(review: PanelReview) -> PanelReviewResponse:
    """Transform ORM PanelReview and its relationships into PanelReviewResponse."""
    votes_resp: list[PanelVoteResponse] = []
    for v in review.votes:
        p_role = (
            v.panel_member.panel_role
            if v.panel_member and hasattr(v.panel_member, "panel_role")
            else None
        )
        v_name = (
            v.panel_member.user.full_name
            if v.panel_member
            and hasattr(v.panel_member, "user")
            and v.panel_member.user
            else None
        )
        votes_resp.append(
            PanelVoteResponse(
                id=v.id,
                panel_review_id=v.panel_review_id,
                panel_member_id=v.panel_member_id,
                vote=v.vote,
                comment=v.comment,
                voted_at=v.voted_at,
                panel_role=p_role,
                voter_name=v_name,
            )
        )

    sg = review.skill_gap
    trade_name = sg.trade.name if sg and sg.trade else None
    nsqf_code = sg.trade.nsqf_code if sg and sg.trade else None
    district_name = sg.district.name if sg and sg.district else None
    gap_type = sg.gap_type if sg else None
    gap_score = sg.gap_score if sg else None
    nlp_confidence = sg.nlp_confidence if sg else None
    job_posting_volume = sg.job_posting_volume if sg else None

    return PanelReviewResponse(
        id=review.id,
        skill_gap_id=review.skill_gap_id,
        track=review.track,
        required_signoffs=review.required_signoffs,
        decision=review.decision,
        veto_used=review.veto_used,
        decided_at=review.decided_at,
        votes=votes_resp,
        trade_name=trade_name,
        nsqf_code=nsqf_code,
        district_name=district_name,
        gap_type=gap_type,
        gap_score=gap_score,
        nlp_confidence=nlp_confidence,
        job_posting_volume=job_posting_volume,
        academic_veto_enabled=settings.academic_veto_enabled,
    )


@router.get("/queue", response_model=list[PanelReviewResponse])
async def get_review_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        dict[str, Any], Depends(require_role(UserRole.PANEL_MEMBER.value))
    ],
) -> list[PanelReviewResponse]:
    """Retrieve all pending panel reviews waiting for votes."""
    query = (
        select(PanelReview)
        .where(PanelReview.decision == ReviewDecision.PENDING)
        .options(*REVIEW_LOAD_OPTIONS)
        .order_by(PanelReview.track.desc())  # Urgent reviews first
    )
    reviews = list((await db.execute(query)).scalars().all())
    return [_build_review_response(r) for r in reviews]


@router.get("/reviews/{review_id}", response_model=PanelReviewResponse)
async def get_review(
    review_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        dict[str, Any], Depends(require_role(UserRole.PANEL_MEMBER.value))
    ],
) -> PanelReviewResponse:
    """Retrieve details of a specific review, including votes cast so far."""
    query = (
        select(PanelReview)
        .where(PanelReview.id == review_id)
        .options(*REVIEW_LOAD_OPTIONS)
    )
    review = (await db.execute(query)).scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panel review {review_id} not found",
        )
    return _build_review_response(review)


@router.post("/reviews/{review_id}/vote", response_model=PanelReviewResponse)
async def vote_on_review(
    review_id: uuid.UUID,
    payload: VoteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        dict[str, Any], Depends(require_role(UserRole.PANEL_MEMBER.value))
    ],
) -> PanelReviewResponse:
    """Cast an individual panel member vote on a review.

    Validates voter is active panel_member, enforces single vote,
    checks academic expert veto toggle, and evaluates signoff requirements.
    """
    voter_uuid = uuid.UUID(current_user["sub"])
    _vote, _review = await panel_service.cast_vote(
        db=db,
        review_id=review_id,
        voter_user_id=voter_uuid,
        vote=payload.vote,
        comment=payload.comment,
    )

    # Re-fetch review with full relationship graph for complete response
    query = (
        select(PanelReview)
        .where(PanelReview.id == review_id)
        .options(*REVIEW_LOAD_OPTIONS)
    )
    updated_review = (await db.execute(query)).scalars().first()
    if not updated_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panel review {review_id} not found after voting",
        )
    return _build_review_response(updated_review)


@router.get(
    "/reviews/{review_id}/score-breakdown", response_model=ScoreBreakdownResponse
)
async def get_review_score_breakdown(
    review_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        dict[str, Any], Depends(require_role(UserRole.PANEL_MEMBER.value))
    ],
) -> ScoreBreakdownResponse:
    """Retrieve the auditable score breakdown for the skill gap
    linked to this review.
    """
    query = (
        select(PanelReview)
        .where(PanelReview.id == review_id)
        .options(
            selectinload(PanelReview.skill_gap).selectinload(SkillGap.trade),
            selectinload(PanelReview.skill_gap).selectinload(SkillGap.district),
        )
    )
    review = (await db.execute(query)).scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Panel review {review_id} not found",
        )

    skill_gap = review.skill_gap
    if not skill_gap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill gap linked to this review was not found",
        )

    return ScoreBreakdownResponse(
        skill_gap_id=skill_gap.id,
        gap_score=skill_gap.gap_score,
        nlp_confidence=skill_gap.nlp_confidence,
        gap_type=skill_gap.gap_type,
        job_posting_volume=skill_gap.job_posting_volume,
        score_breakdown=skill_gap.score_breakdown,
        trade_name=skill_gap.trade.name if skill_gap.trade else None,
        district_name=skill_gap.district.name if skill_gap.district else None,
    )


@router.get("/governance", response_model=GovernanceResponse)
async def get_governance_settings(
    current_user: Annotated[
        dict[str, Any],
        Depends(require_role(UserRole.PANEL_MEMBER.value, UserRole.PLANNER.value)),
    ],
) -> GovernanceResponse:
    """Retrieve current panel governance policies."""
    return GovernanceResponse(academic_veto_enabled=settings.academic_veto_enabled)


@router.post("/governance/toggle", response_model=GovernanceResponse)
async def toggle_academic_veto(
    payload: GovernanceToggleRequest,
    current_user: Annotated[
        dict[str, Any],
        Depends(require_role(UserRole.PANEL_MEMBER.value, UserRole.PLANNER.value)),
    ],
) -> GovernanceResponse:
    """Toggle academic expert veto governance policy on/off for evaluation & testing."""
    if payload.enabled is not None:
        settings.academic_veto_enabled = payload.enabled
    else:
        settings.academic_veto_enabled = not settings.academic_veto_enabled
    return GovernanceResponse(academic_veto_enabled=settings.academic_veto_enabled)

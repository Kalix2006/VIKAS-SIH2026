"""Panel review service for governance, threshold-based routing, and voting logic.

Enforces:
- Threshold routing: MIN_CONFIDENCE_THRESHOLD (0.75) and HIGH_VOLUME_THRESHOLD (50)
- Urgent track (2 signoffs) vs Standard track (4 signoffs)
- Academic expert veto toggle (PANEL_GOVERNANCE.academic_veto_enabled)
- Vote deduplication per member per review
- Split vote non-resolution handling
- Automatic transition to approved with alert generation
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.enums import (
    GapStatus,
    PanelRoleType,
    ReviewDecision,
    ReviewTrack,
    VoteChoice,
)
from app.models.panel_member import PanelMember
from app.models.panel_review import PanelReview
from app.models.panel_vote import PanelVote
from app.models.skill_gap import SkillGap
from app.services.alert import alert_service
from app.services.audit import record_audit_event

logger = logging.getLogger("vikas.panel")

# Documented named threshold constants (not magic numbers)
MIN_CONFIDENCE_THRESHOLD: float = 0.75
HIGH_VOLUME_THRESHOLD: int = 50


class PanelService:
    """Manages skill gap routing and panel member review voting."""

    async def route_skill_gap(
        self, db: AsyncSession, skill_gap: SkillGap
    ) -> PanelReview:
        """Route a detected skill gap into urgent or standard review track.

        Criteria:
        - If nlp_confidence >= MIN_CONFIDENCE_THRESHOLD AND
             job_posting_volume >= HIGH_VOLUME_THRESHOLD:
          -> status = URGENT_ESCALATION, track = URGENT, required_signoffs = 2
        - Otherwise:
          -> status = PANEL_QUEUE, track = STANDARD, required_signoffs = 4
        """
        # Check if review already exists
        review_query = select(PanelReview).where(
            PanelReview.skill_gap_id == skill_gap.id
        )
        existing_review = (await db.execute(review_query)).scalars().first()
        if existing_review:
            return existing_review

        is_urgent = (
            skill_gap.nlp_confidence >= MIN_CONFIDENCE_THRESHOLD
            and skill_gap.job_posting_volume >= HIGH_VOLUME_THRESHOLD
        )

        if is_urgent:
            skill_gap.status = GapStatus.URGENT_ESCALATION
            review = PanelReview(
                skill_gap_id=skill_gap.id,
                track=ReviewTrack.URGENT,
                required_signoffs=2,
                decision=ReviewDecision.PENDING,
                veto_used=False,
            )
        else:
            skill_gap.status = GapStatus.PANEL_QUEUE
            review = PanelReview(
                skill_gap_id=skill_gap.id,
                track=ReviewTrack.STANDARD,
                required_signoffs=4,
                decision=ReviewDecision.PENDING,
                veto_used=False,
            )

        db.add(review)
        await db.commit()
        await db.refresh(review)
        logger.info(
            "Routed skill gap %s to %s track (required signoffs: %d)",
            skill_gap.id,
            review.track.value,
            review.required_signoffs,
        )
        return review

    async def route_all_detected_gaps(self, db: AsyncSession) -> list[PanelReview]:
        """Route all skill gaps currently in 'detected' status."""
        query = select(SkillGap).where(SkillGap.status == GapStatus.DETECTED)
        gaps = list((await db.execute(query)).scalars().all())

        reviews: list[PanelReview] = []
        for gap in gaps:
            rev = await self.route_skill_gap(db, gap)
            reviews.append(rev)

        return reviews

    async def cast_vote(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        voter_user_id: uuid.UUID,
        vote: VoteChoice,
        comment: str | None = None,
    ) -> tuple[PanelVote, PanelReview]:
        """Record an individual panel member's vote and evaluate review outcome."""
        # 1. Validate voter is an active panel member
        member_query = select(PanelMember).where(
            PanelMember.user_id == voter_user_id,
            PanelMember.active.is_(True),
        )
        panel_member = (await db.execute(member_query)).scalars().first()
        if not panel_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not an active panel member",
            )

        # 2. Fetch review and linked skill gap
        review_query = (
            select(PanelReview)
            .where(PanelReview.id == review_id)
            .options(
                selectinload(PanelReview.votes), selectinload(PanelReview.skill_gap)
            )
        )
        review = (await db.execute(review_query)).scalars().first()
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Panel review {review_id} not found",
            )

        if review.decision != ReviewDecision.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Panel review has already been finalized as "
                    f"{review.decision.value}"
                ),
            )

        # 3. Check member hasn't already voted on this review
        for existing_vote in review.votes:
            if existing_vote.panel_member_id == panel_member.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member has already cast a vote on this review",
                )

        # 4. Record new vote
        new_vote = PanelVote(
            panel_review_id=review.id,
            panel_member_id=panel_member.user_id,
            vote=vote,
            comment=comment,
        )
        db.add(new_vote)
        await db.flush()

        # Update votes list in memory
        review.votes.append(new_vote)
        now_dt = datetime.now(UTC)

        # Record immutable audit log for the cast vote
        await record_audit_event(
            db=db,
            event_type="PANEL_VOTE",
            actor_id=panel_member.user_id,
            resource_type="panel_review",
            resource_id=review.id,
            details={
                "vote": vote.value,
                "panel_role": panel_member.panel_role.value,
                "comment": comment,
            },
        )

        # 5. Governance Check: Academic Expert Veto
        # If enabled and academic expert rejects, immediately reject (veto_used=True)
        if (
            settings.academic_veto_enabled
            and panel_member.panel_role == PanelRoleType.ACADEMIC_EXPERT
            and vote == VoteChoice.REJECT
        ):
            review.veto_used = True
            review.decision = ReviewDecision.REJECTED
            review.decided_at = now_dt
            if review.skill_gap:
                review.skill_gap.status = GapStatus.REJECTED
                review.skill_gap.resolved_at = now_dt
            logger.info("Academic expert veto exercised on review %s", review.id)
            await record_audit_event(
                db=db,
                event_type="PANEL_DECISION",
                actor_id=panel_member.user_id,
                resource_type="panel_review",
                resource_id=review.id,
                details={
                    "decision": ReviewDecision.REJECTED.value,
                    "veto_used": True,
                    "reason": "Academic expert veto exercised",
                },
            )
            await db.commit()
            return new_vote, review

        # 6. Vote Counting & Outcome Evaluation
        approve_count = sum(1 for v in review.votes if v.vote == VoteChoice.APPROVE)
        reject_count = sum(1 for v in review.votes if v.vote == VoteChoice.REJECT)
        total_votes = len(review.votes)

        if review.track == ReviewTrack.URGENT:
            # Urgent Track: 2 approve signoffs needed
            if approve_count >= review.required_signoffs:
                review.decision = ReviewDecision.APPROVED
                review.decided_at = now_dt
                if review.skill_gap:
                    review.skill_gap.status = GapStatus.APPROVED
                    review.skill_gap.resolved_at = now_dt
                    await alert_service.create_gap_approved_alerts(db, review.skill_gap)
                await record_audit_event(
                    db=db,
                    event_type="PANEL_DECISION",
                    actor_id=panel_member.user_id,
                    resource_type="panel_review",
                    resource_id=review.id,
                    details={
                        "decision": ReviewDecision.APPROVED.value,
                        "track": "urgent",
                        "approvals": approve_count,
                    },
                )
            elif reject_count >= 3:
                # Impossible to reach 2 approvals out of 4 total panel members
                review.decision = ReviewDecision.REJECTED
                review.decided_at = now_dt
                if review.skill_gap:
                    review.skill_gap.status = GapStatus.REJECTED
                    review.skill_gap.resolved_at = now_dt
                await record_audit_event(
                    db=db,
                    event_type="PANEL_DECISION",
                    actor_id=panel_member.user_id,
                    resource_type="panel_review",
                    resource_id=review.id,
                    details={
                        "decision": ReviewDecision.REJECTED.value,
                        "track": "urgent",
                        "rejections": reject_count,
                    },
                )
            # Otherwise stays PENDING

        elif review.track == ReviewTrack.STANDARD:
            # Standard Track: All 4 members must vote
            if total_votes == 4 and approve_count >= review.required_signoffs:
                review.decision = ReviewDecision.APPROVED
                review.decided_at = now_dt
                if review.skill_gap:
                    review.skill_gap.status = GapStatus.APPROVED
                    review.skill_gap.resolved_at = now_dt
                    await alert_service.create_gap_approved_alerts(db, review.skill_gap)
                await record_audit_event(
                    db=db,
                    event_type="PANEL_DECISION",
                    actor_id=panel_member.user_id,
                    resource_type="panel_review",
                    resource_id=review.id,
                    details={
                        "decision": ReviewDecision.APPROVED.value,
                        "track": "standard",
                        "approvals": approve_count,
                    },
                )
            elif total_votes == 4:
                review.decision = ReviewDecision.REJECTED
                review.decided_at = now_dt
                if review.skill_gap:
                    review.skill_gap.status = GapStatus.REJECTED
                    review.skill_gap.resolved_at = now_dt
                await record_audit_event(
                    db=db,
                    event_type="PANEL_DECISION",
                    actor_id=panel_member.user_id,
                    resource_type="panel_review",
                    resource_id=review.id,
                    details={
                        "decision": ReviewDecision.REJECTED.value,
                        "track": "standard",
                        "total_votes": total_votes,
                    },
                )
            # If total_votes < 4: stays PENDING, even if split

        await db.commit()
        return new_vote, review


# Singleton instance
panel_service = PanelService()

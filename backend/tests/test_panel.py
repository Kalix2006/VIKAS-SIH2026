"""Tests for panel review service, threshold-based routing,
voting logic, and governance.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.district import District
from app.models.enums import (
    GapStatus,
    GapType,
    PanelRoleType,
    ReviewDecision,
    ReviewTrack,
    UserRole,
    VoteChoice,
)
from app.models.panel_member import PanelMember
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.user import User
from app.services.panel import (
    panel_service,
)


async def _create_test_entities(
    db: AsyncSession,
) -> tuple[District, Trade, list[User]]:
    """Helper to create district, trade, and 4 panel members."""
    uid = uuid.uuid4().hex[:6]
    district = District(
        name=f"District_{uid}",
        state="State",
        centroid_lat=18.5,
        centroid_lng=73.8,
    )
    trade = Trade(name=f"Trade_{uid}", nsqf_code=f"TRD-{uid}")
    db.add(district)
    db.add(trade)
    await db.flush()

    members: list[User] = []
    roles = [
        PanelRoleType.ACADEMIC_EXPERT,
        PanelRoleType.INDUSTRY_PROFESSIONAL,
        PanelRoleType.PROGRAM_LEAD,
        PanelRoleType.INDUSTRY_PROFESSIONAL,
    ]

    for i, p_role in enumerate(roles):
        user = User(
            email=f"panel_{uid}_{i}@vikas.gov.in",
            password_hash=hash_password("testpass123"),
            role=UserRole.PANEL_MEMBER,
            full_name=f"Panel Member {i}",
            district_id=district.id,
        )
        db.add(user)
        await db.flush()

        pm = PanelMember(
            user_id=user.id,
            panel_role=p_role,
            active=True,
        )
        db.add(pm)
        members.append(user)

    await db.commit()
    return district, trade, members


@pytest.mark.asyncio
async def test_threshold_based_routing(db_session: AsyncSession) -> None:
    """Threshold routing sends high-conf + high-vol to urgent, others to standard."""
    district, trade, _ = await _create_test_entities(db_session)

    # 1. High confidence + High volume -> Urgent track
    urgent_gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.88,  # >= MIN_CONFIDENCE_THRESHOLD (0.75)
        job_posting_volume=65,  # >= HIGH_VOLUME_THRESHOLD (50)
        gap_score=55.0,
        score_breakdown={"test": "data"},
        status=GapStatus.DETECTED,
    )
    db_session.add(urgent_gap)
    await db_session.commit()

    urgent_review = await panel_service.route_skill_gap(db_session, urgent_gap)
    assert urgent_gap.status == GapStatus.URGENT_ESCALATION
    assert urgent_review.track == ReviewTrack.URGENT
    assert urgent_review.required_signoffs == 2
    assert urgent_review.decision == ReviewDecision.PENDING

    # 2. Lower volume -> Standard track
    std_gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.UNDERSUPPLY,
        nlp_confidence=0.85,
        job_posting_volume=25,  # < 50
        gap_score=30.0,
        score_breakdown={"test": "data"},
        status=GapStatus.DETECTED,
    )
    db_session.add(std_gap)
    await db_session.commit()

    std_review = await panel_service.route_skill_gap(db_session, std_gap)
    assert std_gap.status == GapStatus.PANEL_QUEUE
    assert std_review.track == ReviewTrack.STANDARD
    assert std_review.required_signoffs == 4
    assert std_review.decision == ReviewDecision.PENDING


@pytest.mark.asyncio
async def test_urgent_track_two_of_four_approval(db_session: AsyncSession) -> None:
    """Urgent track resolves to APPROVED once 2 'approve' votes are reached."""
    district, trade, members = await _create_test_entities(db_session)

    gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.85,
        job_posting_volume=60,
        gap_score=50.0,
        score_breakdown={"test": "data"},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()

    review = await panel_service.route_skill_gap(db_session, gap)

    # First approve vote: should stay pending (1 of 2 signoffs)
    _, rev_after_1 = await panel_service.cast_vote(
        db=db_session,
        review_id=review.id,
        voter_user_id=members[0].id,
        vote=VoteChoice.APPROVE,
        comment="First signoff",
    )
    assert rev_after_1.decision == ReviewDecision.PENDING
    assert gap.status == GapStatus.URGENT_ESCALATION

    # Second approve vote: reaches 2 signoffs -> approved!
    _, rev_after_2 = await panel_service.cast_vote(
        db=db_session,
        review_id=review.id,
        voter_user_id=members[1].id,
        vote=VoteChoice.APPROVE,
        comment="Second signoff - urgent approved",
    )
    assert rev_after_2.decision == ReviewDecision.APPROVED
    assert rev_after_2.decided_at is not None
    assert gap.status == GapStatus.APPROVED


@pytest.mark.asyncio
async def test_standard_track_requires_four_approvals(db_session: AsyncSession) -> None:
    """Standard track stays pending until all 4 members vote; requires 4 approvals."""
    district, trade, members = await _create_test_entities(db_session)

    gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.EMERGING_SKILL,
        nlp_confidence=0.80,
        job_posting_volume=20,
        gap_score=35.0,
        score_breakdown={"test": "data"},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()

    review = await panel_service.route_skill_gap(db_session, gap)
    assert review.track == ReviewTrack.STANDARD
    assert review.required_signoffs == 4

    # Cast 3 approve votes -> must still be pending
    for i in range(3):
        await panel_service.cast_vote(
            db=db_session,
            review_id=review.id,
            voter_user_id=members[i].id,
            vote=VoteChoice.APPROVE,
        )
        await db_session.refresh(review)
        assert review.decision == ReviewDecision.PENDING

    # 4th vote also approves -> resolves to approved
    await panel_service.cast_vote(
        db=db_session,
        review_id=review.id,
        voter_user_id=members[3].id,
        vote=VoteChoice.APPROVE,
    )
    await db_session.refresh(review)
    assert review.decision == ReviewDecision.APPROVED
    assert gap.status == GapStatus.APPROVED


@pytest.mark.asyncio
async def test_academic_veto_off_vs_on(db_session: AsyncSession) -> None:
    """When academic_veto_enabled is False, reject vote doesn't veto.
    When True, it immediately vetoes and rejects.
    """
    district, trade, members = await _create_test_entities(db_session)
    academic_member = members[0]  # ACADEMIC_EXPERT

    # Part A: Veto toggle OFF (default)
    settings.academic_veto_enabled = False

    gap1 = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.80,
        job_posting_volume=20,
        gap_score=30.0,
        score_breakdown={},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap1)
    await db_session.commit()
    rev1 = await panel_service.route_skill_gap(db_session, gap1)

    _, rev1_voted = await panel_service.cast_vote(
        db=db_session,
        review_id=rev1.id,
        voter_user_id=academic_member.id,
        vote=VoteChoice.REJECT,
    )
    assert rev1_voted.veto_used is False
    assert (
        rev1_voted.decision == ReviewDecision.PENDING
    )  # Standard track: only 1 vote cast

    # Part B: Veto toggle ON
    settings.academic_veto_enabled = True
    try:
        gap2 = SkillGap(
            district_id=district.id,
            trade_id=trade.id,
            gap_type=GapType.CURRICULUM_DRIFT,
            nlp_confidence=0.80,
            job_posting_volume=20,
            gap_score=30.0,
            score_breakdown={},
            status=GapStatus.DETECTED,
        )
        db_session.add(gap2)
        await db_session.commit()
        rev2 = await panel_service.route_skill_gap(db_session, gap2)

        _, rev2_voted = await panel_service.cast_vote(
            db=db_session,
            review_id=rev2.id,
            voter_user_id=academic_member.id,
            vote=VoteChoice.REJECT,
            comment="Academic expert veto exercised",
        )
        assert rev2_voted.veto_used is True
        assert rev2_voted.decision == ReviewDecision.REJECTED
        assert gap2.status == GapStatus.REJECTED
    finally:
        settings.academic_veto_enabled = False  # Reset


@pytest.mark.asyncio
async def test_split_vote_stays_pending(db_session: AsyncSession) -> None:
    """Split votes stay pending and do not silently resolve early."""
    district, trade, members = await _create_test_entities(db_session)

    gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.UNDERSUPPLY,
        nlp_confidence=0.80,
        job_posting_volume=20,
        gap_score=30.0,
        score_breakdown={},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()
    review = await panel_service.route_skill_gap(db_session, gap)

    # 1 approve, 1 reject on standard track (2 votes remaining)
    await panel_service.cast_vote(
        db=db_session,
        review_id=review.id,
        voter_user_id=members[1].id,
        vote=VoteChoice.APPROVE,
    )
    await panel_service.cast_vote(
        db=db_session,
        review_id=review.id,
        voter_user_id=members[2].id,
        vote=VoteChoice.REJECT,
    )
    await db_session.refresh(review)
    assert review.decision == ReviewDecision.PENDING
    assert gap.status == GapStatus.PANEL_QUEUE


@pytest.mark.asyncio
async def test_panel_api_endpoints_role_gated(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Panel API routes allow panel_member but block unauthorized roles."""
    district, trade, members = await _create_test_entities(db_session)
    panel_user = members[0]

    # Trainee user (forbidden)
    trainee_user = User(
        email=f"trainee_{uuid.uuid4().hex[:6]}@vikas.gov.in",
        password_hash=hash_password("pass123"),
        role=UserRole.TRAINEE,
        full_name="Trainee User",
        district_id=district.id,
    )
    db_session.add(trainee_user)

    gap = SkillGap(
        district_id=district.id,
        trade_id=trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.82,
        job_posting_volume=55,
        gap_score=50.0,
        score_breakdown={"metric": "value"},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()
    review = await panel_service.route_skill_gap(db_session, gap)

    trainee_token = create_access_token(
        subject=str(trainee_user.id),
        role=UserRole.TRAINEE.value,
        district_id=str(district.id),
    )
    panel_token = create_access_token(
        subject=str(panel_user.id),
        role=UserRole.PANEL_MEMBER.value,
        district_id=str(district.id),
    )

    # 1. Trainee accessing /panel/queue -> 403 Forbidden
    resp_trainee = await client.get(
        "/panel/queue",
        headers={"Authorization": f"Bearer {trainee_token}"},
    )
    assert resp_trainee.status_code == 403

    # 2. Panel member accessing /panel/queue -> 200 OK
    resp_panel = await client.get(
        "/panel/queue",
        headers={"Authorization": f"Bearer {panel_token}"},
    )
    assert resp_panel.status_code == 200
    queue = resp_panel.json()
    assert len(queue) >= 1

    # 3. Panel member getting score-breakdown -> 200 OK
    resp_breakdown = await client.get(
        f"/panel/reviews/{review.id}/score-breakdown",
        headers={"Authorization": f"Bearer {panel_token}"},
    )
    assert resp_breakdown.status_code == 200
    data = resp_breakdown.json()
    assert data["skill_gap_id"] == str(gap.id)
    assert data["gap_score"] == 50.0

    # 4. Panel member voting via API -> 200 OK
    resp_vote = await client.post(
        f"/panel/reviews/{review.id}/vote",
        headers={"Authorization": f"Bearer {panel_token}"},
        json={"vote": "approve", "comment": "Approved via API"},
    )
    assert resp_vote.status_code == 200

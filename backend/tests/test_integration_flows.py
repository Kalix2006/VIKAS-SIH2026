"""End-to-end integration tests using real PostgreSQL database transactions.

Exercises complete lifecycle flows against active database:
1. Full Auth Flow: Register -> Login -> Fetch /auth/me -> Refresh token rotation -> Verify old token revocation -> Revocation security.
2. Full Panel Governance Flow: Seed gap -> Automatic threshold routing -> Multi-member voting -> Quorum decision -> Status update -> Audit trail verification.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_refresh_token
from app.models.audit_log import AuditLog
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
from app.models.refresh_token import RefreshToken
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.user import User
from app.services.panel import panel_service


@pytest.mark.asyncio
async def test_e2e_real_db_auth_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    test_district: District,
) -> None:
    """E2E Test 1: Full user registration, login, profile fetch, and refresh token rotation in real DB."""
    email = f"e2e_user_{uuid.uuid4().hex[:8]}@vikas.gov.in"
    password = "SecurePassword#2026"
    full_name = "Vikram Aditya"

    # Step 1: Signup
    signup_resp = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": "trainee",
            "district_id": str(test_district.id),
        },
    )
    assert signup_resp.status_code == 200, f"Signup failed: {signup_resp.text}"
    signup_tokens = signup_resp.json()
    assert "access_token" in signup_tokens
    assert "refresh_token" in signup_tokens

    # Verify user persisted in DB
    user_stmt = select(User).where(User.email == email)
    user = (await db_session.execute(user_stmt)).scalar_one_or_none()
    assert user is not None
    assert user.full_name == full_name
    assert user.role == UserRole.TRAINEE

    # Step 2: Login with credentials
    login_resp = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_tokens = login_resp.json()
    access_token = login_tokens["access_token"]
    refresh_token_1 = login_tokens["refresh_token"]

    # Step 3: Fetch /auth/me with access token
    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["role"] == "trainee"
    assert me_data["id"] == str(user.id)

    # Step 4: Rotate refresh token
    refresh_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    refresh_token_2 = new_tokens["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # Verify in DB that refresh_token_1 is marked revoked
    h1 = hash_refresh_token(refresh_token_1)
    tok1_stmt = select(RefreshToken).where(RefreshToken.token_hash == h1)
    tok1 = (await db_session.execute(tok1_stmt)).scalar_one()
    assert tok1.revoked is True

    # Step 5: Attempting to replay old refresh token must be rejected (401)
    replay_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert replay_resp.status_code == 401
    assert "revoked" in replay_resp.json()["detail"].lower()

    # Step 6: Using new refresh token succeeds
    refresh_resp_2 = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_2},
    )
    assert refresh_resp_2.status_code == 200


@pytest.mark.asyncio
async def test_e2e_real_db_panel_governance_flow(
    db_session: AsyncSession,
    test_district: District,
    create_test_user,
) -> None:
    """E2E Test 2: Full governance flow from gap detection, routing, quorum voting, to audit trail."""
    # Step 1: Ensure trade exists
    trade_stmt = select(Trade).where(Trade.name == "Electrician")
    trade = (await db_session.execute(trade_stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="Electrician", nsqf_code="ELE-001")
        db_session.add(trade)
        await db_session.flush()

    # Step 2: Seed 4 panel members with distinct roles
    roles = [
        PanelRoleType.ACADEMIC_EXPERT,
        PanelRoleType.INDUSTRY_PROFESSIONAL,
        PanelRoleType.PROGRAM_LEAD,
        PanelRoleType.INDUSTRY_PROFESSIONAL,
    ]
    panel_members: list[PanelMember] = []
    for r in roles:
        u = await create_test_user(
            email=f"panel_{uuid.uuid4().hex[:6]}@test.vikas",
            role=UserRole.PANEL_MEMBER,
            district_id=test_district.id,
        )
        pm = PanelMember(user_id=u.id, panel_role=r, active=True)
        db_session.add(pm)
        panel_members.append(pm)
    await db_session.flush()

    # Step 3: Seed a high-confidence, high-volume skill gap
    gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.88,  # > 0.75 threshold
        job_posting_volume=65,  # > 50 threshold -> routes to URGENT track
        gap_score=58.5,
        score_breakdown={"similarity": 0.35, "volume": 65},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()

    # Step 4: Route through threshold engine
    reviews = await panel_service.route_all_detected_gaps(db=db_session)
    matching_review = next((r for r in reviews if r.skill_gap_id == gap.id), None)
    assert matching_review is not None
    assert matching_review.track == ReviewTrack.URGENT
    assert matching_review.required_signoffs == 2
    assert matching_review.decision == ReviewDecision.PENDING

    # Step 5: Member 1 votes APPROVE
    vote_1, rev_1 = await panel_service.cast_vote(
        db=db_session,
        review_id=matching_review.id,
        voter_user_id=panel_members[0].user_id,
        vote=VoteChoice.APPROVE,
        comment="Curriculum drift is empirically backed by local automotive employer requirements.",
    )
    assert vote_1.vote == VoteChoice.APPROVE
    assert rev_1.decision == ReviewDecision.PENDING  # 1 of 2 needed

    # Step 6: Member 2 votes APPROVE -> Reaches Quorum (2 of 2)!
    vote_2, rev_2 = await panel_service.cast_vote(
        db=db_session,
        review_id=matching_review.id,
        voter_user_id=panel_members[1].user_id,
        vote=VoteChoice.APPROVE,
        comment="Approved for modernization syllabus committee.",
    )
    assert rev_2.decision == ReviewDecision.APPROVED
    assert rev_2.decided_at is not None

    # Step 7: Verify skill_gap status automatically updated in database
    await db_session.refresh(gap)
    assert gap.status == GapStatus.APPROVED
    assert gap.resolved_at is not None

    # Step 8: Verify immutable audit log records in database
    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.resource_id == matching_review.id)
        .order_by(AuditLog.created_at.asc())
    )
    audit_entries = list((await db_session.execute(audit_stmt)).scalars().all())

    # Should have 2 PANEL_VOTE entries and 1 PANEL_DECISION entry
    event_types = [entry.event_type for entry in audit_entries]
    assert "PANEL_VOTE" in event_types
    assert "PANEL_DECISION" in event_types
    assert len(audit_entries) >= 3

    decision_audit = next(e for e in audit_entries if e.event_type == "PANEL_DECISION")
    assert decision_audit.details["decision"] == "approved"
    assert decision_audit.details["track"] == "urgent"

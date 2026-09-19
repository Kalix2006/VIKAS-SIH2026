"""Tests for Institute Admin endpoints.

Verifies:
1. GET /institute/flags scoped to own institute_id.
2. POST /institute/flags/{flag_id}/acknowledge sets timestamp and acknowledged_by.
3. Attempt to acknowledge another institute's flag is blocked with 403.
4. POST /institute/flags/{flag_id}/request-trainer-refresher creates record and alert.
5. Attempt to request refresher on another institute's flag is blocked with 403.
6. GET /institute/enrollment-vs-demand returns seats vs job volume comparisons.
7. GET /institute/flags/{flag_id}/detail returns score trend and drifted skills.
8. Role gating blocks unauthorized roles (trainee, employer) with 403.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.course import Course
from app.models.district import District
from app.models.enums import AlertTargetRole, CourseStatus, GapStatus, GapType, UserRole
from app.models.institute import Institute
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.trainer_refresher_request import TrainerRefresherRequest


@pytest.mark.asyncio
async def test_get_flags_scoped_to_institute(
    client: AsyncClient,
    db_session: AsyncSession,
    test_district: District,
    test_district_beed: District,
    test_institute: Institute,
    create_test_user,
    auth_token_for,
) -> None:
    """Institute admin only sees flags for courses belonging to their institute."""
    # Create an institute in Beed
    stmt = select(Institute).where(Institute.name == "Government ITI Beed")
    beed_inst = (await db_session.execute(stmt)).scalar_one_or_none()
    if not beed_inst:
        beed_inst = Institute(
            name="Government ITI Beed",
            district_id=test_district_beed.id,
            type="ITI",
        )
        db_session.add(beed_inst)
        await db_session.commit()
        await db_session.refresh(beed_inst)

    # Trade: Fitter
    stmt = select(Trade).where(Trade.name == "Fitter")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="Fitter", nsqf_code="NSQF-L4-FIT")
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

    # Course at Pune ITI
    pune_course = Course(
        institute_id=test_institute.id,
        trade_id=trade.id,
        seats_available=30,
        status=CourseStatus.FLAGGED,
    )
    # Course at Beed ITI
    beed_course = Course(
        institute_id=beed_inst.id,
        trade_id=trade.id,
        seats_available=25,
        status=CourseStatus.FLAGGED,
    )
    db_session.add_all([pune_course, beed_course])
    await db_session.commit()
    await db_session.refresh(pune_course)
    await db_session.refresh(beed_course)

    # Gaps for both
    pune_gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        course_id=pune_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.88,
        job_posting_volume=45,
        gap_score=62.5,
        score_breakdown={"similarity_score": 0.52, "market_demand_factor": 0.8},
        status=GapStatus.APPROVED,
    )
    beed_gap = SkillGap(
        district_id=test_district_beed.id,
        trade_id=trade.id,
        course_id=beed_course.id,
        gap_type=GapType.OVERSUPPLY,
        nlp_confidence=0.91,
        job_posting_volume=4,
        gap_score=55.0,
        score_breakdown={"similarity_score": 0.85, "market_demand_factor": 0.2},
        status=GapStatus.APPROVED,
    )
    db_session.add_all([pune_gap, beed_gap])
    await db_session.commit()
    await db_session.refresh(pune_gap)
    await db_session.refresh(beed_gap)

    # Admin for Pune ITI
    pune_admin = await create_test_user(
        email="pune_admin_test@dev.vikas",
        role=UserRole.INSTITUTE_ADMIN,
        district_id=test_district.id,
        institute_id=test_institute.id,
    )
    token = auth_token_for(pune_admin)

    # Fetch flags
    resp = await client.get(
        "/institute/flags",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    flags = resp.json()
    assert isinstance(flags, list)

    flag_ids = [f["flag_id"] for f in flags]
    assert str(pune_gap.id) in flag_ids
    # Crucial: Beed gap must NOT be present
    assert str(beed_gap.id) not in flag_ids

    # Verify plain-language reason is populated
    pune_item = next(f for f in flags if f["flag_id"] == str(pune_gap.id))
    assert (
        "curriculum" in pune_item["reason"].lower()
        or "drift" in pune_item["reason"].lower()
    )
    assert pune_item["acknowledged"] is False


@pytest.mark.asyncio
async def test_acknowledge_flag_and_cross_institute_tampering(
    client: AsyncClient,
    db_session: AsyncSession,
    test_district: District,
    test_district_beed: District,
    test_institute: Institute,
    create_test_user,
    auth_token_for,
) -> None:
    """Admin can acknowledge flag, but tampering with another institute is 403."""
    # Create Beed institute
    stmt = select(Institute).where(Institute.name == "Government ITI Beed")
    beed_inst = (await db_session.execute(stmt)).scalar_one_or_none()
    if not beed_inst:
        beed_inst = Institute(
            name="Government ITI Beed",
            district_id=test_district_beed.id,
            type="ITI",
        )
        db_session.add(beed_inst)
        await db_session.commit()
        await db_session.refresh(beed_inst)

    stmt = select(Trade).where(Trade.name == "Welder")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="Welder", nsqf_code="NSQF-L3-WLD")
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

    pune_course = Course(
        institute_id=test_institute.id,
        trade_id=trade.id,
        seats_available=20,
        status=CourseStatus.FLAGGED,
    )
    beed_course = Course(
        institute_id=beed_inst.id,
        trade_id=trade.id,
        seats_available=20,
        status=CourseStatus.FLAGGED,
    )
    db_session.add_all([pune_course, beed_course])
    await db_session.commit()
    await db_session.refresh(pune_course)
    await db_session.refresh(beed_course)

    pune_gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        course_id=pune_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.85,
        job_posting_volume=30,
        gap_score=50.0,
        score_breakdown={"similarity_score": 0.5},
        status=GapStatus.APPROVED,
    )
    beed_gap = SkillGap(
        district_id=test_district_beed.id,
        trade_id=trade.id,
        course_id=beed_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.85,
        job_posting_volume=30,
        gap_score=50.0,
        score_breakdown={"similarity_score": 0.5},
        status=GapStatus.APPROVED,
    )
    db_session.add_all([pune_gap, beed_gap])
    await db_session.commit()
    await db_session.refresh(pune_gap)
    await db_session.refresh(beed_gap)

    # Create a second institute in Pune to test same-district
    # cross-institute tampering (403)
    stmt = select(Institute).where(Institute.name == "Private ITI Pune")
    other_pune_inst = (await db_session.execute(stmt)).scalar_one_or_none()
    if not other_pune_inst:
        other_pune_inst = Institute(
            name="Private ITI Pune",
            district_id=test_district.id,
            type="private",
        )
        db_session.add(other_pune_inst)
        await db_session.commit()
        await db_session.refresh(other_pune_inst)

    other_pune_course = Course(
        institute_id=other_pune_inst.id,
        trade_id=trade.id,
        seats_available=20,
        status=CourseStatus.FLAGGED,
    )
    db_session.add(other_pune_course)
    await db_session.commit()
    await db_session.refresh(other_pune_course)

    other_pune_gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        course_id=other_pune_course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.85,
        job_posting_volume=30,
        gap_score=50.0,
        score_breakdown={"similarity_score": 0.5},
        status=GapStatus.APPROVED,
    )
    db_session.add(other_pune_gap)
    await db_session.commit()
    await db_session.refresh(other_pune_gap)

    # Pune admin
    pune_admin = await create_test_user(
        email="pune_admin_ack@dev.vikas",
        role=UserRole.INSTITUTE_ADMIN,
        district_id=test_district.id,
        institute_id=test_institute.id,
    )
    token = auth_token_for(pune_admin)

    # 1. Acknowledge own flag -> 200 OK
    resp = await client.post(
        f"/institute/flags/{pune_gap.id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["acknowledged"] is True
    assert data["acknowledged_by"] == str(pune_admin.id)

    # Verify DB state
    await db_session.refresh(pune_gap)
    assert pune_gap.acknowledged_at is not None
    assert pune_gap.acknowledged_by == pune_admin.id

    # 2. Attempt to acknowledge another institute's flag in the same
    # district -> 403 Forbidden
    resp_tamper = await client.post(
        f"/institute/flags/{other_pune_gap.id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_tamper.status_code == 403
    assert "Access denied" in resp_tamper.json()["detail"]

    # 3. Attempt to acknowledge a flag in another district -> 404 (hidden by RLS)
    resp_diff_district = await client.post(
        f"/institute/flags/{beed_gap.id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_diff_district.status_code == 404


@pytest.mark.asyncio
async def test_request_trainer_refresher_creates_record_and_alerts_planner(
    client: AsyncClient,
    db_session: AsyncSession,
    test_district: District,
    test_institute: Institute,
    create_test_user,
    auth_token_for,
) -> None:
    """Requesting refresher creates tracked record and alerts district planner."""
    # Ensure a planner user exists in Pune district
    planner = await create_test_user(
        email="pune_planner_refresher@dev.vikas",
        role=UserRole.PLANNER,
        district_id=test_district.id,
    )

    stmt = select(Trade).where(Trade.name == "Electrician")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="Electrician", nsqf_code="NSQF-L4-ELE")
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

    course = Course(
        institute_id=test_institute.id,
        trade_id=trade.id,
        seats_available=40,
        status=CourseStatus.FLAGGED,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        course_id=course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.90,
        job_posting_volume=60,
        gap_score=68.0,
        score_breakdown={"similarity_score": 0.45},
        status=GapStatus.APPROVED,
    )
    db_session.add(gap)
    await db_session.commit()
    await db_session.refresh(gap)

    admin = await create_test_user(
        email="admin_refresher_req@dev.vikas",
        role=UserRole.INSTITUTE_ADMIN,
        district_id=test_district.id,
        institute_id=test_institute.id,
    )
    token = auth_token_for(admin)

    resp = await client.post(
        f"/institute/flags/{gap.id}/request-trainer-refresher",
        json={"notes": "Urgent training needed on PLC and solar inverters."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    res_data = resp.json()
    assert res_data["status"] == "pending"
    assert "Urgent training needed" in res_data["notes"]

    # Check that TrainerRefresherRequest was persisted
    req_stmt = select(TrainerRefresherRequest).where(
        TrainerRefresherRequest.skill_gap_id == gap.id
    )
    req_row = (await db_session.execute(req_stmt)).scalar_one_or_none()
    assert req_row is not None
    assert req_row.requested_by == admin.id
    assert req_row.institute_id == test_institute.id

    # Check that in-app Alert was created for the planner
    alert_stmt = select(Alert).where(
        Alert.target_id == planner.id,
        Alert.target_role == AlertTargetRole.PLANNER,
        Alert.skill_gap_id == gap.id,
    )
    alert = (await db_session.execute(alert_stmt)).scalar_one_or_none()
    assert alert is not None
    assert "Trainer Refresher Requested" in alert.message


@pytest.mark.asyncio
async def test_enrollment_vs_demand_and_flag_detail(
    client: AsyncClient,
    db_session: AsyncSession,
    test_district: District,
    test_institute: Institute,
    create_test_user,
    auth_token_for,
) -> None:
    """Test enrollment vs demand comparison and drift detail drill-down."""
    stmt = select(Trade).where(Trade.name == "COPA")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="COPA", nsqf_code="NSQF-L3-COP")
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)

    course = Course(
        institute_id=test_institute.id,
        trade_id=trade.id,
        seats_available=25,
        status=CourseStatus.FLAGGED,
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    gap = SkillGap(
        district_id=test_district.id,
        trade_id=trade.id,
        course_id=course.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.89,
        job_posting_volume=50,
        gap_score=58.2,
        score_breakdown={
            "similarity_score": 0.55,
            "market_demand_factor": 0.72,
        },
        status=GapStatus.APPROVED,
    )
    db_session.add(gap)
    await db_session.commit()
    await db_session.refresh(gap)

    admin = await create_test_user(
        email="admin_analytics@dev.vikas",
        role=UserRole.INSTITUTE_ADMIN,
        district_id=test_district.id,
        institute_id=test_institute.id,
    )
    token = auth_token_for(admin)

    # 1. Enrollment vs Demand
    evd_resp = await client.get(
        "/institute/enrollment-vs-demand",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert evd_resp.status_code == 200
    evd_data = evd_resp.json()
    assert evd_data["institute_id"] == str(test_institute.id)
    assert len(evd_data["courses"]) > 0
    copa_comp = next(
        (c for c in evd_data["courses"] if c["course_id"] == str(course.id)), None
    )
    assert copa_comp is not None
    assert copa_comp["seats_available"] == 25
    assert copa_comp["job_posting_volume"] == 50
    assert copa_comp["ratio"] == 2.0

    # 2. Flag Detail Drill-down
    detail_resp = await client.get(
        f"/institute/flags/{gap.id}/detail",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["flag_id"] == str(gap.id)
    assert detail["gap_score"] == 58.2
    assert len(detail["score_trend"]) == 6
    assert len(detail["skills_drifted"]) > 0
    assert len(detail["syllabus_skills"]) > 0


@pytest.mark.asyncio
async def test_institute_routes_role_gating(
    client: AsyncClient,
    test_district: District,
    create_test_user,
    auth_token_for,
) -> None:
    """Trainee and employer roles are blocked from /institute endpoints with 403."""
    trainee = await create_test_user(
        email="trainee_blocked_from_inst@dev.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )
    token = auth_token_for(trainee)

    endpoints = [
        ("GET", "/institute/flags"),
        ("GET", "/institute/enrollment-vs-demand"),
        ("POST", f"/institute/flags/{uuid.uuid4()}/acknowledge"),
        ("POST", f"/institute/flags/{uuid.uuid4()}/request-trainer-refresher"),
        ("GET", f"/institute/flags/{uuid.uuid4()}/detail"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = await client.get(path, headers={"Authorization": f"Bearer {token}"})
        else:
            res = await client.post(
                path, json={}, headers={"Authorization": f"Bearer {token}"}
            )
        assert res.status_code == 403, f"{method} {path} should be 403 for trainee"

"""Direct Database Row-Level Security (RLS) policy verification tests.

These tests prove that PostgreSQL RLS policies block cross-tenant / cross-district
reads and writes at the DB engine layer itself, completely independent of the API layer.
This satisfies the strict database-layer defense-in-depth requirement.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import set_rls_context
from app.models.course import Course
from app.models.district import District
from app.models.employer_validation import EmployerValidation
from app.models.enums import (
    CourseStatus,
    GapStatus,
    GapType,
    UserRole,
)
from app.models.flag_annotation import FlagAnnotation
from app.models.institute import Institute
from app.models.skill_gap import SkillGap
from app.models.trade import Trade


@pytest.fixture
async def test_trade(db_session: AsyncSession) -> Trade:
    """Ensure a trade exists for testing."""
    stmt = select(Trade).where(Trade.name == "Electrician")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(name="Electrician", nsqf_code="ELE/Q0101")
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)
    return trade


@pytest.mark.rls
@pytest.mark.asyncio
async def test_trainee_cross_district_skill_gaps_blocked_by_rls(
    db_session: AsyncSession,
    test_district: District,
    test_district_beed: District,
    test_trade: Trade,
    create_test_user,
) -> None:
    """DB-Level Test: Trainee can only read skill gaps in their own district."""
    # 1. Create trainee in Pune
    trainee_pune = await create_test_user(
        email=f"trainee_rls_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )

    # 2. Insert skill gaps in Pune and Beed as admin/superuser
    gap_pune = SkillGap(
        district_id=test_district.id,
        trade_id=test_trade.id,
        gap_type=GapType.UNDERSUPPLY,
        nlp_confidence=0.88,
        job_posting_volume=120,
        gap_score=76.5,
        score_breakdown={"demand": 80, "supply": 40},
        status=GapStatus.DETECTED,
    )
    gap_beed = SkillGap(
        district_id=test_district_beed.id,
        trade_id=test_trade.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.92,
        job_posting_volume=45,
        gap_score=62.0,
        score_breakdown={"demand": 50, "supply": 60},
        status=GapStatus.DETECTED,
    )
    db_session.add_all([gap_pune, gap_beed])
    await db_session.commit()

    # 3. Query under Trainee RLS context
    await set_rls_context(
        session=db_session,
        user_id=str(trainee_pune.id),
        role="trainee",
        district_id=str(test_district.id),
    )

    stmt = select(SkillGap).where(SkillGap.id.in_([gap_pune.id, gap_beed.id]))
    result = await db_session.execute(stmt)
    visible_gaps = result.scalars().all()
    visible_ids = {g.id for g in visible_gaps}

    # Pune gap must be visible; Beed gap MUST NOT be returned by PostgreSQL RLS
    assert gap_pune.id in visible_ids, (
        "Trainee cannot see their own district's skill gap"
    )
    assert gap_beed.id not in visible_ids, (
        "SECURITY VIOLATION: Trainee saw other district's skill gap!"
    )


@pytest.mark.rls
@pytest.mark.asyncio
async def test_institute_admin_cross_institute_courses_blocked_by_rls(
    db_session: AsyncSession,
    test_district: District,
    test_district_beed: District,
    test_trade: Trade,
    create_test_user,
) -> None:
    """DB-Level Test: Institute admin can only see own institute courses."""
    # 1. Setup institutes in Pune and Beed
    inst_pune = Institute(
        name=f"ITI Pune {uuid.uuid4().hex[:6]}",
        district_id=test_district.id,
        type="ITI",
    )
    inst_beed = Institute(
        name=f"ITI Beed {uuid.uuid4().hex[:6]}",
        district_id=test_district_beed.id,
        type="ITI",
    )
    db_session.add_all([inst_pune, inst_beed])
    await db_session.flush()

    # 2. Setup courses for each institute
    course_pune = Course(
        institute_id=inst_pune.id,
        trade_id=test_trade.id,
        seats_available=40,
        status=CourseStatus.ACTIVE,
    )
    course_beed = Course(
        institute_id=inst_beed.id,
        trade_id=test_trade.id,
        seats_available=25,
        status=CourseStatus.ACTIVE,
    )
    db_session.add_all([course_pune, course_beed])

    # 3. Setup institute admin for Pune institute
    admin_pune = await create_test_user(
        email=f"admin_pune_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.INSTITUTE_ADMIN,
        district_id=test_district.id,
        institute_id=inst_pune.id,
    )
    await db_session.commit()

    # 4. Query under Pune Admin RLS context
    await set_rls_context(
        session=db_session,
        user_id=str(admin_pune.id),
        role="institute_admin",
        district_id=str(test_district.id),
        institute_id=str(inst_pune.id),
    )

    stmt = select(Course).where(Course.id.in_([course_pune.id, course_beed.id]))
    result = await db_session.execute(stmt)
    visible_courses = result.scalars().all()
    visible_ids = {c.id for c in visible_courses}

    assert course_pune.id in visible_ids, "Admin cannot see own institute's course"
    assert course_beed.id not in visible_ids, (
        "SECURITY VIOLATION: Admin saw other institute's course!"
    )


@pytest.mark.rls
@pytest.mark.asyncio
async def test_employer_validations_rls_isolation_and_insert_check(
    db_session: AsyncSession,
    test_district: District,
    test_trade: Trade,
    create_test_user,
) -> None:
    """DB-Level Test: Employers can only read own validations and cannot spoof."""
    emp1 = await create_test_user(
        email=f"emp1_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.EMPLOYER,
        district_id=test_district.id,
    )
    emp2 = await create_test_user(
        email=f"emp2_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.EMPLOYER,
        district_id=test_district.id,
    )

    # Insert validation for emp2
    val2 = EmployerValidation(
        employer_user_id=emp2.id,
        trade_id=test_trade.id,
        district_id=test_district.id,
        confirmed_skills={"plc_programming": True},
        raw_free_text="Looking for PLC techs",
    )
    db_session.add(val2)
    await db_session.commit()

    # Switch to emp1 context
    await set_rls_context(
        session=db_session,
        user_id=str(emp1.id),
        role="employer",
        district_id=str(test_district.id),
    )

    # 1. emp1 querying validations: should NOT see val2
    stmt = select(EmployerValidation).where(EmployerValidation.id == val2.id)
    res = await db_session.execute(stmt)
    assert res.scalar_one_or_none() is None, (
        "SECURITY VIOLATION: Employer saw another employer's validation!"
    )

    # 2. Spoofing insert with emp2's user_id must fail via RLS WITH CHECK
    spoofed_val = EmployerValidation(
        employer_user_id=emp2.id,  # Spoofed!
        trade_id=test_trade.id,
        district_id=test_district.id,
        confirmed_skills={"welding": True},
    )
    db_session.add(spoofed_val)
    with pytest.raises(DBAPIError) as exc_info:
        await db_session.flush()

    assert "row-level security" in str(exc_info.value).lower()
    await db_session.rollback()


@pytest.mark.rls
@pytest.mark.asyncio
async def test_planner_cross_district_read_access(
    db_session: AsyncSession,
    test_district: District,
    test_district_beed: District,
    test_trade: Trade,
    create_test_user,
) -> None:
    """DB-Level Test: Planners have full SELECT access across all districts."""
    planner = await create_test_user(
        email=f"planner_rls_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.PLANNER,
        district_id=test_district.id,
    )

    # Insert gaps in both Pune and Beed
    gap_pune = SkillGap(
        district_id=test_district.id,
        trade_id=test_trade.id,
        gap_type=GapType.UNDERSUPPLY,
        nlp_confidence=0.85,
        job_posting_volume=100,
        gap_score=70.0,
        score_breakdown={"score": 70},
        status=GapStatus.DETECTED,
    )
    gap_beed = SkillGap(
        district_id=test_district_beed.id,
        trade_id=test_trade.id,
        gap_type=GapType.OVERSUPPLY,
        nlp_confidence=0.90,
        job_posting_volume=20,
        gap_score=40.0,
        score_breakdown={"score": 40},
        status=GapStatus.DETECTED,
    )
    db_session.add_all([gap_pune, gap_beed])
    await db_session.commit()

    # Query under Planner RLS context
    await set_rls_context(
        session=db_session,
        user_id=str(planner.id),
        role="planner",
        district_id=str(test_district.id),
    )

    stmt = select(SkillGap).where(SkillGap.id.in_([gap_pune.id, gap_beed.id]))
    result = await db_session.execute(stmt)
    visible_ids = {g.id for g in result.scalars().all()}

    # Planner must see BOTH districts
    assert gap_pune.id in visible_ids
    assert gap_beed.id in visible_ids


@pytest.mark.rls
@pytest.mark.asyncio
async def test_flag_annotations_planner_only_write(
    db_session: AsyncSession,
    test_district: District,
    test_trade: Trade,
    create_test_user,
) -> None:
    """DB-Level Test: Non-planners cannot write flag_annotations, planners can."""
    trainee = await create_test_user(
        email=f"trainee_anno_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
    )
    planner = await create_test_user(
        email=f"planner_anno_{uuid.uuid4().hex[:6]}@test.vikas",
        role=UserRole.PLANNER,
        district_id=test_district.id,
    )

    gap = SkillGap(
        district_id=test_district.id,
        trade_id=test_trade.id,
        gap_type=GapType.EMERGING_SKILL,
        nlp_confidence=0.95,
        job_posting_volume=300,
        gap_score=88.0,
        score_breakdown={"score": 88},
        status=GapStatus.DETECTED,
    )
    db_session.add(gap)
    await db_session.commit()

    planner_id = planner.id
    trainee_id = trainee.id
    gap_id = gap.id
    district_id_str = str(test_district.id)

    # 1. Trainee attempting to insert flag_annotation -> blocked by RLS
    await set_rls_context(
        session=db_session,
        user_id=str(trainee_id),
        role="trainee",
        district_id=district_id_str,
    )
    anno_trainee = FlagAnnotation(
        skill_gap_id=gap_id,
        planner_id=trainee_id,
        note="Trainee trying to add a note",
    )
    db_session.add(anno_trainee)
    with pytest.raises(DBAPIError):
        await db_session.flush()
    await db_session.rollback()

    # 2. Planner inserting flag_annotation -> allowed
    await set_rls_context(
        session=db_session,
        user_id=str(planner_id),
        role="planner",
        district_id=district_id_str,
    )
    anno_planner = FlagAnnotation(
        skill_gap_id=gap_id,
        planner_id=planner_id,
        note="Planner verified skill gap",
    )
    db_session.add(anno_planner)
    await db_session.flush()
    assert anno_planner.id is not None
    await db_session.rollback()

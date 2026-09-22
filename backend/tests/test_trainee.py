"""Unit and integration tests for trainee endpoints and services.

Verifies:
- Plain-language demand labels without exposing numeric scores.
- Empathetic alternatives shown only for flagged/obsolete courses.
- Plain-language proficiency expectations.
- Groq fallback on API failure/timeout.
- Grounded chat, query caching, and sliding-window rate limiting.
- Alerts delivery to trainees.
- Strict role gating.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert import Alert
from app.models.course import Course
from app.models.district import District
from app.models.enums import (
    AlertGenerator,
    AlertTargetRole,
    CourseStatus,
    GapStatus,
    GapType,
    UserRole,
)
from app.models.institute import Institute
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.user import User


@pytest.fixture
async def trainee_user(
    create_test_user: Callable[..., Any],
    test_district: District,
    test_institute: Institute,
) -> User:
    """Fixture for a trainee user in Pune."""
    return await create_test_user(
        email="test_trainee_pune@vikas.gov.in",
        role=UserRole.TRAINEE,
        district_id=test_district.id,
        institute_id=test_institute.id,
    )


@pytest.fixture
async def employer_user(
    create_test_user: Callable[..., Any],
    test_district: District,
) -> User:
    """Fixture for an employer user in Pune."""
    return await create_test_user(
        email="test_employer_pune@vikas.gov.in",
        role=UserRole.EMPLOYER,
        district_id=test_district.id,
    )


@pytest.fixture
async def sample_trade(db_session: AsyncSession) -> Trade:
    """Ensure at least one test trade exists."""
    stmt = select(Trade).where(Trade.name == "Electrician")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(
            name="Electrician",
            nsqf_code="ELE/Q0101",
        )
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)
    return trade


@pytest.fixture
async def sample_fitter_trade(db_session: AsyncSession) -> Trade:
    """Ensure a secondary trade (Fitter) exists."""
    stmt = select(Trade).where(Trade.name == "Fitter")
    trade = (await db_session.execute(stmt)).scalar_one_or_none()
    if not trade:
        trade = Trade(
            name="Fitter",
            nsqf_code="CSC/Q0901",
        )
        db_session.add(trade)
        await db_session.commit()
        await db_session.refresh(trade)
    return trade


@pytest.fixture
async def sample_courses(
    db_session: AsyncSession,
    test_institute: Institute,
    sample_trade: Trade,
    sample_fitter_trade: Trade,
) -> tuple[Course, Course]:
    """Create active and flagged sample courses in Pune."""
    # Active course
    stmt1 = select(Course).where(
        Course.institute_id == test_institute.id,
        Course.trade_id == sample_trade.id,
    )
    course1 = (await db_session.execute(stmt1)).scalars().first()
    if not course1:
        course1 = Course(
            institute_id=test_institute.id,
            trade_id=sample_trade.id,
            seats_available=25,
            status=CourseStatus.ACTIVE,
        )
        db_session.add(course1)
    else:
        course1.status = CourseStatus.ACTIVE

    # Flagged course (Fitter)
    stmt2 = select(Course).where(
        Course.institute_id == test_institute.id,
        Course.trade_id == sample_fitter_trade.id,
    )
    course2 = (await db_session.execute(stmt2)).scalars().first()
    if not course2:
        course2 = Course(
            institute_id=test_institute.id,
            trade_id=sample_fitter_trade.id,
            seats_available=15,
            status=CourseStatus.FLAGGED,
        )
        db_session.add(course2)
    else:
        course2.status = CourseStatus.FLAGGED

    await db_session.commit()
    await db_session.refresh(course1)
    await db_session.refresh(course2)
    return course1, course2


@pytest.mark.asyncio
async def test_get_courses_demand_labels_and_zero_raw_scores(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
    sample_courses: tuple[Course, Course],
    sample_trade: Trade,
    test_district: District,
    db_session: AsyncSession,
) -> None:
    """Trainee receives plain-language labels and zero raw scores."""
    # Seed a skill gap for the trade in this district
    gap_stmt = select(SkillGap).where(
        SkillGap.district_id == test_district.id,
        SkillGap.trade_id == sample_trade.id,
    )
    gap = (await db_session.execute(gap_stmt)).scalars().first()
    if not gap:
        gap = SkillGap(
            district_id=test_district.id,
            trade_id=sample_trade.id,
            gap_type=GapType.UNDERSUPPLY,
            nlp_confidence=0.88,
            job_posting_volume=45,
            gap_score=42.5,
            score_breakdown={"volume": 45, "gap": 42.5},
            status=GapStatus.APPROVED,
        )
        db_session.add(gap)
        await db_session.commit()

    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/trainee/courses", headers=headers)
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) >= 1

    for c in courses:
        # Check plain language fields exist
        assert "demand_label" in c
        assert "demand_level" in c
        assert "has_alternatives" in c
        assert isinstance(c["demand_label"], str)

        # STRICT AUDIT: Zero raw numeric scores exposed to trainee
        assert "gap_score" not in c
        assert "nlp_confidence" not in c
        assert "similarity" not in c
        assert "score_breakdown" not in c


@pytest.mark.asyncio
async def test_get_alternatives_when_active_vs_flagged(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
    sample_courses: tuple[Course, Course],
) -> None:
    """Active course returns no alternatives; flagged course returns active options."""
    active_course, flagged_course = sample_courses
    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Active course -> empty alternatives
    resp_active = await client.get(
        f"/trainee/courses/{active_course.id}/alternatives",
        headers=headers,
    )
    assert resp_active.status_code == 200
    active_data = resp_active.json()
    assert len(active_data["alternatives"]) == 0
    assert "actively aligned" in active_data["guidance_message"].lower()

    # 2. Flagged course -> returns active courses
    resp_flagged = await client.get(
        f"/trainee/courses/{flagged_course.id}/alternatives",
        headers=headers,
    )
    assert resp_flagged.status_code == 200
    flagged_data = resp_flagged.json()
    assert len(flagged_data["alternatives"]) >= 1
    assert "Career Guidance Note" in flagged_data["guidance_message"]

    first_alt = flagged_data["alternatives"][0]
    assert first_alt["status"] == "active"
    assert "recommendation_rationale" in first_alt
    assert "gap_score" not in first_alt


@pytest.mark.asyncio
async def test_proficiency_expectations(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
    sample_trade: Trade,
    test_district: District,
) -> None:
    """Proficiency expectations return plain-language categorized skills."""
    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(
        f"/trainee/proficiency-expectations?trade_id={sample_trade.id}&district_id={test_district.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trade_name"] == sample_trade.name
    assert data["district_name"] == test_district.name
    assert len(data["top_in_demand_skills"]) > 0
    assert len(data["skill_categories"]) == 3

    categories = [cat["category"] for cat in data["skill_categories"]]
    assert "Core Tools & Equipment" in categories
    assert "Key Technical Competencies" in categories
    assert "Emerging Industry Techniques" in categories


@pytest.mark.asyncio
async def test_groq_fallback_on_error(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
) -> None:
    """When Groq API fails or times out, fallback deterministic reply is returned."""
    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    orig_post = httpx.AsyncClient.post

    async def mock_post(
        self: httpx.AsyncClient, url: Any, *args: Any, **kwargs: Any
    ) -> Any:
        if "groq" in str(url):
            raise httpx.ConnectError("Groq service unreachable")
        return await orig_post(self, url, *args, **kwargs)

    with (
        patch.object(settings, "groq_api_key", "gsk_simulated_key"),
        patch.object(httpx.AsyncClient, "post", new=mock_post),
    ):
        response = await client.post(
            "/trainee/chat",
            headers=headers,
            json={"question": "What electrician courses are available in Pune?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_used"] is True
        assert len(data["reply"]) > 10
        assert "Pune" in data["grounded_district"]


@pytest.mark.asyncio
async def test_chat_grounding_and_rate_limiting(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
) -> None:
    """Grounded chat uses caching and enforces sliding-window rate limit."""
    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Ask initial question
    resp1 = await client.post(
        "/trainee/chat",
        headers=headers,
        json={"question": "Tell me about course seats in Pune"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "reply" in data1

    # 2. Ask identical question -> cache hit
    resp2 = await client.post(
        "/trainee/chat",
        headers=headers,
        json={"question": "Tell me about course seats in Pune"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data1["reply"] == data2["reply"]

    # 3. Exceed rate limit (10 requests per minute)
    hit_limit = False
    for i in range(12):
        r = await client.post(
            "/trainee/chat",
            headers=headers,
            json={"question": f"Question test sequence #{i}?"},
        )
        if r.status_code == 429:
            hit_limit = True
            break

    assert hit_limit is True


@pytest.mark.asyncio
async def test_trainee_alerts(
    client: httpx.AsyncClient,
    trainee_user: User,
    auth_token_for: Callable[[User], str],
    sample_courses: tuple[Course, Course],
    sample_trade: Trade,
    test_district: District,
    db_session: AsyncSession,
) -> None:
    """Trainee alerts are returned cleanly without raw scores."""
    # Seed a test alert for this trainee
    gap_stmt = select(SkillGap).where(SkillGap.district_id == test_district.id)
    gap = (await db_session.execute(gap_stmt)).scalars().first()
    if not gap:
        gap = SkillGap(
            district_id=test_district.id,
            trade_id=sample_trade.id,
            gap_type=GapType.UNDERSUPPLY,
            nlp_confidence=0.9,
            job_posting_volume=30,
            gap_score=35.0,
            score_breakdown={"volume": 30},
            status=GapStatus.APPROVED,
        )
        db_session.add(gap)
        await db_session.commit()

    alert = Alert(
        target_role=AlertTargetRole.TRAINEE,
        target_id=trainee_user.id,
        skill_gap_id=gap.id,
        message=(
            "Career Guidance: Local employers in Pune show strong "
            "demand for Electrician skills."
        ),
        generated_by=AlertGenerator.TEMPLATE,
        reviewed=False,
    )
    db_session.add(alert)
    await db_session.commit()

    token = auth_token_for(trainee_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/trainee/alerts", headers=headers)
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    assert "strong demand" in alerts[0]["message"].lower()


@pytest.mark.asyncio
async def test_trainee_routes_role_gating(
    client: httpx.AsyncClient,
    employer_user: User,
    auth_token_for: Callable[[User], str],
) -> None:
    """Non-trainee role is rejected with 403 on trainee routes."""
    token = auth_token_for(employer_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/trainee/courses", headers=headers)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()

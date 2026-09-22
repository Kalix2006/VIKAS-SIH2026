"""Unit and integration tests for Planner Dashboard backend endpoints.

Tests:
1. GET /planner/map: Volume-weighted Alignment Health Index formula and aggregation.
2. GET /planner/districts/{district_id}: Trade-level drill-down data table.
3. GET /planner/compare: Cross-district trade comparison and delta insights.
4. POST /planner/flags/{flag_id}/annotate: Planner supervisory notes and overrides.
5. GET /planner/export/capacity-plan: JSON and CSV export formats.
6. RBAC Defense-in-Depth: Verifies non-planner roles (trainee, admin, employer, panel)
   are blocked from planner-only write actions with 403 Forbidden.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.district import District
from app.models.enums import CourseStatus, GapStatus, GapType, UserRole
from app.models.institute import Institute
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.user import User


@pytest.fixture
async def planner_fixtures(db_session: AsyncSession):
    """Seed test fixtures for planner tests."""
    # 1. Districts
    dist_a = District(
        name=f"District_A_{uuid.uuid4().hex[:6]}",
        state="Maharashtra",
        centroid_lat=18.5204,
        centroid_lng=73.8567,
    )
    dist_b = District(
        name=f"District_B_{uuid.uuid4().hex[:6]}",
        state="Maharashtra",
        centroid_lat=19.8762,
        centroid_lng=75.3433,
    )
    db_session.add_all([dist_a, dist_b])
    await db_session.flush()

    # 2. Trades
    trade_1 = Trade(
        name=f"Electrician_{uuid.uuid4().hex[:6]}",
        nsqf_code=f"NSQF-ELE-{uuid.uuid4().hex[:4]}",
    )
    trade_2 = Trade(
        name=f"Fitter_{uuid.uuid4().hex[:6]}",
        nsqf_code=f"NSQF-FIT-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([trade_1, trade_2])
    await db_session.flush()

    # 3. Institutes & Courses
    inst_a = Institute(
        name=f"ITI A_{uuid.uuid4().hex[:6]}",
        district_id=dist_a.id,
        type="ITI",
    )
    inst_b = Institute(
        name=f"ITI B_{uuid.uuid4().hex[:6]}",
        district_id=dist_b.id,
        type="ITI",
    )
    db_session.add_all([inst_a, inst_b])
    await db_session.flush()

    course_a1 = Course(
        institute_id=inst_a.id,
        trade_id=trade_1.id,
        seats_available=20,
        status=CourseStatus.ACTIVE,
    )
    course_b1 = Course(
        institute_id=inst_b.id,
        trade_id=trade_1.id,
        seats_available=40,
        status=CourseStatus.ACTIVE,
    )
    db_session.add_all([course_a1, course_b1])
    await db_session.flush()

    # 4. Skill Gaps
    gap_a1 = SkillGap(
        district_id=dist_a.id,
        trade_id=trade_1.id,
        course_id=course_a1.id,
        gap_type=GapType.CURRICULUM_DRIFT,
        nlp_confidence=0.85,
        job_posting_volume=80,
        gap_score=68.0,
        score_breakdown={
            "similarity_score": 0.65,
            "dissimilarity": 0.35,
            "volume_factor": 0.8,
            "volume_weight": 0.6,
            "recency_decay": 0.75,
            "recency_weight": 0.4,
            "market_demand_factor": 0.78,
            "final_gap_score": 68.0,
            "formula": "Gap Score = (1 - S) * [0.60 * F_v + 0.40 * R]",
        },
        status=GapStatus.DETECTED,
    )
    gap_b1 = SkillGap(
        district_id=dist_b.id,
        trade_id=trade_1.id,
        course_id=course_b1.id,
        gap_type=GapType.OVERSUPPLY,
        nlp_confidence=0.90,
        job_posting_volume=10,
        gap_score=35.0,
        score_breakdown={
            "similarity_score": 0.85,
            "dissimilarity": 0.15,
            "volume_factor": 0.3,
            "volume_weight": 0.6,
            "recency_decay": 0.8,
            "recency_weight": 0.4,
            "market_demand_factor": 0.5,
            "final_gap_score": 35.0,
        },
        status=GapStatus.DETECTED,
    )
    db_session.add_all([gap_a1, gap_b1])
    await db_session.flush()

    # 5. Users for RBAC testing
    planner_user = User(
        email=f"planner_{uuid.uuid4().hex[:6]}@test.vikas",
        password_hash="hash",
        role=UserRole.PLANNER,
        full_name="State Skill Officer",
        district_id=dist_a.id,
    )
    trainee_user = User(
        email=f"trainee_{uuid.uuid4().hex[:6]}@test.vikas",
        password_hash="hash",
        role=UserRole.TRAINEE,
        full_name="Test Trainee",
        district_id=dist_a.id,
    )
    institute_user = User(
        email=f"institute_{uuid.uuid4().hex[:6]}@test.vikas",
        password_hash="hash",
        role=UserRole.INSTITUTE_ADMIN,
        full_name="Test Admin",
        district_id=dist_a.id,
        institute_id=inst_a.id,
    )
    employer_user = User(
        email=f"employer_{uuid.uuid4().hex[:6]}@test.vikas",
        password_hash="hash",
        role=UserRole.EMPLOYER,
        full_name="Test Employer",
        district_id=dist_a.id,
    )
    panel_user = User(
        email=f"panel_{uuid.uuid4().hex[:6]}@test.vikas",
        password_hash="hash",
        role=UserRole.PANEL_MEMBER,
        full_name="Test Panel Member",
        district_id=dist_a.id,
    )
    db_session.add_all(
        [
            planner_user,
            trainee_user,
            institute_user,
            employer_user,
            panel_user,
        ]
    )
    await db_session.commit()

    return {
        "dist_a": dist_a,
        "dist_b": dist_b,
        "trade_1": trade_1,
        "trade_2": trade_2,
        "gap_a1": gap_a1,
        "gap_b1": gap_b1,
        "planner_user": planner_user,
        "trainee_user": trainee_user,
        "institute_user": institute_user,
        "employer_user": employer_user,
        "panel_user": panel_user,
    }


def make_auth_header(user: User) -> dict[str, str]:
    """Helper to generate JWT bearer token header for a user."""
    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        district_id=str(user.district_id),
        institute_id=str(user.institute_id) if user.institute_id else None,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_planner_map_alignment_health_aggregation(
    planner_fixtures,
):
    """Verify GET /planner/map computes volume-weighted AHI and categories correctly."""
    fixtures = planner_fixtures
    planner_headers = make_auth_header(fixtures["planner_user"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/planner/map", headers=planner_headers)
        assert res.status_code == 200
        data = res.json()

        assert "districts" in data
        assert "state_avg_health" in data
        assert "formula_definition" in data
        assert len(data["districts"]) >= 2

        # Check district A
        dist_a_summary = next(
            d for d in data["districts"] if d["id"] == str(fixtures["dist_a"].id)
        )
        assert dist_a_summary["name"] == fixtures["dist_a"].name
        assert dist_a_summary["centroid_lat"] == 18.5204
        assert dist_a_summary["total_job_volume"] == 80
        # gap_score is 68.0, so AHI = 100 - 68.0 = 32.0 (Critical Divergence)
        assert dist_a_summary["alignment_health_score"] == 32.0
        assert dist_a_summary["health_category"] == "Critical Divergence"

        # Check district B
        dist_b_summary = next(
            d for d in data["districts"] if d["id"] == str(fixtures["dist_b"].id)
        )
        # gap_score is 35.0, so AHI = 100 - 35.0 = 65.0 (Moderate Drift)
        assert dist_b_summary["alignment_health_score"] == 65.0
        assert dist_b_summary["health_category"] == "Moderate Drift"


@pytest.mark.asyncio
async def test_planner_district_drilldown(
    planner_fixtures,
):
    """Verify GET /planner/districts/{district_id} returns trade-level data table payload."""
    fixtures = planner_fixtures
    planner_headers = make_auth_header(fixtures["planner_user"])
    dist_a_id = fixtures["dist_a"].id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(
            f"/planner/districts/{dist_a_id}", headers=planner_headers
        )
        assert res.status_code == 200
        data = res.json()

        assert data["district_name"] == fixtures["dist_a"].name
        assert len(data["trades"]) >= 2

        trade_1_row = next(
            t for t in data["trades"] if t["trade_id"] == str(fixtures["trade_1"].id)
        )
        assert trade_1_row["gap_score"] == 68.0
        assert trade_1_row["alignment_score"] == 32.0
        assert trade_1_row["seats_available"] == 20
        assert trade_1_row["job_posting_volume"] == 80
        assert trade_1_row["hiring_to_seats_ratio"] == 4.0
        assert trade_1_row["trend_direction"] == "deteriorating"


@pytest.mark.asyncio
async def test_planner_compare_districts(
    planner_fixtures,
):
    """Verify GET /planner/compare returns side-by-side trade comparison with delta."""
    fixtures = planner_fixtures
    planner_headers = make_auth_header(fixtures["planner_user"])
    dist_a_id = fixtures["dist_a"].id
    dist_b_id = fixtures["dist_b"].id
    trade_id = fixtures["trade_1"].id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(
            f"/planner/compare?district_ids={dist_a_id},{dist_b_id}&trade_id={trade_id}",
            headers=planner_headers,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["trade_id"] == str(trade_id)
        assert data["district_a"]["district_name"] == fixtures["dist_a"].name
        assert data["district_b"]["district_name"] == fixtures["dist_b"].name
        assert data["district_a"]["alignment_score"] == 32.0
        assert data["district_b"]["alignment_score"] == 65.0
        # delta = 32.0 - 65.0 = -33.0
        assert data["alignment_score_delta"] == -33.0
        assert "comparative_insight" in data
        assert len(data["comparative_insight"]) > 20


@pytest.mark.asyncio
async def test_planner_flag_annotate_and_override(
    planner_fixtures, db_session: AsyncSession
):
    """Verify POST /planner/flags/{flag_id}/annotate persists note and executes override."""
    fixtures = planner_fixtures
    planner_headers = make_auth_header(fixtures["planner_user"])
    gap_id = fixtures["gap_a1"].id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Add annotation with override_status="confirmed"
        res = await client.post(
            f"/planner/flags/{gap_id}/annotate",
            headers=planner_headers,
            json={
                "note": "Field audit verifies severe solar drift; accelerating to urgent track.",
                "override_status": "confirmed",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["override_status"] == "confirmed"
        assert data["new_gap_status"] == "urgent_escalation"

        # Verify in DB
        db_gap = await db_session.get(SkillGap, gap_id)
        await db_session.refresh(db_gap)
        assert db_gap.status == GapStatus.URGENT_ESCALATION

        # 2. Add annotation with override_status="dismissed"
        res2 = await client.post(
            f"/planner/flags/{gap_id}/annotate",
            headers=planner_headers,
            json={
                "note": "Resolved through local employer CSR MOU.",
                "override_status": "dismissed",
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["override_status"] == "dismissed"
        assert data2["new_gap_status"] == "rejected"

        await db_session.refresh(db_gap)
        assert db_gap.status == GapStatus.REJECTED
        assert db_gap.resolved_at is not None


@pytest.mark.asyncio
async def test_planner_capacity_plan_export_json_and_csv(
    planner_fixtures,
):
    """Verify GET /planner/export/capacity-plan supports both JSON and downloadable CSV formats."""
    fixtures = planner_fixtures
    planner_headers = make_auth_header(fixtures["planner_user"])
    dist_a_id = fixtures["dist_a"].id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # JSON format
        res_json = await client.get(
            f"/planner/export/capacity-plan?district_id={dist_a_id}&format=json",
            headers=planner_headers,
        )
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["district_name"] == fixtures["dist_a"].name
        assert len(data["recommendations"]) >= 2

        # Ratio in dist_a for trade_1 is 80 / 20 = 4.0 -> recommend positive seat adjustment
        trade_1_rec = next(
            r
            for r in data["recommendations"]
            if r["trade_id"] == str(fixtures["trade_1"].id)
        )
        assert trade_1_rec["recommended_seat_adjustment"] > 0
        assert trade_1_rec["recommended_trainer_workshops"] >= 1
        assert trade_1_rec["equipment_investment_priority"] == "High"

        # CSV format
        res_csv = await client.get(
            f"/planner/export/capacity-plan?district_id={dist_a_id}&format=csv",
            headers=planner_headers,
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "attachment" in res_csv.headers["content-disposition"]
        csv_text = res_csv.text
        assert "Trade Name" in csv_text
        assert "Seat Adjustment" in csv_text
        assert fixtures["dist_a"].name in csv_text


@pytest.mark.asyncio
async def test_planner_write_actions_blocked_for_other_roles(
    planner_fixtures,
):
    """Verify non-planner roles (trainee, admin, employer, panel) cannot execute planner writes."""
    fixtures = planner_fixtures
    gap_id = fixtures["gap_a1"].id

    roles_to_test = [
        fixtures["trainee_user"],
        fixtures["institute_user"],
        fixtures["employer_user"],
        fixtures["panel_user"],
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for user in roles_to_test:
            headers = make_auth_header(user)
            # Attempt to annotate flag
            res = await client.post(
                f"/planner/flags/{gap_id}/annotate",
                headers=headers,
                json={"note": "Unauthorized tampering attempt."},
            )
            assert res.status_code == 403, (
                f"Expected 403 Forbidden for role '{user.role}', got {res.status_code}"
            )

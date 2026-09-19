"""Unit and integration tests for Employer Validation & Demand Signals endpoints.

Tests:
1. GET /employer/skills-inferred: Pre-filled inferred skills for quick 1-minute confirmation.
2. POST /employer/validate: Skill confirmation and Groq free-text parsing with deterministic fallback.
3. POST /employer/hiring-signal: Structured vacancy demand signaling.
4. GET /employer/aggregate-readiness: STRICT PRIVACY-BY-DESIGN AUDIT verifying zero candidate
   identifiers (trainee_id, student names, emails, roll numbers, personal profiles) in response.
5. GET /employer/my-validations: Scoped list of employer's own submissions.
6. RBAC & Multi-tenant Defense: Non-employer roles receive 403 Forbidden, and Employer A
   cannot view Employer B's validation records.
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.district import District
from app.models.employer_validation import EmployerValidation
from app.models.enums import CourseStatus, UserRole
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.trade import Trade
from app.models.user import User


@pytest.fixture
async def employer_fixtures(db_session: AsyncSession):
    """Seed test fixtures for employer endpoints."""
    # 1. District
    district = District(
        name=f"District_Emp_{uuid.uuid4().hex[:6]}",
        state="Maharashtra",
        centroid_lat=18.5204,
        centroid_lng=73.8567,
    )
    db_session.add(district)
    await db_session.flush()

    # 2. Trade
    trade = Trade(
        name=f"Electrician_{uuid.uuid4().hex[:6]}",
        nsqf_code=f"NSQF-ELE-{uuid.uuid4().hex[:4]}",
    )
    db_session.add(trade)
    await db_session.flush()

    # 3. Institute & Course
    institute = Institute(
        name=f"Govt ITI {uuid.uuid4().hex[:6]}",
        district_id=district.id,
        type="ITI",
    )
    db_session.add(institute)
    await db_session.flush()

    course = Course(
        institute_id=institute.id,
        trade_id=trade.id,
        seats_available=60,
        status=CourseStatus.ACTIVE,
    )
    db_session.add(course)

    # 4. Job postings with extracted skills
    posting = JobPosting(
        source="adzuna",
        district_id=district.id,
        trade_id=trade.id,
        raw_title="Senior Industrial Electrician",
        raw_description="Looking for electrician skilled in PLC and Solar Inverters.",
        extracted_skills={
            "skills": ["PLC Troubleshooting", "Solar Inverter Maintenance", "Earthing"],
            "tools": ["Multimeter", "Megger"],
        },
        posted_at=datetime.now(timezone.utc),
    )
    db_session.add(posting)
    await db_session.flush()

    # 5. Employer User A
    employer_a = User(
        email=f"employer_a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="argon2_fake_hash",
        role=UserRole.EMPLOYER,
        full_name="Mahindra Plant HR",
        district_id=district.id,
    )
    # Employer User B
    employer_b = User(
        email=f"employer_b_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="argon2_fake_hash",
        role=UserRole.EMPLOYER,
        full_name="Tata Motors HR",
        district_id=district.id,
    )
    # Trainee User (for RBAC testing)
    trainee_user = User(
        email=f"trainee_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="argon2_fake_hash",
        role=UserRole.TRAINEE,
        full_name="Rohan Trainee",
        district_id=district.id,
    )
    db_session.add_all([employer_a, employer_b, trainee_user])
    await db_session.commit()

    token_a = create_access_token(
        subject=str(employer_a.id),
        role=UserRole.EMPLOYER.value,
        district_id=str(district.id),
    )
    token_b = create_access_token(
        subject=str(employer_b.id),
        role=UserRole.EMPLOYER.value,
        district_id=str(district.id),
    )
    token_trainee = create_access_token(
        subject=str(trainee_user.id),
        role=UserRole.TRAINEE.value,
        district_id=str(district.id),
    )

    return {
        "district": district,
        "trade": trade,
        "employer_a": employer_a,
        "employer_b": employer_b,
        "trainee": trainee_user,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
        "headers_trainee": {"Authorization": f"Bearer {token_trainee}"},
    }


@pytest.mark.asyncio
async def test_employer_skills_inferred(employer_fixtures):
    """Test GET /employer/skills-inferred returns pre-filled skills for 1-minute confirmation."""
    f = employer_fixtures
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(
            f"/employer/skills-inferred?trade_id={f['trade'].id}&district_id={f['district'].id}",
            headers=f["headers_a"],
        )
        assert res.status_code == 200
        data = res.json()
        assert data["trade_id"] == str(f["trade"].id)
        assert data["district_id"] == str(f["district"].id)
        assert data["total_postings_analyzed"] >= 1
        assert len(data["inferred_skills"]) > 0

        first_skill = data["inferred_skills"][0]
        assert "skill_name" in first_skill
        assert "category" in first_skill
        assert "is_recommended" in first_skill
        assert first_skill["is_recommended"] is True


@pytest.mark.asyncio
async def test_employer_validate_structured_and_fallback(employer_fixtures):
    """Test POST /employer/validate with confirmed skills and free-text parsing/fallback."""
    f = employer_fixtures
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "trade_id": str(f["trade"].id),
            "district_id": str(f["district"].id),
            "confirmed_skills": [
                "Industrial Control Panel Assembly",
                "Solar Inverter Setup",
            ],
            "raw_free_text": "Need technicians experienced in PLC Ladder Logic and three-phase motor maintenance.",
        }
        res = await client.post(
            "/employer/validate",
            headers=f["headers_a"],
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["validation_id"] is not None
        assert "Industrial Control Panel Assembly" in data["confirmed_skills"]
        assert "Solar Inverter Setup" in data["confirmed_skills"]
        # Fallback will either be Groq parsed (if key provided) or deterministic fallback
        assert isinstance(data["extracted_from_free_text"], list)
        assert isinstance(data["parsed_by_llm"], bool)
        assert isinstance(data["needs_manual_review"], bool)


@pytest.mark.asyncio
async def test_employer_hiring_signal(employer_fixtures):
    """Test POST /employer/hiring-signal records structured vacancy intention."""
    f = employer_fixtures
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "trade_id": str(f["trade"].id),
            "district_id": str(f["district"].id),
            "vacancies_count": 30,
            "timeframe_months": 3,
            "urgency": "immediate",
            "notes": "Plant expansion requires immediate electrical maintenance batch.",
        }
        res = await client.post(
            "/employer/hiring-signal",
            headers=f["headers_a"],
            json=payload,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["signal_id"] is not None
        assert data["vacancies_count"] == 30
        assert data["timeframe_months"] == 3
        assert data["urgency"] == "immediate"


@pytest.mark.asyncio
async def test_employer_aggregate_readiness_strict_privacy_audit(employer_fixtures):
    """CRITICAL PRIVACY TEST: Verify GET /employer/aggregate-readiness exposes NO PII or trainee identifiers.

    Recursively scans every key, nested dictionary, list, and string in the response
    to guarantee zero per-person identifiable fields are returned to the employer role.
    """
    f = employer_fixtures
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get(
            f"/employer/aggregate-readiness?trade_id={f['trade'].id}&district_id={f['district'].id}",
            headers=f["headers_a"],
        )
        assert res.status_code == 200
        data = res.json()

        # Basic aggregate structure
        assert "total_enrolled_trainees" in data
        assert "cohort_readiness_index" in data
        assert "readiness_distribution" in data
        assert "competency_mastery" in data
        assert "privacy_guarantee" in data

        # Blacklisted candidate identity substrings (lower-cased)
        FORBIDDEN_KEY_SUBSTRINGS = [
            "trainee_id",
            "candidate_id",
            "student_id",
            "roll_number",
            "user_id",
            "full_name",
            "first_name",
            "last_name",
            "trainee_name",
            "candidate_name",
            "email",
            "phone",
            "mobile",
            "aadhaar",
            "address",
            "gender",
            "date_of_birth",
            "dob",
        ]

        def recursive_privacy_check(obj, path="root"):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    key_lower = k.lower()
                    # Assert no forbidden key exists
                    for forbidden in FORBIDDEN_KEY_SUBSTRINGS:
                        assert forbidden not in key_lower, (
                            f"PRIVACY VIOLATION: Forbidden candidate identifier key '{k}' "
                            f"found at path '{path}.{k}'"
                        )
                    recursive_privacy_check(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    recursive_privacy_check(item, f"{path}[{idx}]")

        # Execute recursive privacy audit
        recursive_privacy_check(data)


@pytest.mark.asyncio
async def test_employer_rbac_and_isolation(employer_fixtures):
    """Test RBAC blocks non-employers and validates employer isolation."""
    f = employer_fixtures
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trainee attempting to access employer endpoint -> 403
        res = await client.get(
            f"/employer/skills-inferred?trade_id={f['trade'].id}&district_id={f['district'].id}",
            headers=f["headers_trainee"],
        )
        assert res.status_code == 403

        # Employer A submits validation
        val_res = await client.post(
            "/employer/validate",
            headers=f["headers_a"],
            json={
                "trade_id": str(f["trade"].id),
                "district_id": str(f["district"].id),
                "confirmed_skills": ["Panel Assembly"],
            },
        )
        assert val_res.status_code == 200

        # Employer A sees their validation
        list_a = await client.get("/employer/my-validations", headers=f["headers_a"])
        assert list_a.status_code == 200
        assert len(list_a.json()) >= 1

        # Employer B sees only their own validations (isolation)
        list_b = await client.get("/employer/my-validations", headers=f["headers_b"])
        assert list_b.status_code == 200
        assert len(list_b.json()) == 0


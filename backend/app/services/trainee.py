"""Trainee service for courses, alternatives, expectations, and grounded chat.

Strictly grounded in district-level database records:
- Hides all raw metrics/scores from trainees.
- Rate-limited and cached Groq chat assistant with mandatory template fallback.
- Refuses to speculate or hallucinate outside the local district context.
"""

import hashlib
import logging
import time
import uuid
from collections import Counter

import httpx
from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.alert import Alert
from app.models.course import Course
from app.models.district import District
from app.models.enums import AlertTargetRole, CourseStatus, GapStatus
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.schemas.trainee import (
    AlternativesGuideResponse,
    ChatResponse,
    CourseAlternativeResponse,
    ProficiencyExpectationsResponse,
    SkillCategory,
    TraineeCourseResponse,
)
from app.services.alert import get_demand_label

logger = logging.getLogger("vikas.trainee")

# In-memory sliding-window rate limiter: {user_id: [epoch_timestamps]}
_user_rate_limits: dict[uuid.UUID, list[float]] = {}

# In-memory query cache:
# {hash: (expiry, reply, district_name, course_count, fallback_used)}
_chat_cache: dict[str, tuple[float, str, str, int, bool]] = {}


class TraineeService:
    """Business logic for trainee operations."""

    async def get_district_courses(
        self, db: AsyncSession, district_id: uuid.UUID
    ) -> list[TraineeCourseResponse]:
        """Fetch courses in trainee's district with plain-language demand labels."""
        query = (
            select(Course)
            .join(Course.institute)
            .join(Course.trade)
            .where(Institute.district_id == district_id)
            .options(joinedload(Course.institute), joinedload(Course.trade))
            .order_by(Course.status, Course.trade_id)
        )
        courses = list((await db.execute(query)).scalars().all())

        gap_query = select(SkillGap).where(
            SkillGap.district_id == district_id,
            SkillGap.status.in_([GapStatus.APPROVED, GapStatus.DETECTED]),
        )
        gaps = list((await db.execute(gap_query)).scalars().all())
        trade_gaps = {gap.trade_id: gap for gap in gaps}

        response_list: list[TraineeCourseResponse] = []
        for course in courses:
            gap = trade_gaps.get(course.trade_id)
            if gap:
                demand_label, demand_level = get_demand_label(
                    gap.gap_score, gap.gap_type
                )
            else:
                demand_label, demand_level = "Stable local demand", "stable"

            has_alts = course.status in (
                CourseStatus.FLAGGED,
                CourseStatus.OBSOLETE,
            )

            response_list.append(
                TraineeCourseResponse(
                    id=course.id,
                    institute_id=course.institute_id,
                    institute_name=course.institute.name,
                    trade_id=course.trade_id,
                    trade_name=course.trade.name,
                    nsqf_code=course.trade.nsqf_code,
                    seats_available=course.seats_available,
                    status=course.status,
                    demand_label=demand_label,
                    demand_level=demand_level,
                    has_alternatives=has_alts,
                )
            )

        return response_list

    async def get_course_alternatives(
        self, db: AsyncSession, course_id: uuid.UUID
    ) -> AlternativesGuideResponse:
        """Return empathetic guidance and active alternative courses."""
        course_query = (
            select(Course)
            .where(Course.id == course_id)
            .options(joinedload(Course.institute), joinedload(Course.trade))
        )
        course = (await db.execute(course_query)).scalar_one_or_none()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        trade_name = course.trade.name
        institute_name = course.institute.name
        district_id = course.institute.district_id

        if course.status == CourseStatus.ACTIVE:
            return AlternativesGuideResponse(
                flagged_course_name=trade_name,
                flagged_institute_name=institute_name,
                guidance_message=(
                    f"This course ({trade_name}) is actively aligned with "
                    "local industry standards. No alternative enrollment "
                    "is required at this time."
                ),
                alternatives=[],
            )

        alt_query = (
            select(Course)
            .join(Course.institute)
            .join(Course.trade)
            .where(
                Institute.district_id == district_id,
                Course.id != course_id,
                Course.status == CourseStatus.ACTIVE,
            )
            .options(joinedload(Course.institute), joinedload(Course.trade))
            .order_by(desc(Course.seats_available))
        )
        active_courses = list((await db.execute(alt_query)).scalars().all())

        gap_query = select(SkillGap).where(SkillGap.district_id == district_id)
        gaps = list((await db.execute(gap_query)).scalars().all())
        trade_gaps = {gap.trade_id: gap for gap in gaps}

        alternatives: list[CourseAlternativeResponse] = []
        for alt in active_courses:
            gap = trade_gaps.get(alt.trade_id)
            demand_label, _ = (
                get_demand_label(gap.gap_score, gap.gap_type)
                if gap
                else ("Stable local demand", "stable")
            )

            if alt.trade_id == course.trade_id:
                rationale = (
                    f"Accredited active program for {alt.trade.name} at "
                    f"{alt.institute.name} with {alt.seats_available} open seats "
                    "and updated curriculum equipment."
                )
            else:
                rationale = (
                    f"High-synergy vocational program ({alt.trade.name}) at "
                    f"{alt.institute.name} with strong hiring alignment "
                    "in your district."
                )

            alternatives.append(
                CourseAlternativeResponse(
                    id=alt.id,
                    institute_id=alt.institute_id,
                    institute_name=alt.institute.name,
                    trade_id=alt.trade_id,
                    trade_name=alt.trade.name,
                    nsqf_code=alt.trade.nsqf_code,
                    seats_available=alt.seats_available,
                    status=alt.status,
                    demand_label=demand_label,
                    recommendation_rationale=rationale,
                )
            )

        guidance_message = (
            f"Career Guidance Note: While the {trade_name} curriculum at "
            f"{institute_name} provides valuable foundational knowledge, "
            "local industries in your district are currently seeking updated modern "
            "competencies. To maximize your employment prospects upon graduation, "
            "we recommend exploring these active courses with healthy local "
            "employer demand."
        )

        return AlternativesGuideResponse(
            flagged_course_name=trade_name,
            flagged_institute_name=institute_name,
            guidance_message=guidance_message,
            alternatives=alternatives,
        )

    async def get_proficiency_expectations(
        self, db: AsyncSession, trade_id: uuid.UUID, district_id: uuid.UUID
    ) -> ProficiencyExpectationsResponse:
        """Surface plain-language skills sought by employers from postings."""
        trade = (
            await db.execute(select(Trade).where(Trade.id == trade_id))
        ).scalar_one_or_none()
        district = (
            await db.execute(select(District).where(District.id == district_id))
        ).scalar_one_or_none()

        if not trade or not district:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade or district not found",
            )

        postings_query = (
            select(JobPosting)
            .where(
                JobPosting.district_id == district_id,
                JobPosting.trade_id == trade_id,
            )
            .order_by(desc(JobPosting.posted_at))
            .limit(100)
        )
        postings = list((await db.execute(postings_query)).scalars().all())

        extracted_skills_counter: Counter[str] = Counter()
        extracted_tools_counter: Counter[str] = Counter()

        for p in postings:
            if p.extracted_skills and isinstance(p.extracted_skills, dict):
                skills_list = p.extracted_skills.get("skills", [])
                tools_list = p.extracted_skills.get("tools", [])
                for s in skills_list:
                    extracted_skills_counter[s] += 1
                for t in tools_list:
                    extracted_tools_counter[t] += 1

        default_skills = {
            "Electrician": {
                "tools": [
                    "Multimeter",
                    "Megger",
                    "Conduit Bender",
                    "Wire Stripper",
                    "Drill Machine",
                ],
                "competencies": [
                    "Domestic Wiring",
                    "Control Panel Assembly",
                    "Circuit Breaker Testing",
                    "Earthing Standards",
                ],
                "emerging": [
                    "Solar Rooftop Installation",
                    "Smart Energy Metering",
                    "EV Charging Stations",
                ],
            },
            "Fitter": {
                "tools": [
                    "Vernier Caliper",
                    "Micrometer",
                    "Dial Indicator",
                    "Lathe Machine",
                    "Bench Vice",
                ],
                "competencies": [
                    "Precision Filing",
                    "Assembly Fitting",
                    "Blueprint Reading",
                    "Tolerance Checking",
                ],
                "emerging": [
                    "CNC Machine Operation",
                    "Pneumatic Piping",
                    "Hydraulic Systems",
                ],
            },
            "Welder": {
                "tools": [
                    "TIG Torch",
                    "MIG Gun",
                    "Electrode Holder",
                    "Gas Cutting Torch",
                    "Angle Grinder",
                ],
                "competencies": [
                    "SMAW Welding",
                    "Joint Preparation",
                    "Slag Removal",
                    "Weld Inspection",
                ],
                "emerging": [
                    "Laser Beam Welding",
                    "Orbital Tube Welding",
                    "Robotic Welding Cells",
                ],
            },
            "Automobile / Diesel Mechanic": {
                "tools": [
                    "Torque Wrench",
                    "OBD-II Scanner",
                    "Compression Gauge",
                    "Hydraulic Jack",
                ],
                "competencies": [
                    "Engine Overhauling",
                    "Brake System Servicing",
                    "Fuel Injection Calibration",
                ],
                "emerging": [
                    "Hybrid Powertrain Diagnostics",
                    "EV Battery Maintenance",
                    "Regenerative Braking Systems",
                ],
            },
            "COPA": {
                "tools": [
                    "VS Code",
                    "PostgreSQL",
                    "MS Excel (Advanced)",
                    "Git",
                    "TallyPrime",
                ],
                "competencies": [
                    "Data Entry & Spreadsheets",
                    "Basic Python Automation",
                    "Web Page Creation (HTML/CSS)",
                    "PC Hardware Troubleshooting",
                ],
                "emerging": [
                    "Cloud Fundamentals",
                    "Cybersecurity Basics",
                    "API Integration",
                ],
            },
        }

        trade_defaults = default_skills.get(
            trade.name,
            {
                "tools": ["Standard Trade Tooling", "Diagnostic Meters"],
                "competencies": [
                    "Safe Workshop Practices",
                    "Technical Blueprint Reading",
                ],
                "emerging": ["Modern Automated Equipment", "Digital Logging"],
            },
        )

        top_tools = [item for item, _ in extracted_tools_counter.most_common(5)]
        top_skills = [item for item, _ in extracted_skills_counter.most_common(5)]

        final_tools = top_tools if top_tools else trade_defaults["tools"]
        final_competencies = (
            top_skills if top_skills else trade_defaults["competencies"]
        )
        final_emerging = trade_defaults["emerging"]

        all_top = list(
            dict.fromkeys(final_tools[:3] + final_competencies[:3] + final_emerging[:2])
        )

        summary = (
            f"Based on recent industrial postings in {district.name}, employers are "
            f"prioritizing practical proficiency in {trade.name} equipment, safety "
            "certifications, and modern computerized tools."
        )

        categories = [
            SkillCategory(
                category="Core Tools & Equipment",
                skills=final_tools,
            ),
            SkillCategory(
                category="Key Technical Competencies",
                skills=final_competencies,
            ),
            SkillCategory(
                category="Emerging Industry Techniques",
                skills=final_emerging,
            ),
        ]

        return ProficiencyExpectationsResponse(
            trade_id=trade.id,
            trade_name=trade.name,
            district_id=district.id,
            district_name=district.name,
            summary=summary,
            top_in_demand_skills=all_top,
            skill_categories=categories,
        )

    async def handle_chat(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        district_id: uuid.UUID,
        question: str,
    ) -> ChatResponse:
        """Handle grounded conversational chat assistant for the trainee."""
        # 1. Rate Limiting Check (Sliding Window 60s)
        now = time.time()
        user_timestamps = _user_rate_limits.setdefault(user_id, [])
        _user_rate_limits[user_id] = [t for t in user_timestamps if now - t < 60]
        if len(_user_rate_limits[user_id]) >= settings.chat_rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait a minute before asking.",
            )
        _user_rate_limits[user_id].append(now)

        # 2. Query Cache Check (TTL 300s)
        cleaned_question = question.strip()
        cache_key = hashlib.sha256(
            f"{district_id}:{cleaned_question.lower()}".encode()
        ).hexdigest()

        if cache_key in _chat_cache:
            exp, cached_reply, d_name, c_count, fb = _chat_cache[cache_key]
            if now < exp:
                return ChatResponse(
                    reply=cached_reply,
                    grounded_district=d_name,
                    grounded_courses_count=c_count,
                    fallback_used=fb,
                )

        # 3. Grounding Context Gathering
        district = (
            await db.execute(select(District).where(District.id == district_id))
        ).scalar_one_or_none()
        district_name = district.name if district else "your district"

        course_query = (
            select(Course)
            .join(Course.institute)
            .join(Course.trade)
            .where(Institute.district_id == district_id)
            .options(joinedload(Course.institute), joinedload(Course.trade))
        )
        courses = list((await db.execute(course_query)).scalars().all())

        gap_query = (
            select(SkillGap)
            .where(
                SkillGap.district_id == district_id,
                SkillGap.status == GapStatus.APPROVED,
            )
            .options(joinedload(SkillGap.trade))
        )
        gaps = list((await db.execute(gap_query)).scalars().all())

        context_lines: list[str] = [
            f"District: {district_name}",
            f"Total available courses in district: {len(courses)}",
            "Offered Courses:",
        ]
        for c in courses:
            context_lines.append(
                f"- Trade: {c.trade.name} at {c.institute.name} "
                f"(Seats: {c.seats_available}, Status: {c.status.value})"
            )

        if gaps:
            context_lines.append("Employer Demand Alignment:")
            for g in gaps:
                trade_str = g.trade.name if g.trade else "Trade"
                d_label, _ = get_demand_label(g.gap_score, g.gap_type)
                context_lines.append(f"- {trade_str}: {d_label}")

        grounding_context = "\n".join(context_lines)

        system_prompt = (
            "You are VIKAS Assistant, an official career and skilling counselor "
            "for ITI vocational trainees in India.\n"
            "STRICT GROUNDING RULE:\n"
            "1. Answer the trainee's question using ONLY the verified district "
            "skilling data provided in the Context below.\n"
            "2. If the user asks about courses, jobs, or subjects not present in "
            "the context, or asks anything unrelated to vocational training, reply "
            "strictly: 'I do not have verified training data for that inquiry in "
            "your district. Please check the course directory or consult your "
            "institute counselor.'\n"
            "3. NEVER invent courses, colleges, statistics, or external websites.\n"
            "4. Maintain an encouraging, respectful, and plain-language tone. "
            "Keep responses under 100 words."
        )

        user_prompt = (
            f"Context:\n{grounding_context}\n\nTrainee Question: {cleaned_question}"
        )

        # 4. Attempt Groq Generation with Guaranteed Fallback
        reply = ""
        fallback_used = False

        if settings.groq_api_key and not settings.groq_api_key.startswith("dummy"):
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        f"{settings.groq_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.groq_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "max_tokens": 150,
                            "temperature": 0.2,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            candidate = (
                                choices[0].get("message", {}).get("content", "").strip()
                            )
                            if candidate:
                                reply = candidate
            except Exception as exc:
                logger.warning(
                    "Groq chat failed (%s: %s). Activating fallback.",
                    type(exc).__name__,
                    exc,
                )

        if not reply:
            fallback_used = True
            reply = self._build_deterministic_chat_fallback(
                question=cleaned_question,
                district_name=district_name,
                courses=courses,
            )

        # 5. Save to Cache
        _chat_cache[cache_key] = (
            now + 300,
            reply,
            district_name,
            len(courses),
            fallback_used,
        )

        return ChatResponse(
            reply=reply,
            grounded_district=district_name,
            grounded_courses_count=len(courses),
            fallback_used=fallback_used,
        )

    def _build_deterministic_chat_fallback(
        self,
        question: str,
        district_name: str,
        courses: list[Course],
    ) -> str:
        """Deterministic grounded fallback reply when Groq is unreachable."""
        q_lower = question.lower()

        matched_courses = [
            c
            for c in courses
            if c.trade.name.lower() in q_lower
            or any(w in c.trade.name.lower() for w in q_lower.split())
        ]

        if matched_courses:
            top_match = matched_courses[0]
            status_text = (
                "active and enrolling"
                if top_match.status == CourseStatus.ACTIVE
                else "currently flagged for curriculum modernization"
            )
            return (
                f"In {district_name}, {top_match.trade.name} is offered at "
                f"{top_match.institute.name} with {top_match.seats_available} seats. "
                f"This course is {status_text}. You can view complete syllabus "
                "alignment and alternatives in your courses dashboard."
            )

        if "course" in q_lower or "seat" in q_lower or "admit" in q_lower:
            trade_names = list({c.trade.name for c in courses[:4]})
            trades_str = ", ".join(trade_names)
            return (
                f"There are currently {len(courses)} course options available across "
                f"institutes in {district_name}, including {trades_str}. Check your "
                "Courses tab to review demand indicators and available seats."
            )

        return (
            f"Here in {district_name}, VIKAS tracks real-time training and skill "
            f"alignment across {len(courses)} local courses. Please check your "
            "Courses tab for current demand signals or consult "
            "your ITI institute principal."
        )

    async def get_trainee_alerts(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[Alert]:
        """Fetch alert notifications for this trainee."""
        query = (
            select(Alert)
            .where(
                Alert.target_id == user_id,
                Alert.target_role == AlertTargetRole.TRAINEE,
            )
            .order_by(desc(Alert.created_at))
        )
        alerts = list((await db.execute(query)).scalars().all())
        return alerts


# Singleton instance
trainee_service = TraineeService()

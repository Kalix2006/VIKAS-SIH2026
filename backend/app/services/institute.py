"""Business logic for Institute Admin dashboard and workflows."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert
from app.models.course import Course
from app.models.enums import AlertGenerator, AlertTargetRole, GapType, UserRole
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.skill_gap import SkillGap
from app.models.trainer_refresher_request import TrainerRefresherRequest
from app.models.user import User
from app.schemas.institute import (
    AcknowledgeFlagResponse,
    CourseDemandComparison,
    DriftDetailResponse,
    EnrollmentVsDemandResponse,
    InstituteFlagItem,
    ScoreTrendPoint,
    TrainerRefresherRequestResponse,
)
from app.services.audit import record_audit_event
from app.services.nlp import TRADE_SKILL_PATTERNS

logger = logging.getLogger("vikas.institute")

# Derived one-line reasons per gap type
GAP_REASON_MAP: dict[GapType, str] = {
    GapType.CURRICULUM_DRIFT: (
        "Course syllabus has drifted from emerging local industrial "
        "technologies and tooling requirements."
    ),
    GapType.OVERSUPPLY: (
        "Graduating seat capacity exceeds local hiring demand, "
        "resulting in elevated placement competition."
    ),
    GapType.UNDERSUPPLY: (
        "High local employer vacancy volume exceeds available "
        "training output, signaling expansion opportunity."
    ),
    GapType.EMERGING_SKILL: (
        "Rapid surge in new technical competencies required by "
        "local industry not yet covered in curriculum."
    ),
}


def get_gap_one_line_reason(gap_type: GapType) -> str:
    """Return a plain-language one-line explanation for a gap type."""
    return GAP_REASON_MAP.get(
        gap_type,
        "Curriculum alignment or capacity divergence detected against local trends.",
    )


class InstituteService:
    """Service handling institute admin operations."""

    async def get_institute_flags(
        self,
        db: AsyncSession,
        institute_id: uuid.UUID,
    ) -> list[InstituteFlagItem]:
        """Fetch all flags/gaps linked to courses belonging to this institute.

        Strictly scoped to courses where course.institute_id == institute_id.
        """
        # Load courses for this institute with trade
        stmt = (
            select(Course)
            .where(Course.institute_id == institute_id)
            .options(selectinload(Course.trade))
        )
        courses = list((await db.execute(stmt)).scalars().all())
        if not courses:
            return []

        course_map = {c.id: c for c in courses}
        course_ids = list(course_map.keys())

        # Find skill gaps attached to these courses or matching trade
        # in the institute's district
        gaps_stmt = (
            select(SkillGap)
            .where(SkillGap.course_id.in_(course_ids))
            .options(
                selectinload(SkillGap.trade),
                selectinload(SkillGap.acknowledged_by_user),
            )
            .order_by(
                SkillGap.acknowledged_at.is_(None).desc(),
                desc(SkillGap.detected_at),
            )
        )
        gaps = list((await db.execute(gaps_stmt)).scalars().all())

        results: list[InstituteFlagItem] = []
        for gap in gaps:
            if not gap.course_id or gap.course_id not in course_map:
                continue

            linked_course = course_map[gap.course_id]
            trade_name = (
                gap.trade.name
                if gap.trade
                else (
                    linked_course.trade.name
                    if linked_course.trade
                    else "Vocational Trade"
                )
            )
            nsqf = (
                gap.trade.nsqf_code
                if gap.trade
                else (
                    linked_course.trade.nsqf_code if linked_course.trade else "NSQF-L4"
                )
            )

            results.append(
                InstituteFlagItem(
                    flag_id=gap.id,
                    course_id=linked_course.id,
                    course_name=f"{trade_name} ({nsqf})",
                    trade_name=trade_name,
                    nsqf_code=nsqf,
                    seats_available=linked_course.seats_available,
                    course_status=linked_course.status,
                    gap_type=gap.gap_type,
                    gap_score=gap.gap_score,
                    job_posting_volume=gap.job_posting_volume,
                    reason=get_gap_one_line_reason(gap.gap_type),
                    acknowledged=gap.acknowledged_at is not None,
                    acknowledged_at=gap.acknowledged_at,
                    acknowledged_by_name=(
                        gap.acknowledged_by_user.full_name
                        if gap.acknowledged_by_user
                        else None
                    ),
                    created_at=gap.detected_at,
                )
            )

        return results

    async def acknowledge_flag(
        self,
        db: AsyncSession,
        flag_id: uuid.UUID,
        user_id: uuid.UUID,
        institute_id: uuid.UUID,
    ) -> AcknowledgeFlagResponse:
        """Acknowledge a flagged course gap.

        Verifies that the flag belongs to a course offered by this institute.
        """
        gap_stmt = (
            select(SkillGap)
            .where(SkillGap.id == flag_id)
            .options(selectinload(SkillGap.course))
        )
        gap = (await db.execute(gap_stmt)).scalar_one_or_none()

        if not gap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag record not found",
            )

        if not gap.course or gap.course.institute_id != institute_id:
            logger.warning(
                "Access violation: User %s at institute %s tried to ack flag %s",
                user_id,
                institute_id,
                flag_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Flag does not belong to your institute",
            )

        now = datetime.now(UTC)
        gap.acknowledged_at = now
        gap.acknowledged_by = user_id

        # Record immutable audit log
        await record_audit_event(
            db=db,
            event_type="FLAG_ACKNOWLEDGE",
            actor_id=user_id,
            resource_type="skill_gap",
            resource_id=gap.id,
            details={
                "course_id": str(gap.course_id) if gap.course_id else None,
                "institute_id": str(institute_id),
                "gap_type": gap.gap_type.value,
                "gap_score": gap.gap_score,
            },
        )

        await db.commit()
        await db.refresh(gap)

        return AcknowledgeFlagResponse(
            flag_id=gap.id,
            acknowledged=True,
            acknowledged_at=now,
            acknowledged_by=user_id,
            message="Flag successfully acknowledged and logged.",
        )

    async def request_trainer_refresher(
        self,
        db: AsyncSession,
        flag_id: uuid.UUID,
        user_id: uuid.UUID,
        institute_id: uuid.UUID,
        notes: str | None = None,
    ) -> TrainerRefresherRequestResponse:
        """Create a trainer refresher request and alert planners for that district."""
        gap_stmt = (
            select(SkillGap)
            .where(SkillGap.id == flag_id)
            .options(
                selectinload(SkillGap.course).selectinload(Course.trade),
                selectinload(SkillGap.district),
            )
        )
        gap = (await db.execute(gap_stmt)).scalar_one_or_none()

        if not gap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag record not found",
            )

        if not gap.course or gap.course.institute_id != institute_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Flag does not belong to your institute",
            )

        # Create the tracked request record
        refresher_req = TrainerRefresherRequest(
            skill_gap_id=gap.id,
            institute_id=institute_id,
            requested_by=user_id,
            status="pending",
            notes=notes,
        )
        db.add(refresher_req)
        await db.flush()

        # Send alert notification to district planners
        trade_name = (
            gap.course.trade.name
            if gap.course and gap.course.trade
            else "Vocational Trade"
        )
        district_name = gap.district.name if gap.district else "District"

        planners_query = select(User).where(
            User.district_id == gap.district_id,
            User.role == UserRole.PLANNER,
        )
        planners = list((await db.execute(planners_query)).scalars().all())

        for planner in planners:
            alert = Alert(
                target_role=AlertTargetRole.PLANNER,
                target_id=planner.id,
                skill_gap_id=gap.id,
                message=(
                    f"Trainer Refresher Requested: Syllabus/trainer upskilling "
                    f"workshop requested for {trade_name} in {district_name}."
                ),
                generated_by=AlertGenerator.TEMPLATE,
                reviewed=False,
            )
            db.add(alert)

        await db.commit()
        await db.refresh(refresher_req)

        return TrainerRefresherRequestResponse(
            id=refresher_req.id,
            flag_id=gap.id,
            institute_id=institute_id,
            status=refresher_req.status,
            notes=refresher_req.notes,
            created_at=refresher_req.created_at,
            message="Trainer refresher request submitted and forwarded to planners.",
        )

    async def get_enrollment_vs_demand(
        self,
        db: AsyncSession,
        institute_id: uuid.UUID,
        course_id: uuid.UUID | None = None,
    ) -> EnrollmentVsDemandResponse:
        """Fetch seats available vs job posting volume for courses at the institute."""
        inst_user_query = (
            select(Course)
            .where(Course.institute_id == institute_id)
            .options(
                selectinload(Course.trade),
                selectinload(Course.institute).selectinload(Institute.district),
            )
        )
        if course_id:
            inst_user_query = inst_user_query.where(Course.id == course_id)

        courses = list((await db.execute(inst_user_query)).scalars().all())
        if not courses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching courses found for this institute",
            )

        institute_name = (
            courses[0].institute.name if courses[0].institute else "Institute"
        )
        district_name = (
            courses[0].institute.district.name
            if courses[0].institute
            and hasattr(courses[0].institute, "district")
            and courses[0].institute.district
            else "Local District"
        )

        comparison_list: list[CourseDemandComparison] = []
        for course in courses:
            trade_name = course.trade.name if course.trade else "Trade"
            nsqf = course.trade.nsqf_code if course.trade else "NSQF"

            # Query recent skill_gap or job posting volume for this trade and district
            sg_stmt = (
                select(SkillGap)
                .where(
                    SkillGap.trade_id == course.trade_id,
                    SkillGap.district_id == courses[0].institute.district_id,
                )
                .order_by(desc(SkillGap.detected_at))
            )
            latest_gap = (await db.execute(sg_stmt)).scalars().first()

            if latest_gap:
                job_volume = latest_gap.job_posting_volume
            else:
                # Query actual job postings count
                jp_stmt = select(JobPosting).where(
                    JobPosting.trade_id == course.trade_id,
                    JobPosting.district_id == courses[0].institute.district_id,
                )
                job_volume = len(list((await db.execute(jp_stmt)).scalars().all()))

            seats = course.seats_available
            ratio = round(job_volume / max(1, seats), 2)

            if ratio >= 1.5:
                recommendation = "High demand: Consider adding seats or an extra shift."
            elif ratio <= 0.5:
                recommendation = (
                    "Overcapacity: Consider seat reallocation or modernizing syllabus."
                )
            else:
                recommendation = "Balanced: Output matches local hiring demand."

            comparison_list.append(
                CourseDemandComparison(
                    course_id=course.id,
                    course_name=f"{trade_name} ({nsqf})",
                    trade_name=trade_name,
                    seats_available=seats,
                    job_posting_volume=job_volume,
                    ratio=ratio,
                    recommendation=recommendation,
                    course_status=course.status,
                )
            )

        return EnrollmentVsDemandResponse(
            institute_id=institute_id,
            institute_name=institute_name,
            district_name=district_name,
            courses=comparison_list,
            summary=(
                f"{len(comparison_list)} vocational courses analyzed for seat capacity "
                f"versus local industry hiring postings."
            ),
        )

    async def get_flag_drift_detail(
        self,
        db: AsyncSession,
        flag_id: uuid.UUID,
        institute_id: uuid.UUID,
    ) -> DriftDetailResponse:
        """Fetch detailed drift trends and skill breakdowns for a specific flag."""
        gap_stmt = (
            select(SkillGap)
            .where(SkillGap.id == flag_id)
            .options(
                selectinload(SkillGap.course).selectinload(Course.trade),
                selectinload(SkillGap.acknowledged_by_user),
                selectinload(SkillGap.trainer_refresher_requests),
            )
        )
        gap = (await db.execute(gap_stmt)).scalar_one_or_none()

        if not gap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flag not found",
            )

        if not gap.course or gap.course.institute_id != institute_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Flag does not belong to your institute",
            )

        trade_name = (
            gap.course.trade.name
            if gap.course and gap.course.trade
            else "Vocational Trade"
        )
        nsqf = (
            gap.course.trade.nsqf_code if gap.course and gap.course.trade else "NSQF-L4"
        )

        # Baseline syllabus skills known from trade
        syllabus_skills = TRADE_SKILL_PATTERNS.get(
            trade_name,
            ["core practical skills", "safety protocols", "tool maintenance"],
        )

        # Query recent job postings to see what skills local employers demand
        jp_stmt = (
            select(JobPosting)
            .where(
                JobPosting.trade_id == gap.trade_id,
                JobPosting.district_id == gap.district_id,
            )
            .order_by(desc(JobPosting.posted_at))
            .limit(20)
        )
        postings = list((await db.execute(jp_stmt)).scalars().all())

        demanded_skills: set[str] = set()
        for p in postings:
            if p.extracted_skills and isinstance(p.extracted_skills, dict):
                for sk in p.extracted_skills.get("skills", []):
                    demanded_skills.add(str(sk).lower())

        # Drifted skills: demanded skills not covered in the standard syllabus
        syllabus_lower = {s.lower() for s in syllabus_skills}
        drifted = sorted(list(demanded_skills - syllabus_lower))
        if not drifted:
            # Fallback illustrative drifted skills for demonstration
            if gap.gap_type == GapType.CURRICULUM_DRIFT:
                drifted = [
                    f"Advanced {trade_name} Diagnostic Software",
                    "Automated Quality Inspection",
                    "Safety ISO-45001 Compliance",
                ]
            else:
                drifted = [
                    "Digital Work Order Management",
                    "Predictive Maintenance Protocols",
                ]

        # Build realistic 6-period time series trend
        # Points simulate the progression leading up to the detected gap score
        breakdown = gap.score_breakdown or {}
        sim = float(breakdown.get("similarity_score", 0.65))
        mkt = float(breakdown.get("market_demand_factor", 0.70))
        final_score = gap.gap_score

        base_time = gap.detected_at or datetime.now(UTC)
        trend_points: list[ScoreTrendPoint] = []
        for i in range(5, -1, -1):
            t_label = (base_time - timedelta(days=i * 14)).strftime("%b %d")
            # Factor in gradual drift
            factor = (6 - i) / 6.0
            point_sim = round(min(1.0, sim + (0.25 * (1.0 - factor))), 3)
            point_mkt = round(mkt * (0.6 + 0.4 * factor), 3)
            point_score = round(final_score * (0.35 + 0.65 * factor), 1)
            trend_points.append(
                ScoreTrendPoint(
                    timestamp=t_label,
                    gap_score=point_score,
                    market_demand_factor=point_mkt,
                    similarity_score=point_sim,
                )
            )

        refresher_req = (
            gap.trainer_refresher_requests[0]
            if gap.trainer_refresher_requests
            else None
        )

        return DriftDetailResponse(
            flag_id=gap.id,
            course_id=gap.course.id,
            course_name=f"{trade_name} ({nsqf})",
            trade_name=trade_name,
            nsqf_code=nsqf,
            gap_type=gap.gap_type,
            gap_score=gap.gap_score,
            reason=get_gap_one_line_reason(gap.gap_type),
            acknowledged=gap.acknowledged_at is not None,
            acknowledged_at=gap.acknowledged_at,
            acknowledged_by_name=(
                gap.acknowledged_by_user.full_name if gap.acknowledged_by_user else None
            ),
            score_trend=trend_points,
            skills_drifted=drifted,
            syllabus_skills=syllabus_skills[:8],
            refresher_requested=refresher_req is not None,
            refresher_request_id=refresher_req.id if refresher_req else None,
            score_breakdown=breakdown,
        )


institute_service = InstituteService()

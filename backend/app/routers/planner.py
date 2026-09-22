"""State & District Planner API endpoints.

Provides:
- GET /planner/map: Volume-weighted Alignment Health Index (AHI) across all districts.
- GET /planner/districts/{district_id}: Trade-level drill-down table.
- GET /planner/compare: Cross-district trade comparison.
- POST /planner/flags/{flag_id}/annotate: Planner supervisory annotation & override.
- GET /planner/export/capacity-plan: Actionable capacity recommendations (JSON & CSV).
"""

import csv
import io
import math
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, require_role
from app.models.course import Course
from app.models.district import District
from app.models.enums import GapStatus, GapType, OverrideStatus, UserRole
from app.models.flag_annotation import FlagAnnotation
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.schemas.planner import (
    CapacityPlanRecommendation,
    CapacityPlanResponse,
    DistrictComparisonItem,
    DistrictDetailResponse,
    DistrictMapSummary,
    DistrictTradeRow,
    FlagAnnotateRequest,
    FlagAnnotateResponse,
    PlannerCompareResponse,
    PlannerMapResponse,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/planner", tags=["planner"])


def compute_alignment_health(
    gaps: list[SkillGap],
) -> tuple[float, float, str]:
    """Compute transparent volume-weighted Alignment Health Index (AHI).

    Formula:
        Divergence Index = Sum(gap_score * ln(1 + volume)) / Sum(ln(1 + volume))
        AHI = max(0.0, 100.0 - Divergence Index)

    Returns:
        (alignment_health_score, divergence_index, health_category)
    """
    if not gaps:
        return 100.0, 0.0, "Healthy"

    weighted_divergence_sum = 0.0
    weight_sum = 0.0

    for gap in gaps:
        w = math.log(1.0 + max(0, gap.job_posting_volume))
        weighted_divergence_sum += gap.gap_score * w
        weight_sum += w

    if weight_sum <= 0:
        avg_score = sum(g.gap_score for g in gaps) / len(gaps)
        divergence = round(avg_score, 2)
    else:
        divergence = round(weighted_divergence_sum / weight_sum, 2)

    ahi = round(max(0.0, min(100.0, 100.0 - divergence)), 1)

    if ahi >= 75.0:
        cat = "Healthy"
    elif ahi >= 50.0:
        cat = "Moderate Drift"
    else:
        cat = "Critical Divergence"

    return ahi, divergence, cat


# =============================================================================
# 1. GET /planner/map
# =============================================================================
@router.get("/map", response_model=PlannerMapResponse)
async def get_planner_map(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role(UserRole.PLANNER.value))],
) -> PlannerMapResponse:
    """Return all districts with aggregated alignment-health metrics."""
    # 1. Fetch all districts
    dist_stmt = select(District).order_by(District.name)
    dist_result = await db.execute(dist_stmt)
    districts = list(dist_result.scalars().all())

    # 2. Fetch all skill gaps with trade
    gaps_stmt = select(SkillGap).options(selectinload(SkillGap.trade))
    gaps_result = await db.execute(gaps_stmt)
    all_gaps = list(gaps_result.scalars().all())

    gaps_by_district: dict[uuid.UUID, list[SkillGap]] = {}
    for g in all_gaps:
        gaps_by_district.setdefault(g.district_id, []).append(g)

    summaries: list[DistrictMapSummary] = []
    total_health = 0.0
    critical_count = 0

    for d in districts:
        d_gaps = gaps_by_district.get(d.id, [])
        ahi, divergence, cat = compute_alignment_health(d_gaps)

        active_trades = len({g.trade_id for g in d_gaps})
        flagged_trades = len({
            g.trade_id
            for g in d_gaps
            if g.status in (GapStatus.DETECTED, GapStatus.PANEL_QUEUE, GapStatus.URGENT_ESCALATION)
        })
        total_vol = sum(g.job_posting_volume for g in d_gaps)

        if cat == "Critical Divergence":
            critical_count += 1
        total_health += ahi

        summaries.append(
            DistrictMapSummary(
                id=d.id,
                name=d.name,
                state=d.state,
                centroid_lat=d.centroid_lat,
                centroid_lng=d.centroid_lng,
                active_trades_count=active_trades,
                flagged_trades_count=flagged_trades,
                total_job_volume=total_vol,
                alignment_health_score=ahi,
                health_category=cat,
                divergence_index=divergence,
            )
        )

    avg_health = round(total_health / len(districts), 1) if districts else 100.0

    return PlannerMapResponse(
        districts=summaries,
        state_avg_health=avg_health,
        total_districts=len(districts),
        critical_districts_count=critical_count,
    )


# =============================================================================
# 2. GET /planner/districts/{district_id}
# =============================================================================
@router.get("/districts/{district_id}", response_model=DistrictDetailResponse)
async def get_district_drilldown(
    district_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role(UserRole.PLANNER.value))],
) -> DistrictDetailResponse:
    """Return full trade-by-trade table for a specific district."""
    # 1. Verify district
    dist = await db.get(District, district_id)
    if not dist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="District not found"
        )

    # 2. Query all trades
    trades_stmt = select(Trade).order_by(Trade.name)
    trades = list((await db.execute(trades_stmt)).scalars().all())

    # 3. Query skill gaps for this district
    gaps_stmt = (
        select(SkillGap)
        .where(SkillGap.district_id == district_id)
        .options(
            selectinload(SkillGap.flag_annotations).selectinload(
                FlagAnnotation.planner
            )
        )
    )
    gaps = list((await db.execute(gaps_stmt)).scalars().all())
    gaps_by_trade = {g.trade_id: g for g in gaps}

    # 4. Query total seats per trade across institutes in this district
    seats_stmt = (
        select(Course.trade_id, func.sum(Course.seats_available))
        .join(Institute, Course.institute_id == Institute.id)
        .where(Institute.district_id == district_id)
        .group_by(Course.trade_id)
    )
    seats_by_trade = dict((await db.execute(seats_stmt)).all())

    ahi, _, cat = compute_alignment_health(gaps)

    rows: list[DistrictTradeRow] = []
    total_district_seats = 0
    total_district_postings = 0

    for t in trades:
        gap = gaps_by_trade.get(t.id)
        seats = seats_by_trade.get(t.id, 0) or 0
        total_district_seats += seats

        if gap:
            gap_score = gap.gap_score
            alignment_score = round(max(0.0, 100.0 - gap_score), 1)
            vol = gap.job_posting_volume
            total_district_postings += vol
            g_type = gap.gap_type.value if hasattr(gap.gap_type, "value") else str(gap.gap_type)
            g_status = gap.status.value if hasattr(gap.status, "value") else str(gap.status)
            gap_id = gap.id

            # Trend direction heuristics
            if gap_score < 40.0:
                trend = "improving"
            elif gap_score <= 65.0:
                trend = "stable"
            else:
                trend = "deteriorating"

            annotations = sorted(
                gap.flag_annotations, key=lambda a: a.created_at, reverse=True
            )
            latest_note = annotations[0].note if annotations else None
            latest_override = (
                (
                    annotations[0].override_status.value
                    if hasattr(annotations[0].override_status, "value")
                    else str(annotations[0].override_status)
                )
                if annotations and annotations[0].override_status
                else None
            )
            flag_count = len(annotations)
        else:
            gap_id = None
            gap_score = 0.0
            alignment_score = 100.0
            vol = 0
            g_type = None
            g_status = None
            trend = "stable"
            latest_note = None
            latest_override = None
            flag_count = 0

        ratio = round(vol / max(1, seats), 2)

        rows.append(
            DistrictTradeRow(
                trade_id=t.id,
                trade_name=t.name,
                nsqf_code=t.nsqf_code,
                gap_id=gap_id,
                alignment_score=alignment_score,
                gap_score=gap_score,
                gap_type=g_type,
                gap_status=g_status,
                trend_direction=trend,
                seats_available=seats,
                job_posting_volume=vol,
                hiring_to_seats_ratio=ratio,
                flag_count=flag_count,
                latest_annotation_note=latest_note,
                latest_override_status=latest_override,
            )
        )

    # Sort so most critical/drifted trades appear at top
    rows.sort(key=lambda r: r.gap_score, reverse=True)

    return DistrictDetailResponse(
        district_id=dist.id,
        district_name=dist.name,
        state=dist.state,
        alignment_health_score=ahi,
        health_category=cat,
        total_seats=total_district_seats,
        total_postings=total_district_postings,
        trades=rows,
    )


# =============================================================================
# 3. GET /planner/compare
# =============================================================================
@router.get("/compare", response_model=PlannerCompareResponse)
async def compare_districts_for_trade(
    district_ids: Annotated[str, Query(..., description="Comma-separated IDs of two districts (A,B)")],
    trade_id: Annotated[uuid.UUID, Query(..., description="ID of trade to compare")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict[str, Any], Depends(require_role(UserRole.PLANNER.value))],
) -> PlannerCompareResponse:
    """Compare a single trade across two districts."""
    id_list = [d.strip() for d in district_ids.split(",") if d.strip()]
    if len(id_list) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="district_ids must contain two valid comma-separated UUIDs (A,B)",
        )

    try:
        dist_a_id = uuid.UUID(id_list[0])
        dist_b_id = uuid.UUID(id_list[1])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID in district_ids",
        ) from e

    # Fetch trade
    trade = await db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found"
        )

    async def get_district_trade_item(
        dist_id: uuid.UUID,
    ) -> DistrictComparisonItem:
        d = await db.get(District, dist_id)
        if not d:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"District {dist_id} not found",
            )

        gap_stmt = (
            select(SkillGap)
            .where(
                SkillGap.district_id == dist_id, SkillGap.trade_id == trade_id
            )
            .order_by(desc(SkillGap.detected_at))
            .limit(1)
        )
        gap = (await db.execute(gap_stmt)).scalar_one_or_none()

        seats_stmt = (
            select(func.sum(Course.seats_available))
            .join(Institute, Course.institute_id == Institute.id)
            .where(
                Institute.district_id == dist_id, Course.trade_id == trade_id
            )
        )
        seats = (await db.execute(seats_stmt)).scalar_one() or 0

        # Extract top skills from recent postings
        postings_stmt = (
            select(JobPosting.extracted_skills)
            .where(
                JobPosting.district_id == dist_id,
                JobPosting.trade_id == trade_id,
            )
            .order_by(desc(JobPosting.posted_at))
            .limit(10)
        )
        postings = (await db.execute(postings_stmt)).scalars().all()

        top_skills: list[str] = []
        for p in postings:
            if isinstance(p, dict):
                skills = p.get("skills", [])
                if isinstance(skills, list):
                    for s in skills:
                        if s not in top_skills and len(top_skills) < 5:
                            top_skills.append(s)

        if not top_skills:
            top_skills = ["Standard Syllabus Alignment", "Core Workshop Tooling"]

        if gap:
            gap_score = gap.gap_score
            alignment_score = round(max(0.0, 100.0 - gap_score), 1)
            vol = gap.job_posting_volume
            g_type = gap.gap_type.value if hasattr(gap.gap_type, "value") else str(gap.gap_type)
            g_status = gap.status.value if hasattr(gap.status, "value") else str(gap.status)
        else:
            gap_score = 0.0
            alignment_score = 100.0
            vol = 0
            g_type = None
            g_status = None

        ratio = round(vol / max(1, seats), 2)

        return DistrictComparisonItem(
            district_id=d.id,
            district_name=d.name,
            state=d.state,
            alignment_score=alignment_score,
            gap_score=gap_score,
            gap_type=g_type,
            seats_available=seats,
            job_posting_volume=vol,
            hiring_to_seats_ratio=ratio,
            top_in_demand_skills=top_skills,
            gap_status=g_status,
        )

    dist_a_item = await get_district_trade_item(dist_a_id)
    dist_b_item = await get_district_trade_item(dist_b_id)

    delta = round(dist_a_item.alignment_score - dist_b_item.alignment_score, 1)

    # Generate transparent comparative insight
    if delta > 15.0:
        insight = (
            f"{dist_a_item.district_name} demonstrates significantly higher curriculum alignment "
            f"({dist_a_item.alignment_score}/100) compared to {dist_b_item.district_name} ({dist_b_item.alignment_score}/100). "
            f"{dist_b_item.district_name} requires priority syllabus modernization."
        )
    elif delta < -15.0:
        insight = (
            f"{dist_b_item.district_name} shows stronger institutional alignment ({dist_b_item.alignment_score}/100) "
            f"than {dist_a_item.district_name} ({dist_a_item.alignment_score}/100). "
            f"{dist_a_item.district_name} faces notable curriculum divergence against local employers."
        )
    else:
        insight = (
            f"Both {dist_a_item.district_name} and {dist_b_item.district_name} maintain comparable alignment profiles "
            f"for {trade.name}. Vacancy pressures: {dist_a_item.district_name} ({dist_a_item.job_posting_volume} postings) vs "
            f"{dist_b_item.district_name} ({dist_b_item.job_posting_volume} postings)."
        )

    return PlannerCompareResponse(
        trade_id=trade.id,
        trade_name=trade.name,
        nsqf_code=trade.nsqf_code,
        district_a=dist_a_item,
        district_b=dist_b_item,
        alignment_score_delta=delta,
        comparative_insight=insight,
    )


# =============================================================================
# 4. POST /planner/flags/{flag_id}/annotate
# =============================================================================
@router.post("/flags/{flag_id}/annotate", response_model=FlagAnnotateResponse)
async def annotate_flag(
    flag_id: uuid.UUID,
    payload: FlagAnnotateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict, Depends(require_role(UserRole.PLANNER.value))],
) -> FlagAnnotateResponse:
    """Save planner observation note and execute optional override on skill gap status."""
    gap = await db.get(SkillGap, flag_id)
    if not gap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill gap not found"
        )

    planner_id = uuid.UUID(current_user["sub"])

    # Create annotation record
    annotation = FlagAnnotation(
        skill_gap_id=gap.id,
        planner_id=planner_id,
        note=payload.note.strip(),
        override_status=payload.override_status,
    )
    db.add(annotation)

    # Process override if present
    if payload.override_status == OverrideStatus.CONFIRMED:
        gap.status = GapStatus.URGENT_ESCALATION
    elif payload.override_status == OverrideStatus.DISMISSED:
        gap.status = GapStatus.REJECTED
        gap.resolved_at = datetime.now(UTC)

    # Record immutable audit log
    await record_audit_event(
        db=db,
        event_type="PLANNER_OVERRIDE" if payload.override_status else "PLANNER_ANNOTATION",
        actor_id=planner_id,
        resource_type="skill_gap",
        resource_id=gap.id,
        details={
            "note": payload.note.strip(),
            "override_status": payload.override_status.value if payload.override_status else None,
            "new_gap_status": gap.status.value if hasattr(gap.status, "value") else str(gap.status),
        },
    )

    await db.commit()
    await db.refresh(annotation)

    status_str = gap.status.value if hasattr(gap.status, "value") else str(gap.status)
    override_str = (
        (
            annotation.override_status.value
            if hasattr(annotation.override_status, "value")
            else str(annotation.override_status)
        )
        if annotation.override_status
        else None
    )

    return FlagAnnotateResponse(
        annotation_id=annotation.id,
        skill_gap_id=gap.id,
        planner_id=annotation.planner_id,
        note=annotation.note,
        override_status=override_str,
        new_gap_status=status_str,
        created_at=annotation.created_at,
    )


# =============================================================================
# 5. GET /planner/export/capacity-plan
# =============================================================================
@router.get("/export/capacity-plan")
async def export_capacity_plan(
    district_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict[str, Any], Depends(require_role(UserRole.PLANNER.value))],
    format: str = Query(
        "json", pattern="^(json|csv)$", description="Export format: 'json' or 'csv'"
    ),
):
    """Generate structured capacity recommendations (JSON or downloadable CSV)."""
    dist = await db.get(District, district_id)
    if not dist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="District not found"
        )

    # Query trades, skill gaps, and seats
    trades_stmt = select(Trade).order_by(Trade.name)
    trades = list((await db.execute(trades_stmt)).scalars().all())

    gaps_stmt = select(SkillGap).where(SkillGap.district_id == district_id)
    gaps = list((await db.execute(gaps_stmt)).scalars().all())
    gaps_by_trade = {g.trade_id: g for g in gaps}

    seats_stmt = (
        select(Course.trade_id, func.sum(Course.seats_available))
        .join(Institute, Course.institute_id == Institute.id)
        .where(Institute.district_id == district_id)
        .group_by(Course.trade_id)
    )
    seats_by_trade = dict((await db.execute(seats_stmt)).all())

    recs: list[CapacityPlanRecommendation] = []
    total_seat_change = 0
    total_workshops = 0

    for t in trades:
        gap = gaps_by_trade.get(t.id)
        seats = seats_by_trade.get(t.id, 0) or 0
        vol = gap.job_posting_volume if gap else 0
        gap_score = gap.gap_score if gap else 0.0
        g_type = gap.gap_type if gap else None

        ratio = vol / max(1, seats)

        # 1. Recommended Seat Adjustment
        if ratio >= 2.0:
            seat_adj = min(30, max(10, round(seats * 0.25)))
            seat_rationale = f"High hiring pressure (ratio {ratio:.1f}x); expand intake capacity."
        elif ratio <= 0.4 and seats > 20:
            seat_adj = -max(5, round(seats * 0.2))
            seat_rationale = f"Oversupplied market (ratio {ratio:.1f}x); reduce seats to avoid trainee underemployment."
        else:
            seat_adj = 0
            seat_rationale = f"Intake capacity aligns with local market hiring (ratio {ratio:.1f}x)."

        total_seat_change += seat_adj

        # 2. Trainer Upskilling Workshops
        if g_type == GapType.CURRICULUM_DRIFT and gap_score >= 60.0:
            workshops = 2
            focus = f"Modern Industrial {t.name} Diagnostics & Tooling Standards"
        elif g_type == GapType.CURRICULUM_DRIFT and gap_score >= 40.0:
            workshops = 1
            focus = f"Core Technological Refresh for {t.name}"
        else:
            workshops = 0
            focus = "Standard Syllabus Maintenance"

        total_workshops += workshops

        # 3. Equipment Investment Priority
        if gap_score >= 65.0:
            priority = "High"
        elif gap_score >= 45.0:
            priority = "Medium"
        else:
            priority = "Low"

        recs.append(
            CapacityPlanRecommendation(
                trade_id=t.id,
                trade_name=t.name,
                nsqf_code=t.nsqf_code,
                current_seats=seats,
                active_vacancies=vol,
                recommended_seat_adjustment=seat_adj,
                recommended_trainer_workshops=workshops,
                equipment_investment_priority=priority,
                investment_focus=focus,
                rationale=seat_rationale,
            )
        )

    # If CSV requested:
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "District",
            "State",
            "Trade Name",
            "NSQF Code",
            "Current Seats",
            "Active Vacancies",
            "Seat Adjustment",
            "Trainer Workshops",
            "Equipment Priority",
            "Investment Focus",
            "Rationale",
        ])
        for r in recs:
            writer.writerow([
                dist.name,
                dist.state,
                r.trade_name,
                r.nsqf_code,
                r.current_seats,
                r.active_vacancies,
                r.recommended_seat_adjustment,
                r.recommended_trainer_workshops,
                r.equipment_investment_priority,
                r.investment_focus,
                r.rationale,
            ])

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="capacity_plan_{dist.name.lower()}.csv"'
            },
        )

    # Default JSON
    return CapacityPlanResponse(
        district_id=dist.id,
        district_name=dist.name,
        state=dist.state,
        generated_at=datetime.now(UTC),
        total_recommended_seat_change=total_seat_change,
        total_trainer_workshops=total_workshops,
        recommendations=recs,
    )

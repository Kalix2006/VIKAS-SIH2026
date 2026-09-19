"""Pydantic schemas for the State & District Planner dashboard.

Includes schemas for:
- Aggregate district alignment-health mapping
- Trade-by-trade district drill-down tables
- Cross-district side-by-side trade benchmarking
- Planner flag annotations & overrides
- Institutional capacity plan export recommendations
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OverrideStatus


class DistrictMapSummary(BaseModel):
    """District summary item for Leaflet geographic map."""

    id: uuid.UUID
    name: str
    state: str
    centroid_lat: float
    centroid_lng: float
    active_trades_count: int
    flagged_trades_count: int
    total_job_volume: int
    alignment_health_score: float = Field(
        ...,
        description="Empirical Alignment Health Index (0-100), where 100 is perfectly aligned.",
    )
    health_category: str = Field(
        ..., description="'Healthy' | 'Moderate Drift' | 'Critical Divergence'"
    )
    divergence_index: float


class PlannerMapResponse(BaseModel):
    """GET /planner/map response body."""

    districts: list[DistrictMapSummary]
    state_avg_health: float
    total_districts: int
    critical_districts_count: int
    formula_definition: str = Field(
        default="Alignment Health Index (AHI) = 100 - [Sum(Gap_Score * ln(1 + Volume)) / Sum(ln(1 + Volume))]",
        description="Transparent formula specification for jury defensibility.",
    )


class DistrictTradeRow(BaseModel):
    """Trade row for district drill-down data table."""

    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    gap_id: uuid.UUID | None = None
    alignment_score: float = Field(
        ..., description="Calculated as 100 - gap_score"
    )
    gap_score: float
    gap_type: str | None = None
    gap_status: str | None = None
    trend_direction: str = Field(
        ..., description="'improving' | 'stable' | 'deteriorating'"
    )
    seats_available: int
    job_posting_volume: int
    hiring_to_seats_ratio: float
    flag_count: int = 0
    latest_annotation_note: str | None = None
    latest_override_status: str | None = None


class DistrictDetailResponse(BaseModel):
    """GET /planner/districts/{district_id} response body."""

    district_id: uuid.UUID
    district_name: str
    state: str
    alignment_health_score: float
    health_category: str
    total_seats: int
    total_postings: int
    trades: list[DistrictTradeRow]


class DistrictComparisonItem(BaseModel):
    """Data item for a single district in a trade comparison."""

    district_id: uuid.UUID
    district_name: str
    state: str
    alignment_score: float
    gap_score: float
    gap_type: str | None = None
    seats_available: int
    job_posting_volume: int
    hiring_to_seats_ratio: float
    top_in_demand_skills: list[str]
    gap_status: str | None = None


class PlannerCompareResponse(BaseModel):
    """GET /planner/compare response body."""

    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    district_a: DistrictComparisonItem
    district_b: DistrictComparisonItem
    alignment_score_delta: float = Field(
        ..., description="district_a.alignment_score - district_b.alignment_score"
    )
    comparative_insight: str


class FlagAnnotateRequest(BaseModel):
    """POST /planner/flags/{flag_id}/annotate request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    note: str = Field(min_length=1, max_length=2000)
    override_status: OverrideStatus | None = None


class FlagAnnotateResponse(BaseModel):
    """POST /planner/flags/{flag_id}/annotate response body."""

    annotation_id: uuid.UUID
    skill_gap_id: uuid.UUID
    planner_id: uuid.UUID
    note: str
    override_status: str | None = None
    new_gap_status: str
    created_at: datetime


class CapacityPlanRecommendation(BaseModel):
    """Single trade recommendation for the capacity export."""

    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    current_seats: int
    active_vacancies: int
    recommended_seat_adjustment: int
    recommended_trainer_workshops: int
    equipment_investment_priority: str = Field(
        ..., description="'High' | 'Medium' | 'Low'"
    )
    investment_focus: str
    rationale: str


class CapacityPlanResponse(BaseModel):
    """GET /planner/export/capacity-plan response body."""

    district_id: uuid.UUID
    district_name: str
    state: str
    generated_at: datetime
    total_recommended_seat_change: int
    total_trainer_workshops: int
    recommendations: list[CapacityPlanRecommendation]


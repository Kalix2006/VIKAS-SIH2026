"""Pydantic schemas for institute admin endpoints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CourseStatus, GapType


class InstituteFlagItem(BaseModel):
    """Flag item returned in the institute flag inbox."""

    flag_id: uuid.UUID
    course_id: uuid.UUID
    course_name: str
    trade_name: str
    nsqf_code: str
    seats_available: int
    course_status: CourseStatus
    gap_type: GapType
    gap_score: float
    job_posting_volume: int
    reason: str
    acknowledged: bool
    acknowledged_at: datetime | None = None
    acknowledged_by_name: str | None = None
    created_at: datetime


class AcknowledgeFlagResponse(BaseModel):
    """Response returned when a flag is acknowledged."""

    flag_id: uuid.UUID
    acknowledged: bool
    acknowledged_at: datetime
    acknowledged_by: uuid.UUID
    message: str


class TrainerRefresherRequestCreate(BaseModel):
    """Request body for requesting a trainer refresher."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    notes: str | None = Field(default=None, max_length=1000)


class TrainerRefresherRequestResponse(BaseModel):
    """Response returned when a trainer refresher request is created."""

    id: uuid.UUID
    flag_id: uuid.UUID
    institute_id: uuid.UUID
    status: str
    notes: str | None
    created_at: datetime
    message: str


class ScoreTrendPoint(BaseModel):
    """Historical or calculated data point for score trend line chart."""

    timestamp: str
    gap_score: float
    market_demand_factor: float
    similarity_score: float


class DriftDetailResponse(BaseModel):
    """Comprehensive drift analysis drill-down for a flagged course."""

    flag_id: uuid.UUID
    course_id: uuid.UUID
    course_name: str
    trade_name: str
    nsqf_code: str
    gap_type: GapType
    gap_score: float
    reason: str
    acknowledged: bool
    acknowledged_at: datetime | None
    acknowledged_by_name: str | None
    score_trend: list[ScoreTrendPoint]
    skills_drifted: list[str]
    syllabus_skills: list[str]
    refresher_requested: bool = False
    refresher_request_id: uuid.UUID | None = None
    score_breakdown: dict[str, Any]


class CourseDemandComparison(BaseModel):
    """Enrollment vs market demand data point for charts."""

    course_id: uuid.UUID
    course_name: str
    trade_name: str
    seats_available: int
    job_posting_volume: int
    ratio: float
    recommendation: str
    course_status: CourseStatus


class EnrollmentVsDemandResponse(BaseModel):
    """Response for enrollment vs market demand analytics."""

    institute_id: uuid.UUID
    institute_name: str
    district_name: str
    courses: list[CourseDemandComparison]
    summary: str

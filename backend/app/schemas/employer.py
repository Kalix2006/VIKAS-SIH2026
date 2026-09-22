"""Pydantic schemas for the Employer Validation & Demand Signals dashboard.

Enforces strict privacy-by-design:
- Inferred skill demand
- Structured skill validation and free-text parsing
- Hiring intent signals
- Strictly aggregate cohort readiness (zero per-person identifiers or PII)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InferredSkillItem(BaseModel):
    """Inferred skill candidate for quick confirmation."""

    skill_name: str
    category: str = Field(
        ..., description="'core_tool' | 'technical_competency' | 'emerging'"
    )
    posting_frequency: int = 0
    is_recommended: bool = True


class SkillsInferredResponse(BaseModel):
    """GET /employer/skills-inferred response body."""

    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    district_id: uuid.UUID
    district_name: str
    total_postings_analyzed: int
    inferred_skills: list[InferredSkillItem]


class EmployerValidateRequest(BaseModel):
    """POST /employer/validate request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    trade_id: uuid.UUID
    district_id: uuid.UUID
    confirmed_skills: list[str] = Field(
        default_factory=list,
        description="List of skills confirmed/edited by the employer",
    )
    raw_free_text: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional unstructured job requirements or syllabus feedback",
    )


class EmployerValidateResponse(BaseModel):
    """POST /employer/validate response body."""

    validation_id: uuid.UUID
    trade_name: str
    district_name: str
    confirmed_skills: list[str]
    extracted_from_free_text: list[str] = Field(default_factory=list)
    parsed_by_llm: bool
    needs_manual_review: bool
    submitted_at: datetime


class HiringSignalRequest(BaseModel):
    """POST /employer/hiring-signal request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    trade_id: uuid.UUID
    district_id: uuid.UUID
    vacancies_count: int = Field(..., ge=1, le=1000)
    timeframe_months: int = Field(..., ge=1, le=24)
    urgency: str = Field(
        default="immediate",
        description="'immediate' | 'upcoming' | 'apprenticeship'",
    )
    notes: str | None = Field(default=None, max_length=1000)


class HiringSignalResponse(BaseModel):
    """POST /employer/hiring-signal response body."""

    signal_id: uuid.UUID
    trade_name: str
    district_name: str
    vacancies_count: int
    timeframe_months: int
    urgency: str
    notes: str | None = None
    recorded_at: datetime


class CompetencyMastery(BaseModel):
    """Aggregate competency mastery for a vocational trade cohort."""

    competency_name: str
    category: str
    mastery_percentage: float


class ReadinessDistribution(BaseModel):
    """Distribution of trainee readiness cohorts (aggregate counts only)."""

    high_readiness: int = Field(..., description="Readiness score >= 80%")
    moderate_readiness: int = Field(..., description="Readiness score 50-79%")
    foundational: int = Field(..., description="Readiness score < 50%")


class AggregateReadinessResponse(BaseModel):
    """GET /employer/aggregate-readiness response body.

    CRITICAL PRIVACY GUARANTEE:
    This payload provides statistical aggregates strictly at the district cohort level.
    It contains ZERO individual trainee IDs, names, emails, roll numbers, or personal profiles.
    """

    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    district_id: uuid.UUID
    district_name: str
    total_enrolled_trainees: int
    graduating_within_90_days: int
    cohort_readiness_index: float = Field(
        ..., description="Aggregate cohort readiness score (0-100)"
    )
    readiness_distribution: ReadinessDistribution
    competency_mastery: list[CompetencyMastery]
    contributing_institutes_count: int
    privacy_guarantee: str = Field(
        default=(
            "Aggregate readiness metrics strictly anonymized per VIKAS Data "
            "Protection & Privacy-by-Design Guidelines. Zero candidate PII or "
            "individual trainee identifiers exposed."
        )
    )


class EmployerValidationListItem(BaseModel):
    """Item for GET /employer/my-validations."""

    id: uuid.UUID
    trade_name: str
    district_name: str
    type: str = Field(..., description="'skill_validation' | 'hiring_signal'")
    summary: str
    parsed_by_llm: bool
    needs_manual_review: bool
    submitted_at: datetime

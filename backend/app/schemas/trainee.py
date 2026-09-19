"""Pydantic schemas for trainee-facing endpoints.

All schemas designed for the trainee persona:
- Never expose raw numeric scores (gap_score, similarity, nlp_confidence).
- Use plain-language labels, empathetic guidance, and structured categories.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AlertGenerator, CourseStatus


class TraineeCourseResponse(BaseModel):
    """Course item for district catalog viewed by a trainee."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institute_id: uuid.UUID
    institute_name: str
    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    seats_available: int
    status: CourseStatus
    demand_label: str  # e.g., "Strong local demand", "High competition"
    demand_level: str  # "high", "stable", "caution", "emerging"
    has_alternatives: bool = False


class CourseAlternativeResponse(BaseModel):
    """Recommended alternative course for a flagged or obsolete program."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institute_id: uuid.UUID
    institute_name: str
    trade_id: uuid.UUID
    trade_name: str
    nsqf_code: str
    seats_available: int
    status: CourseStatus
    demand_label: str
    recommendation_rationale: str


class AlternativesGuideResponse(BaseModel):
    """Wrapper response providing empathetic career guidance and ranked alternatives."""

    flagged_course_name: str
    flagged_institute_name: str
    guidance_message: str
    alternatives: list[CourseAlternativeResponse]


class SkillCategory(BaseModel):
    """Category grouping of skills required in the local job market."""

    category: str  # e.g., "Core Tools & Equipment", "Key Competencies"
    skills: list[str]


class ProficiencyExpectationsResponse(BaseModel):
    """Market skill expectations for a trade within a district."""

    trade_id: uuid.UUID
    trade_name: str
    district_id: uuid.UUID
    district_name: str
    summary: str
    top_in_demand_skills: list[str]
    skill_categories: list[SkillCategory]


class ChatRequest(BaseModel):
    """Trainee conversational assistant prompt."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Career or course inquiry from the trainee.",
    )


class ChatResponse(BaseModel):
    """Grounded conversational response with provenance metadata."""

    reply: str
    grounded_district: str
    grounded_courses_count: int
    fallback_used: bool = False


class TraineeAlertResponse(BaseModel):
    """Alert notification tailored for a trainee."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message: str
    generated_by: AlertGenerator
    reviewed: bool
    created_at: datetime

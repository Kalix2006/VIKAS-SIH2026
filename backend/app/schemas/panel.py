"""Pydantic schemas for panel review and voting endpoints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    GapType,
    PanelRoleType,
    ReviewDecision,
    ReviewTrack,
    VoteChoice,
)


class VoteRequest(BaseModel):
    """POST /panel/reviews/{id}/vote request body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vote: VoteChoice
    comment: str | None = Field(default=None, max_length=1000)


class PanelVoteResponse(BaseModel):
    """Single panel vote response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    panel_review_id: uuid.UUID
    panel_member_id: uuid.UUID
    vote: VoteChoice
    comment: str | None
    voted_at: datetime
    panel_role: PanelRoleType | None = None
    voter_name: str | None = None


class PanelReviewResponse(BaseModel):
    """Panel review summary response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    skill_gap_id: uuid.UUID
    track: ReviewTrack
    required_signoffs: int
    decision: ReviewDecision
    veto_used: bool
    decided_at: datetime | None
    votes: list[PanelVoteResponse] = []

    # Rich contextual fields populated for frontend display
    trade_name: str | None = None
    nsqf_code: str | None = None
    district_name: str | None = None
    gap_type: GapType | None = None
    gap_score: float | None = None
    nlp_confidence: float | None = None
    job_posting_volume: int | None = None
    academic_veto_enabled: bool = False


class ScoreBreakdownResponse(BaseModel):
    """GET /panel/reviews/{id}/score-breakdown response body."""

    skill_gap_id: uuid.UUID
    gap_score: float
    nlp_confidence: float
    gap_type: GapType
    job_posting_volume: int
    score_breakdown: dict[str, Any]
    trade_name: str | None = None
    district_name: str | None = None


class GovernanceResponse(BaseModel):
    """GET /panel/governance response body."""

    academic_veto_enabled: bool


class GovernanceToggleRequest(BaseModel):
    """POST /panel/governance/toggle request body."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None

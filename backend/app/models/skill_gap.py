"""SkillGap model — detected demand-supply gap."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GapStatus, GapType, enum_values

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.course import Course
    from app.models.district import District
    from app.models.flag_annotation import FlagAnnotation
    from app.models.panel_review import PanelReview
    from app.models.trade import Trade
    from app.models.trainer_refresher_request import TrainerRefresherRequest
    from app.models.user import User


class SkillGap(Base):
    """Detected skill demand-supply gap at the district-trade level.

    gap_score and nlp_confidence are computed algorithmically —
    the LLM is NEVER used for scoring (see CLAUDE.md LLM Policy).
    score_breakdown stores the component scores for auditability.
    """

    __tablename__ = "skill_gaps"
    __table_args__ = (
        sa.CheckConstraint(
            "nlp_confidence >= 0 AND nlp_confidence <= 1",
            name="ck_skill_gaps_nlp_confidence_range",
        ),
        sa.CheckConstraint(
            "gap_score >= 0", name="ck_skill_gaps_gap_score_non_negative"
        ),
        sa.Index("ix_skill_gaps_district_trade", "district_id", "trade_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    trade_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    gap_type: Mapped[GapType] = mapped_column(
        sa.Enum(
            GapType,
            name="gap_type",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    nlp_confidence: Mapped[float] = mapped_column(sa.Float, nullable=False)
    job_posting_volume: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    gap_score: Mapped[float] = mapped_column(sa.Float, nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[GapStatus] = mapped_column(
        sa.Enum(
            GapStatus,
            name="gap_status",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=sa.text("'detected'"),
        index=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    district: Mapped["District"] = relationship(back_populates="skill_gaps")
    trade: Mapped["Trade"] = relationship(back_populates="skill_gaps")
    course: Mapped["Course | None"] = relationship(back_populates="skill_gaps")
    panel_review: Mapped["PanelReview | None"] = relationship(
        back_populates="skill_gap", uselist=False
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="skill_gap")
    flag_annotations: Mapped[list["FlagAnnotation"]] = relationship(
        back_populates="skill_gap"
    )
    acknowledged_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[acknowledged_by]
    )
    trainer_refresher_requests: Mapped[list["TrainerRefresherRequest"]] = relationship(
        back_populates="skill_gap"
    )

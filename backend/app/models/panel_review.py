"""PanelReview model — review decision on a skill gap."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReviewDecision, ReviewTrack, enum_values

if TYPE_CHECKING:
    from app.models.panel_vote import PanelVote
    from app.models.skill_gap import SkillGap


class PanelReview(Base):
    """Panel review for a detected skill gap.

    Each skill gap gets at most one review (UNIQUE on skill_gap_id).
    Tracks whether the review follows the urgent or standard track.
    """

    __tablename__ = "panel_reviews"
    __table_args__ = (
        sa.CheckConstraint(
            "required_signoffs > 0",
            name="ck_panel_reviews_signoffs_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    skill_gap_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    track: Mapped[ReviewTrack] = mapped_column(
        sa.Enum(
            ReviewTrack,
            name="review_track",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    required_signoffs: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(
        sa.Enum(
            ReviewDecision,
            name="review_decision",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=sa.text("'pending'"),
        index=True,
    )
    veto_used: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    skill_gap: Mapped["SkillGap"] = relationship(back_populates="panel_review")
    votes: Mapped[list["PanelVote"]] = relationship(back_populates="panel_review")

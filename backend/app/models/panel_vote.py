"""PanelVote model — individual panel member vote on a review."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import VoteChoice, enum_values

if TYPE_CHECKING:
    from app.models.panel_member import PanelMember
    from app.models.panel_review import PanelReview


class PanelVote(Base):
    """Individual vote cast by a panel member on a review.

    UniqueConstraint ensures one vote per member per review.
    """

    __tablename__ = "panel_votes"
    __table_args__ = (
        sa.UniqueConstraint(
            "panel_review_id",
            "panel_member_id",
            name="uq_panel_votes_review_member",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    panel_review_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("panel_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    panel_member_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("panel_members.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    vote: Mapped[VoteChoice] = mapped_column(
        sa.Enum(
            VoteChoice,
            name="vote_choice",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    voted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    panel_review: Mapped["PanelReview"] = relationship(back_populates="votes")
    panel_member: Mapped["PanelMember"] = relationship(back_populates="votes")

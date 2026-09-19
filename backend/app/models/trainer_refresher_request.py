"""TrainerRefresherRequest model — tracked training refresher requests by institutes."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.institute import Institute
    from app.models.skill_gap import SkillGap
    from app.models.user import User


class TrainerRefresherRequest(Base):
    """Institute admin request for trainer refresher / upskilling on a skill gap.

    Allows institutes to signal curriculum training needs to district planners.
    """

    __tablename__ = "trainer_refresher_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    skill_gap_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institute_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("institutes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, server_default=sa.text("'pending'")
    )
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    skill_gap: Mapped["SkillGap"] = relationship(
        back_populates="trainer_refresher_requests"
    )
    institute: Mapped["Institute"] = relationship()
    requester: Mapped["User"] = relationship()

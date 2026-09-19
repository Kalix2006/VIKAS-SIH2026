"""FlagAnnotation model — planner notes on flagged skill gaps."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OverrideStatus, enum_values

if TYPE_CHECKING:
    from app.models.skill_gap import SkillGap
    from app.models.user import User


class FlagAnnotation(Base):
    """Planner annotation on a skill gap.

    Planners can add notes and optionally override (confirm/dismiss) a gap.
    Write access is limited to planners only (enforced by both app + RLS).
    """

    __tablename__ = "flag_annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    skill_gap_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    planner_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note: Mapped[str] = mapped_column(sa.Text, nullable=False)
    override_status: Mapped[OverrideStatus | None] = mapped_column(
        sa.Enum(
            OverrideStatus,
            name="override_status",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    skill_gap: Mapped["SkillGap"] = relationship(back_populates="flag_annotations")
    planner: Mapped["User"] = relationship(back_populates="flag_annotations")

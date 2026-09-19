"""Alert model — notifications to trainees and institute admins."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AlertGenerator, AlertTargetRole, enum_values

if TYPE_CHECKING:
    from app.models.skill_gap import SkillGap
    from app.models.user import User


class Alert(Base):
    """Alert notification generated for a skill gap.

    generated_by tracks whether Groq LLM or a deterministic template
    produced the message text. Template fallback is mandatory — see CLAUDE.md.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    target_role: Mapped[AlertTargetRole] = mapped_column(
        sa.Enum(
            AlertTargetRole,
            name="alert_target_role",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_gap_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    generated_by: Mapped[AlertGenerator] = mapped_column(
        sa.Enum(
            AlertGenerator,
            name="alert_generator",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    reviewed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    target_user: Mapped["User"] = relationship(back_populates="alerts")
    skill_gap: Mapped["SkillGap"] = relationship(back_populates="alerts")

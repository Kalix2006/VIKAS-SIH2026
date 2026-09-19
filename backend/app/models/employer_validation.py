"""EmployerValidation model — employer-submitted skill demand confirmation."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.district import District
    from app.models.trade import Trade
    from app.models.user import User


class EmployerValidation(Base):
    """Employer validation of skill demand in a district-trade pair.

    raw_free_text may be parsed by Groq LLM (parsed_by_llm=True),
    but this is ONLY for text extraction — never for scoring.
    Every Groq call has a template fallback (see CLAUDE.md).
    """

    __tablename__ = "employer_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    employer_user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trade_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    confirmed_skills: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    raw_free_text: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    parsed_by_llm: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    employer_user: Mapped["User"] = relationship(back_populates="employer_validations")
    trade: Mapped["Trade"] = relationship(back_populates="employer_validations")
    district: Mapped["District"] = relationship(back_populates="employer_validations")

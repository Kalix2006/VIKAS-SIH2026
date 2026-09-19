"""JobPosting model — ingested from external job boards."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobSource, enum_values

if TYPE_CHECKING:
    from app.models.district import District
    from app.models.trade import Trade


class JobPosting(Base):
    """Job posting ingested from Adzuna or Jooble.

    extracted_skills is populated by the NLP pipeline (spaCy + sentence-transformers),
    NEVER by the LLM — see CLAUDE.md LLM Policy.
    """

    __tablename__ = "job_postings"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    source: Mapped[JobSource] = mapped_column(
        sa.Enum(
            JobSource,
            name="job_source",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    raw_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    extracted_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    posted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    # Relationships
    district: Mapped["District"] = relationship(back_populates="job_postings")
    trade: Mapped["Trade | None"] = relationship(back_populates="job_postings")

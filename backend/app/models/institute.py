"""Institute model — training institution."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.district import District
    from app.models.user import User


class Institute(Base):
    """Training institute (ITI, PMKVY center, private institute, etc.)."""

    __tablename__ = "institutes"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,  # e.g., "ITI", "PMKVY", "private"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    district: Mapped["District"] = relationship(back_populates="institutes")
    users: Mapped[list["User"]] = relationship(back_populates="institute")
    courses: Mapped[list["Course"]] = relationship(back_populates="institute")

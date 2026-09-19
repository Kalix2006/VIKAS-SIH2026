"""TraineeProfile model — 1:1 extension for users with trainee role."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.district import District
    from app.models.user import User


class TraineeProfile(Base):
    """Trainee profile linked to a user, district, and optional course enrollment."""

    __tablename__ = "trainee_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    enrolled_course_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="trainee_profile")
    enrolled_course: Mapped["Course | None"] = relationship(
        back_populates="trainee_profiles"
    )
    district: Mapped["District"] = relationship(back_populates="trainee_profiles")

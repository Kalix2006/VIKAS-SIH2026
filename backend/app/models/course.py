"""Course model — training program offered by an institute."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CourseStatus, enum_values

if TYPE_CHECKING:
    from app.models.institute import Institute
    from app.models.skill_gap import SkillGap
    from app.models.trade import Trade
    from app.models.trainee_profile import TraineeProfile


class Course(Base):
    """Training course offered by an institute for a specific trade."""

    __tablename__ = "courses"
    __table_args__ = (
        sa.CheckConstraint(
            "seats_available >= 0", name="ck_courses_seats_non_negative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    institute_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("institutes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trade_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    seats_available: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[CourseStatus] = mapped_column(
        sa.Enum(
            CourseStatus,
            name="course_status",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=sa.text("'active'"),
        index=True,
    )

    # Relationships
    institute: Mapped["Institute"] = relationship(back_populates="courses")
    trade: Mapped["Trade"] = relationship(back_populates="courses")
    skill_gaps: Mapped[list["SkillGap"]] = relationship(back_populates="course")
    trainee_profiles: Mapped[list["TraineeProfile"]] = relationship(
        back_populates="enrolled_course"
    )

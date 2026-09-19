"""District model — administrative unit for gap analysis."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.employer_validation import EmployerValidation
    from app.models.institute import Institute
    from app.models.job_posting import JobPosting
    from app.models.skill_gap import SkillGap
    from app.models.trainee_profile import TraineeProfile
    from app.models.user import User


class District(Base):
    """Indian administrative district.

    Primary geographic unit for skill demand-supply gap analysis.
    Centroid coordinates used for Leaflet map rendering.
    """

    __tablename__ = "districts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    state: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    centroid_lat: Mapped[float] = mapped_column(sa.Float, nullable=False)
    centroid_lng: Mapped[float] = mapped_column(sa.Float, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="district")
    institutes: Mapped[list["Institute"]] = relationship(back_populates="district")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="district")
    skill_gaps: Mapped[list["SkillGap"]] = relationship(back_populates="district")
    employer_validations: Mapped[list["EmployerValidation"]] = relationship(
        back_populates="district"
    )
    trainee_profiles: Mapped[list["TraineeProfile"]] = relationship(
        back_populates="district"
    )

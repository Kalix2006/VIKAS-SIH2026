"""Trade model — vocational skill/occupation classification."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.employer_validation import EmployerValidation
    from app.models.job_posting import JobPosting
    from app.models.skill_gap import SkillGap


class Trade(Base):
    """Vocational trade aligned to NSQF (National Skills Qualifications Framework).

    Each trade has a unique NSQF code. The five locked starter trades are:
    Electrician, Fitter, Welder, Automobile/Diesel Mechanic, COPA.
    """

    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    nsqf_code: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True)

    # Relationships
    courses: Mapped[list["Course"]] = relationship(back_populates="trade")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="trade")
    skill_gaps: Mapped[list["SkillGap"]] = relationship(back_populates="trade")
    employer_validations: Mapped[list["EmployerValidation"]] = relationship(
        back_populates="trade"
    )

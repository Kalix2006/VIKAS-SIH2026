"""User model — authenticated platform user with RBAC role."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, enum_values

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.district import District
    from app.models.employer_validation import EmployerValidation
    from app.models.flag_annotation import FlagAnnotation
    from app.models.institute import Institute
    from app.models.panel_member import PanelMember
    from app.models.refresh_token import RefreshToken
    from app.models.trainee_profile import TraineeProfile


class User(Base):
    """Platform user.

    Every user has exactly one RBAC role. Role determines:
    - Which routes they can access (application-layer require_role)
    - Which rows they can see (database-layer RLS policies)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(
        sa.String(320),
        nullable=False,
        unique=True,  # RFC 5321 max email length
    )
    password_hash: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("districts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    institute_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("institutes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    district: Mapped["District"] = relationship(back_populates="users")
    institute: Mapped["Institute | None"] = relationship(back_populates="users")
    panel_member: Mapped["PanelMember | None"] = relationship(
        back_populates="user", uselist=False
    )
    trainee_profile: Mapped["TraineeProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    employer_validations: Mapped[list["EmployerValidation"]] = relationship(
        back_populates="employer_user"
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="target_user")
    flag_annotations: Mapped[list["FlagAnnotation"]] = relationship(
        back_populates="planner"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")

"""PanelMember model — 1:1 extension for users with panel_member role."""

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PanelRoleType, enum_values

if TYPE_CHECKING:
    from app.models.panel_vote import PanelVote
    from app.models.user import User


class PanelMember(Base):
    """Panel member profile.

    One-to-one extension of User for users with role=panel_member.
    user_id is both PK and FK — ensures exactly one panel_member per user.
    """

    __tablename__ = "panel_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    panel_role: Mapped[PanelRoleType] = mapped_column(
        sa.Enum(
            PanelRoleType,
            name="panel_role_type",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="panel_member")
    votes: Mapped[list["PanelVote"]] = relationship(back_populates="panel_member")

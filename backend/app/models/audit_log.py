"""AuditLog model — immutable audit trail for governance actions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.user import User

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditLog(Base):
    """Immutable audit trail of high-stakes governance actions.

    Records panel review votes/decisions, planner overrides,
    and administrative flag acknowledgements for government accountability.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    event_type: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
        index=True,
    )

    # Relationships
    actor: Mapped["User"] = relationship()

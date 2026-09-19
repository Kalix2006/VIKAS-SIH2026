"""Audit logging service for tracking critical governance decisions."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.audit_log import AuditLog


async def record_audit_event(
    db: AsyncSession,
    event_type: str,
    actor_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an immutable audit log entry in PostgreSQL."""
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    db.add(entry)
    await db.flush()

    logger.info(
        f"AUDIT_EVENT: {event_type} on {resource_type}:{resource_id} by actor {actor_id}",
        extra={
            "audit_event": event_type,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "actor_id": str(actor_id),
        },
    )
    return entry


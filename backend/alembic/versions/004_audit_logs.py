"""Add audit_logs table for immutable governance actions.

Revision ID: 004
Revises: 003
Create Date: 2026-09-19

Creates the audit_logs table with RLS policies:
- Immutable audit log for panel decisions, planner overrides, and flag acknowledgements.
- Planners can read all audit logs.
- Insert restricted to authenticated actors recording their own actions.
- No update or delete allowed (append-only ledger).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "details",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # RLS Policies
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY"))

    # Planners can read all audit logs
    conn.execute(sa.text("""
        CREATE POLICY rls_audit_logs_select ON audit_logs
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) = 'planner'
            OR actor_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # Any authenticated user can insert an audit log record as themselves
    conn.execute(sa.text("""
        CREATE POLICY rls_audit_logs_insert ON audit_logs
        FOR INSERT
        WITH CHECK (
            actor_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # Grant access to vikas_app
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vikas_app') THEN
                GRANT ALL ON audit_logs TO vikas_app;
            END IF;
        END $$;
    """))


def downgrade() -> None:
    op.drop_table("audit_logs")


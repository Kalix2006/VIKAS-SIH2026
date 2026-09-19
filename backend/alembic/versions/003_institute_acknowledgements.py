"""Add institute flag acknowledgements and trainer refresher requests.

Revision ID: 003
Revises: 002
Create Date: 2026-09-18

Additive changes:
1. Add 'planner' to alert_target_role enum.
2. Add acknowledged_at and acknowledged_by to skill_gaps.
3. Create trainer_refresher_requests table with RLS policies.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add 'planner' to alert_target_role enum
    # In PostgreSQL, ALTER TYPE ... ADD VALUE cannot be run inside a transaction block in older PG versions,
    # but PostgreSQL 12+ allows it IF the value doesn't already exist.
    conn.execute(sa.text("ALTER TYPE alert_target_role ADD VALUE IF NOT EXISTS 'planner'"))

    # 2. Add acknowledged_at and acknowledged_by to skill_gaps
    op.add_column(
        "skill_gaps",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "skill_gaps",
        sa.Column(
            "acknowledged_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_skill_gaps_acknowledged_at", "skill_gaps", ["acknowledged_at"])

    # 3. Create trainer_refresher_requests table
    op.create_table(
        "trainer_refresher_requests",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "skill_gap_id",
            UUID(as_uuid=True),
            sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "institute_id",
            UUID(as_uuid=True),
            sa.ForeignKey("institutes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(50),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_trainer_refresher_requests_skill_gap_id",
        "trainer_refresher_requests",
        ["skill_gap_id"],
    )
    op.create_index(
        "ix_trainer_refresher_requests_institute_id",
        "trainer_refresher_requests",
        ["institute_id"],
    )
    op.create_index(
        "ix_trainer_refresher_requests_requested_by",
        "trainer_refresher_requests",
        ["requested_by"],
    )

    # 4. RLS on trainer_refresher_requests
    conn.execute(sa.text("ALTER TABLE trainer_refresher_requests ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE trainer_refresher_requests FORCE ROW LEVEL SECURITY"))

    # Institute admins see requests for their institute; planners and panel members see all
    conn.execute(
        sa.text("""
        CREATE POLICY rls_trainer_refresher_requests_select ON trainer_refresher_requests
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
            OR institute_id = current_setting('app.current_institute_id', true)::uuid
        )
    """)
    )

    # Institute admins can insert for their own institute
    conn.execute(
        sa.text("""
        CREATE POLICY rls_trainer_refresher_requests_insert ON trainer_refresher_requests
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_role', true) = 'institute_admin'
            AND institute_id = current_setting('app.current_institute_id', true)::uuid
            AND requested_by = current_setting('app.current_user_id', true)::uuid
        )
    """)
    )

    # 5. RLS policies for skill_gaps update and alerts insert
    conn.execute(
        sa.text("""
        CREATE POLICY rls_skill_gaps_institute_update ON skill_gaps
        FOR UPDATE
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
            OR (
                current_setting('app.current_user_role', true) = 'institute_admin'
                AND course_id IN (
                    SELECT id FROM courses WHERE institute_id = current_setting('app.current_institute_id', true)::uuid
                )
            )
        )
    """)
    )

    conn.execute(
        sa.text("""
        DROP POLICY IF EXISTS rls_alerts_select ON alerts;
        CREATE POLICY rls_alerts_select ON alerts
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member', 'institute_admin')
            OR target_id = current_setting('app.current_user_id', true)::uuid
        );
    """)
    )

    conn.execute(
        sa.text("""
        CREATE POLICY rls_alerts_insert ON alerts
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member', 'institute_admin')
        )
    """)
    )

    # 6. Grant access to vikas_app
    conn.execute(
        sa.text("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vikas_app') THEN
                GRANT ALL ON trainer_refresher_requests TO vikas_app;
            END IF;
        END $$;
    """)
    )


def downgrade() -> None:
    op.drop_table("trainer_refresher_requests")
    op.drop_index("ix_skill_gaps_acknowledged_at", table_name="skill_gaps")
    op.drop_column("skill_gaps", "acknowledged_by")
    op.drop_column("skill_gaps", "acknowledged_at")

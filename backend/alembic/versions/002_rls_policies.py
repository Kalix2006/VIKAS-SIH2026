"""Row-Level Security policies for Supabase defense-in-depth.

Revision ID: 002
Revises: 001
Create Date: 2026-09-17

Implements RLS policies using PostgreSQL session variables set via
SET LOCAL at the start of each transaction (see app.db.session.set_rls_context).

Session variables used:
  - app.current_user_id   (UUID as text)
  - app.current_user_role  (user_role enum value as text)
  - app.current_district_id (UUID as text)
  - app.current_institute_id (UUID as text, empty string if N/A)

Policy design:
  - Trainees: SELECT only their own user row + their district's data
  - Institute admins: SELECT/UPDATE scoped to their institute_id
  - Employers: SELECT/INSERT scoped to their own user_id
  - Planners: Full SELECT across all districts, writes limited to flag_annotations
  - Panel members: Treated similarly to planners for SELECT on review-related tables

Defense-in-depth: These policies mirror the application-layer require_role()
and require_own_scope() dependencies. Neither layer is a replacement for the other.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text as sa_text

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that get RLS policies
RLS_TABLES = [
    "users",
    "panel_members",
    "courses",
    "job_postings",
    "skill_gaps",
    "panel_reviews",
    "panel_votes",
    "employer_validations",
    "trainee_profiles",
    "alerts",
    "flag_annotations",
    "refresh_tokens",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ---- Enable RLS on all data tables ----
    for table in RLS_TABLES:
        conn.execute(sa_text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        # FORCE RLS for table owners too (Supabase best practice)
        conn.execute(sa_text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

    # ============================================================
    # USERS TABLE POLICIES
    # ============================================================

    # Trainees can only see their own user row
    conn.execute(sa_text("""
        CREATE POLICY rls_users_trainee_select ON users
        FOR SELECT
        USING (
            -- Non-trainees bypass this policy
            current_setting('app.current_user_role', true) != 'trainee'
            -- Trainees can only see their own row
            OR id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # Institute admins can see users in their institute
    conn.execute(sa_text("""
        CREATE POLICY rls_users_institute_select ON users
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) NOT IN ('trainee', 'institute_admin')
            OR id = current_setting('app.current_user_id', true)::uuid
            OR (
                current_setting('app.current_user_role', true) = 'institute_admin'
                AND institute_id IS NOT NULL
                AND institute_id = current_setting('app.current_institute_id', true)::uuid
            )
        )
    """))

    # ============================================================
    # COURSES TABLE POLICIES
    # ============================================================

    # Institute admins can only see/modify courses in their institute
    conn.execute(sa_text("""
        CREATE POLICY rls_courses_institute_select ON courses
        FOR SELECT
        USING (
            -- Planners, panel members, employers see all courses
            current_setting('app.current_user_role', true) NOT IN ('trainee', 'institute_admin')
            -- Institute admins see only their institute's courses
            OR institute_id = current_setting('app.current_institute_id', true)::uuid
            -- Trainees see courses in their district (via institute)
            OR (
                current_setting('app.current_user_role', true) = 'trainee'
                AND institute_id IN (
                    SELECT id FROM institutes
                    WHERE district_id = current_setting('app.current_district_id', true)::uuid
                )
            )
        )
    """))

    conn.execute(sa_text("""
        CREATE POLICY rls_courses_institute_update ON courses
        FOR UPDATE
        USING (
            current_setting('app.current_user_role', true) = 'institute_admin'
            AND institute_id = current_setting('app.current_institute_id', true)::uuid
        )
    """))

    # ============================================================
    # SKILL_GAPS TABLE POLICIES
    # ============================================================

    # Trainees can only see skill gaps in their district
    conn.execute(sa_text("""
        CREATE POLICY rls_skill_gaps_district_select ON skill_gaps
        FOR SELECT
        USING (
            -- Planners and panel members see all
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
            -- Others see only their district
            OR district_id = current_setting('app.current_district_id', true)::uuid
        )
    """))

    # ============================================================
    # EMPLOYER_VALIDATIONS TABLE POLICIES
    # ============================================================

    # Employers can only see their own validations
    conn.execute(sa_text("""
        CREATE POLICY rls_employer_validations_select ON employer_validations
        FOR SELECT
        USING (
            -- Planners and panel members see all
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
            -- Employers see only their own
            OR employer_user_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    conn.execute(sa_text("""
        CREATE POLICY rls_employer_validations_insert ON employer_validations
        FOR INSERT
        WITH CHECK (
            -- Only employers can insert, and only for themselves
            current_setting('app.current_user_role', true) = 'employer'
            AND employer_user_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # ============================================================
    # TRAINEE_PROFILES TABLE POLICIES
    # ============================================================

    conn.execute(sa_text("""
        CREATE POLICY rls_trainee_profiles_select ON trainee_profiles
        FOR SELECT
        USING (
            -- Non-trainees bypass
            current_setting('app.current_user_role', true) != 'trainee'
            -- Trainees see only their own profile
            OR user_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # ============================================================
    # ALERTS TABLE POLICIES
    # ============================================================

    conn.execute(sa_text("""
        CREATE POLICY rls_alerts_select ON alerts
        FOR SELECT
        USING (
            -- Planners see all alerts
            current_setting('app.current_user_role', true) = 'planner'
            -- Others see only alerts targeted to them
            OR target_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # ============================================================
    # FLAG_ANNOTATIONS TABLE POLICIES
    # ============================================================

    # Only planners can read flag annotations
    conn.execute(sa_text("""
        CREATE POLICY rls_flag_annotations_select ON flag_annotations
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) = 'planner'
        )
    """))

    # Only planners can insert, and only as themselves
    conn.execute(sa_text("""
        CREATE POLICY rls_flag_annotations_insert ON flag_annotations
        FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_role', true) = 'planner'
            AND planner_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # ============================================================
    # REFRESH_TOKENS TABLE POLICIES
    # ============================================================

    # Users can only see their own refresh tokens
    conn.execute(sa_text("""
        CREATE POLICY rls_refresh_tokens_select ON refresh_tokens
        FOR SELECT
        USING (
            user_id = current_setting('app.current_user_id', true)::uuid
        )
    """))

    # ============================================================
    # JOB_POSTINGS, PANEL_REVIEWS, PANEL_VOTES, PANEL_MEMBERS
    # ============================================================

    # Job postings: district-scoped for trainees, full for others
    conn.execute(sa_text("""
        CREATE POLICY rls_job_postings_select ON job_postings
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member', 'employer')
            OR district_id = current_setting('app.current_district_id', true)::uuid
        )
    """))

    # Panel reviews: visible to planners and panel members
    conn.execute(sa_text("""
        CREATE POLICY rls_panel_reviews_select ON panel_reviews
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
        )
    """))

    # Panel votes: visible to planners and panel members
    conn.execute(sa_text("""
        CREATE POLICY rls_panel_votes_select ON panel_votes
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
        )
    """))

    # Panel members: visible to planners and panel members themselves
    conn.execute(sa_text("""
        CREATE POLICY rls_panel_members_select ON panel_members
        FOR SELECT
        USING (
            current_setting('app.current_user_role', true) IN ('planner', 'panel_member')
            OR user_id = current_setting('app.current_user_id', true)::uuid
        )
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Drop all policies by disabling RLS (which implicitly removes policies)
    for table in RLS_TABLES:
        # Drop all policies on this table
        conn.execute(sa_text(f"""
            DO $$ DECLARE
                pol RECORD;
            BEGIN
                FOR pol IN
                    SELECT policyname FROM pg_policies WHERE tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY %I ON {table}', pol.policyname);
                END LOOP;
            END $$;
        """))
        conn.execute(sa_text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

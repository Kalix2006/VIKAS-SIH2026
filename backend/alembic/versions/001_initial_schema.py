"""Initial schema: all core tables.

Revision ID: 001
Revises: 
Create Date: 2026-09-17

Creates 15 tables in dependency order:
1. ENUM types (12 PostgreSQL enums)
2. districts, trades (no FK deps)
3. institutes (FK -> districts)
4. users (FK -> districts, institutes)
5. panel_members (FK -> users)
6. courses (FK -> institutes, trades)
7. job_postings (FK -> districts, trades)
8. skill_gaps (FK -> districts, trades, courses)
9. panel_reviews (FK -> skill_gaps)
10. panel_votes (FK -> panel_reviews, panel_members)
11. employer_validations (FK -> users, trades, districts)
12. trainee_profiles (FK -> users, courses, districts)
13. alerts (FK -> users, skill_gaps)
14. flag_annotations (FK -> skill_gaps, users)
15. refresh_tokens (FK -> users)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB, UUID

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ENUM type definitions using PostgreSQL dialect ENUM
user_role_enum = PG_ENUM(
    "trainee", "institute_admin", "employer", "planner", "panel_member",
    name="user_role", create_type=False
)
panel_role_type_enum = PG_ENUM(
    "academic_expert", "industry_professional", "program_lead",
    name="panel_role_type", create_type=False
)
course_status_enum = PG_ENUM(
    "active", "flagged", "obsolete",
    name="course_status", create_type=False
)
job_source_enum = PG_ENUM(
    "adzuna", "jooble",
    name="job_source", create_type=False
)
gap_type_enum = PG_ENUM(
    "curriculum_drift", "oversupply", "undersupply", "emerging_skill",
    name="gap_type", create_type=False
)
gap_status_enum = PG_ENUM(
    "detected", "panel_queue", "urgent_escalation", "approved", "rejected",
    name="gap_status", create_type=False
)
review_track_enum = PG_ENUM(
    "urgent", "standard",
    name="review_track", create_type=False
)
review_decision_enum = PG_ENUM(
    "pending", "approved", "rejected",
    name="review_decision", create_type=False
)
vote_choice_enum = PG_ENUM(
    "approve", "reject", "abstain",
    name="vote_choice", create_type=False
)
alert_target_role_enum = PG_ENUM(
    "trainee", "institute_admin",
    name="alert_target_role", create_type=False
)
alert_generator_enum = PG_ENUM(
    "template", "groq",
    name="alert_generator", create_type=False
)
override_status_enum = PG_ENUM(
    "confirmed", "dismissed",
    name="override_status", create_type=False
)

ENUM_OBJECTS = [
    user_role_enum,
    panel_role_type_enum,
    course_status_enum,
    job_source_enum,
    gap_type_enum,
    gap_status_enum,
    review_track_enum,
    review_decision_enum,
    vote_choice_enum,
    alert_target_role_enum,
    alert_generator_enum,
    override_status_enum,
]


def upgrade() -> None:
    conn = op.get_bind()

    # ---- Create ENUM types ----
    for enum_obj in ENUM_OBJECTS:
        enum_obj.create(conn, checkfirst=True)

    # ---- 1. districts (no FK deps) ----
    op.create_table(
        "districts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("state", sa.String(255), nullable=False),
        sa.Column("centroid_lat", sa.Float, nullable=False),
        sa.Column("centroid_lng", sa.Float, nullable=False),
    )
    op.create_index("ix_districts_state", "districts", ["state"])

    # ---- 2. trades (no FK deps) ----
    op.create_table(
        "trades",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("nsqf_code", sa.String(50), nullable=False, unique=True),
    )

    # ---- 3. institutes (FK -> districts) ----
    op.create_table(
        "institutes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_institutes_district_id", "institutes", ["district_id"])

    # ---- 4. users (FK -> districts, institutes) ----
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("institute_id", UUID(as_uuid=True), sa.ForeignKey("institutes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_district_id", "users", ["district_id"])
    op.create_index("ix_users_institute_id", "users", ["institute_id"])

    # ---- 5. panel_members (FK -> users, PK = user_id) ----
    op.create_table(
        "panel_members",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("panel_role", panel_role_type_enum, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )

    # ---- 6. courses (FK -> institutes, trades) ----
    op.create_table(
        "courses",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("institute_id", UUID(as_uuid=True), sa.ForeignKey("institutes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("seats_available", sa.Integer, nullable=False),
        sa.Column("status", course_status_enum, nullable=False, server_default=sa.text("'active'")),
        sa.CheckConstraint("seats_available >= 0", name="ck_courses_seats_non_negative"),
    )
    op.create_index("ix_courses_institute_id", "courses", ["institute_id"])
    op.create_index("ix_courses_trade_id", "courses", ["trade_id"])
    op.create_index("ix_courses_status", "courses", ["status"])

    # ---- 7. job_postings (FK -> districts, trades) ----
    op.create_table(
        "job_postings",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source", job_source_enum, nullable=False),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_title", sa.String(500), nullable=False),
        sa.Column("raw_description", sa.Text, nullable=False),
        sa.Column("extracted_skills", JSONB, nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_job_postings_district_id", "job_postings", ["district_id"])
    op.create_index("ix_job_postings_trade_id", "job_postings", ["trade_id"])
    op.create_index("ix_job_postings_source", "job_postings", ["source"])

    # ---- 8. skill_gaps (FK -> districts, trades, courses) ----
    op.create_table(
        "skill_gaps",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gap_type", gap_type_enum, nullable=False),
        sa.Column("nlp_confidence", sa.Float, nullable=False),
        sa.Column("job_posting_volume", sa.Integer, nullable=False),
        sa.Column("gap_score", sa.Float, nullable=False),
        sa.Column("score_breakdown", JSONB, nullable=False),
        sa.Column("status", gap_status_enum, nullable=False, server_default=sa.text("'detected'")),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("nlp_confidence >= 0 AND nlp_confidence <= 1", name="ck_skill_gaps_nlp_confidence_range"),
        sa.CheckConstraint("gap_score >= 0", name="ck_skill_gaps_gap_score_non_negative"),
    )
    op.create_index("ix_skill_gaps_district_id", "skill_gaps", ["district_id"])
    op.create_index("ix_skill_gaps_trade_id", "skill_gaps", ["trade_id"])
    op.create_index("ix_skill_gaps_status", "skill_gaps", ["status"])
    op.create_index("ix_skill_gaps_district_trade", "skill_gaps", ["district_id", "trade_id"])

    # ---- 9. panel_reviews (FK -> skill_gaps) ----
    op.create_table(
        "panel_reviews",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("skill_gap_id", UUID(as_uuid=True), sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("track", review_track_enum, nullable=False),
        sa.Column("required_signoffs", sa.Integer, nullable=False),
        sa.Column("decision", review_decision_enum, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("veto_used", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("required_signoffs > 0", name="ck_panel_reviews_signoffs_positive"),
    )
    op.create_index("ix_panel_reviews_decision", "panel_reviews", ["decision"])

    # ---- 10. panel_votes (FK -> panel_reviews, panel_members) ----
    op.create_table(
        "panel_votes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("panel_review_id", UUID(as_uuid=True), sa.ForeignKey("panel_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("panel_member_id", UUID(as_uuid=True), sa.ForeignKey("panel_members.user_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vote", vote_choice_enum, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("voted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("panel_review_id", "panel_member_id", name="uq_panel_votes_review_member"),
    )
    op.create_index("ix_panel_votes_panel_review_id", "panel_votes", ["panel_review_id"])

    # ---- 11. employer_validations (FK -> users, trades, districts) ----
    op.create_table(
        "employer_validations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("employer_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("trades.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("confirmed_skills", JSONB, nullable=False),
        sa.Column("raw_free_text", sa.Text, nullable=True),
        sa.Column("parsed_by_llm", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_employer_validations_employer_user_id", "employer_validations", ["employer_user_id"])
    op.create_index("ix_employer_validations_district_id", "employer_validations", ["district_id"])
    op.create_index("ix_employer_validations_trade_id", "employer_validations", ["trade_id"])

    # ---- 12. trainee_profiles (FK -> users, courses, districts) ----
    op.create_table(
        "trainee_profiles",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enrolled_course_id", UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("district_id", UUID(as_uuid=True), sa.ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_trainee_profiles_user_id", "trainee_profiles", ["user_id"])
    op.create_index("ix_trainee_profiles_district_id", "trainee_profiles", ["district_id"])

    # ---- 13. alerts (FK -> users, skill_gaps) ----
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("target_role", alert_target_role_enum, nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_gap_id", UUID(as_uuid=True), sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("generated_by", alert_generator_enum, nullable=False),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alerts_target_id", "alerts", ["target_id"])
    op.create_index("ix_alerts_skill_gap_id", "alerts", ["skill_gap_id"])
    op.create_index("ix_alerts_reviewed", "alerts", ["reviewed"])

    # ---- 14. flag_annotations (FK -> skill_gaps, users) ----
    op.create_table(
        "flag_annotations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("skill_gap_id", UUID(as_uuid=True), sa.ForeignKey("skill_gaps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("planner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("override_status", override_status_enum, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_flag_annotations_skill_gap_id", "flag_annotations", ["skill_gap_id"])

    # ---- 15. refresh_tokens (FK -> users) ----
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("refresh_tokens")
    op.drop_table("flag_annotations")
    op.drop_table("alerts")
    op.drop_table("trainee_profiles")
    op.drop_table("employer_validations")
    op.drop_table("panel_votes")
    op.drop_table("panel_reviews")
    op.drop_table("skill_gaps")
    op.drop_table("job_postings")
    op.drop_table("courses")
    op.drop_table("panel_members")
    op.drop_table("users")
    op.drop_table("institutes")
    op.drop_table("trades")
    op.drop_table("districts")

    # Drop ENUM types
    conn = op.get_bind()
    for enum_obj in reversed(ENUM_OBJECTS):
        enum_obj.drop(conn, checkfirst=True)

"""SQLAlchemy ORM models.

All models are imported here so Alembic can discover them for autogeneration.
Do not remove any import — Alembic needs them all to detect schema changes.
"""

from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.district import District
from app.models.employer_validation import EmployerValidation
from app.models.enums import (
    AlertGenerator,
    AlertTargetRole,
    CourseStatus,
    GapStatus,
    GapType,
    JobSource,
    OverrideStatus,
    PanelRoleType,
    ReviewDecision,
    ReviewTrack,
    UserRole,
    VoteChoice,
)
from app.models.flag_annotation import FlagAnnotation
from app.models.institute import Institute
from app.models.job_posting import JobPosting
from app.models.panel_member import PanelMember
from app.models.panel_review import PanelReview
from app.models.panel_vote import PanelVote
from app.models.refresh_token import RefreshToken
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.models.trainee_profile import TraineeProfile
from app.models.trainer_refresher_request import TrainerRefresherRequest
from app.models.user import User

__all__ = [
    "Alert",
    "AlertGenerator",
    "AlertTargetRole",
    "AuditLog",
    "Course",
    "CourseStatus",
    "District",
    "EmployerValidation",
    "FlagAnnotation",
    "GapStatus",
    "GapType",
    "Institute",
    "JobPosting",
    "JobSource",
    "OverrideStatus",
    "PanelMember",
    "PanelReview",
    "PanelRoleType",
    "PanelVote",
    "RefreshToken",
    "ReviewDecision",
    "ReviewTrack",
    "SkillGap",
    "Trade",
    "TraineeProfile",
    "TrainerRefresherRequest",
    "User",
    "UserRole",
    "VoteChoice",
]

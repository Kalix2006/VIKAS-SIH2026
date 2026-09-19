"""PostgreSQL ENUM types used across the VIKAS schema.

These Python enums map 1:1 to PostgreSQL ENUM types.
Never rename values without a migration — the DB stores these as strings.
"""

import enum


def enum_values(cls: type[enum.Enum]) -> list[str]:
    """Return enum member values for SQLAlchemy Enum values_callable."""
    return [str(e.value) for e in cls]


class UserRole(enum.StrEnum):
    """RBAC roles. See CLAUDE.md for role descriptions."""

    TRAINEE = "trainee"
    INSTITUTE_ADMIN = "institute_admin"
    EMPLOYER = "employer"
    PLANNER = "planner"
    PANEL_MEMBER = "panel_member"


class PanelRoleType(enum.StrEnum):
    """Panel member specialization."""

    ACADEMIC_EXPERT = "academic_expert"
    INDUSTRY_PROFESSIONAL = "industry_professional"
    PROGRAM_LEAD = "program_lead"


class CourseStatus(enum.StrEnum):
    """Lifecycle status of a training course."""

    ACTIVE = "active"
    FLAGGED = "flagged"
    OBSOLETE = "obsolete"


class JobSource(enum.StrEnum):
    """External job board source."""

    ADZUNA = "adzuna"
    JOOBLE = "jooble"


class GapType(enum.StrEnum):
    """Classification of detected skill gaps."""

    CURRICULUM_DRIFT = "curriculum_drift"
    OVERSUPPLY = "oversupply"
    UNDERSUPPLY = "undersupply"
    EMERGING_SKILL = "emerging_skill"


class GapStatus(enum.StrEnum):
    """Workflow status of a skill gap through the review pipeline."""

    DETECTED = "detected"
    PANEL_QUEUE = "panel_queue"
    URGENT_ESCALATION = "urgent_escalation"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewTrack(enum.StrEnum):
    """Panel review urgency track."""

    URGENT = "urgent"
    STANDARD = "standard"


class ReviewDecision(enum.StrEnum):
    """Panel review outcome."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VoteChoice(enum.StrEnum):
    """Individual panel member vote."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class AlertTargetRole(enum.StrEnum):
    """Roles that can receive alerts."""

    TRAINEE = "trainee"
    INSTITUTE_ADMIN = "institute_admin"
    PLANNER = "planner"


class AlertGenerator(enum.StrEnum):
    """How the alert message was generated."""

    TEMPLATE = "template"
    GROQ = "groq"


class OverrideStatus(enum.StrEnum):
    """Planner's override decision on a flagged skill gap."""

    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"

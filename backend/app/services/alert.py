"""Alert service for notifications to trainees and institute admins.

Provides deterministic template-based alerts and optional Groq-generated
plain-language phrasing with a mandatory graceful fallback.
Raw numeric scores (gap_score, nlp_confidence) are strictly hidden from trainees.
"""

import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.alert import Alert
from app.models.enums import AlertGenerator, AlertTargetRole, GapType, UserRole
from app.models.skill_gap import SkillGap
from app.models.user import User

logger = logging.getLogger("vikas.alert")


def get_demand_label(gap_score: float, gap_type: GapType | None) -> tuple[str, str]:
    """Map gap score and type to plain-language demand label and badge level.

    Returns:
        (label, level):
          label: User-facing descriptive copy.
          level: "high", "caution", "stable", or "emerging".
    """
    if gap_type == GapType.UNDERSUPPLY:
        return "Strong local demand", "high"
    if gap_type == GapType.OVERSUPPLY:
        return "High competition", "caution"
    if gap_type == GapType.CURRICULUM_DRIFT:
        return "Evolving industry skills", "stable"
    if gap_type == GapType.EMERGING_SKILL:
        return "Emerging local demand", "emerging"

    if gap_score >= 35.0:
        return "Strong local demand", "high"
    if gap_score >= 20.0:
        return "Moderate local demand", "stable"
    return "Stable local demand", "stable"


class AlertService:
    """Creates alerts when skill gaps are approved or flagged."""

    async def generate_alert_text(
        self,
        target_role: AlertTargetRole,
        trade_name: str,
        district_name: str,
        gap_type: GapType,
        template_text: str,
    ) -> tuple[str, AlertGenerator]:
        """Generate empathetic alert text via Groq with mandatory fallback."""
        if not settings.groq_api_key or settings.groq_api_key.startswith("dummy"):
            return template_text, AlertGenerator.TEMPLATE

        if target_role == AlertTargetRole.TRAINEE:
            role_prompt = (
                "Write a supportive, concise (under 30 words) career "
                "notification for a vocational trainee in India. "
                "Never use numeric scores or alarming bureaucratic jargon."
            )
        else:
            role_prompt = (
                "Write a clear, actionable administrative alert "
                "(under 30 words) for an ITI institute principal."
            )

        system_message = (
            "You are VIKAS, the Viksit India Kaushal Alignment System "
            "alert generator. Return only the notification message text "
            "without quotes or preamble."
        )

        user_message = (
            f"{role_prompt}\n"
            f"Trade: {trade_name}\n"
            f"District: {district_name}\n"
            f"Alignment Status: {gap_type.value}\n"
        )

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(
                    f"{settings.groq_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": 80,
                        "temperature": 0.3,
                    },
                )
                if response.status_code == 200:
                    data: dict[str, Any] = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content: str = (
                            choices[0].get("message", {}).get("content", "").strip()
                        )
                        if content:
                            return content, AlertGenerator.GROQ

                logger.warning(
                    "Groq alert API returned %d, falling back to template",
                    response.status_code,
                )
        except Exception as exc:
            logger.warning(
                "Groq alert generation failed (%s: %s), using template",
                type(exc).__name__,
                exc,
            )

        return template_text, AlertGenerator.TEMPLATE

    async def create_gap_approved_alerts(
        self, db: AsyncSession, skill_gap: SkillGap
    ) -> list[Alert]:
        """Create alerts for institute admins and trainees in the district.

        Always falls back gracefully to templates if Groq is unavailable.
        """
        # Load trade and district names if available
        stmt = (
            select(SkillGap)
            .where(SkillGap.id == skill_gap.id)
            .options(
                selectinload(SkillGap.trade),
                selectinload(SkillGap.district),
            )
        )
        loaded_gap = (await db.execute(stmt)).scalar_one_or_none() or skill_gap
        trade_name = loaded_gap.trade.name if loaded_gap.trade else "Vocational Trade"
        district_name = (
            loaded_gap.district.name if loaded_gap.district else "your district"
        )

        # Find users in the district
        users_query = select(User).where(
            User.district_id == skill_gap.district_id,
            User.role.in_([UserRole.INSTITUTE_ADMIN, UserRole.TRAINEE]),
        )
        target_users = list((await db.execute(users_query)).scalars().all())

        created_alerts: list[Alert] = []

        for user in target_users:
            if user.role == UserRole.INSTITUTE_ADMIN:
                target_role = AlertTargetRole.INSTITUTE_ADMIN
                template_text = (
                    f"Curriculum Alignment Notice: Skill gap detected for {trade_name} "
                    f"in {district_name} ({skill_gap.gap_type.value}). "
                    "Please review training capacity and syllabus alignment."
                )
            else:
                target_role = AlertTargetRole.TRAINEE
                # Never expose raw scores to trainees
                demand_label, _ = get_demand_label(
                    skill_gap.gap_score, skill_gap.gap_type
                )
                template_text = (
                    f"Career Guidance: Local employers in {district_name} show "
                    f"{demand_label.lower()} for {trade_name} skills. "
                    "Check current course offerings to align your training."
                )

            message, generated_by = await self.generate_alert_text(
                target_role=target_role,
                trade_name=trade_name,
                district_name=district_name,
                gap_type=skill_gap.gap_type,
                template_text=template_text,
            )

            alert = Alert(
                target_role=target_role,
                target_id=user.id,
                skill_gap_id=skill_gap.id,
                message=message,
                generated_by=generated_by,
                reviewed=False,
            )
            db.add(alert)
            created_alerts.append(alert)

        await db.commit()
        logger.info(
            "Created %d alerts (%s) for approved skill gap %s",
            len(created_alerts),
            created_alerts[0].generated_by.value if created_alerts else "none",
            skill_gap.id,
        )
        return created_alerts


# Singleton instance
alert_service = AlertService()

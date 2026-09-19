"""End-to-End Pipeline Demonstration Script for VIKAS.

Executes the full pipeline:
Ingest Mock Jobs -> spaCy NLP Extraction -> SentenceTransformer Scoring
-> Threshold Routing -> Panel Voting -> Final Approval & Alert Generation.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, select

from app.db.session import async_session_maker
from app.models.alert import Alert
from app.models.district import District
from app.models.enums import GapStatus, VoteChoice
from app.models.job_posting import JobPosting
from app.models.panel_member import PanelMember
from app.models.skill_gap import SkillGap
from app.models.trade import Trade
from app.services.ingestion import IngestionService
from app.services.nlp import nlp_service
from app.services.panel import panel_service
from app.services.scoring import (
    CURRICULUM_SKILL_PROFILES,
    calculate_gap_score,
    scoring_service,
)


async def run_pipeline() -> None:
    print("=" * 80)
    print("VIKAS CORE INTELLIGENCE PIPELINE: END-TO-END DEMONSTRATION")
    print("=" * 80)

    async with async_session_maker() as session:
        # 1. Fetch reference District and Trade
        d_stmt = select(District).where(District.name == "Pune")
        district = (await session.execute(d_stmt)).scalars().first()

        t_stmt = select(Trade).where(Trade.name == "Electrician")
        trade = (await session.execute(t_stmt)).scalars().first()

        if not district or not trade:
            print("Required reference data (Pune / Electrician) not found.")
            return

        print(
            f"\n[STEP 1: INGESTION] Ingesting mock jobs for "
            f"{district.name} / {trade.name}..."
        )
        # Clear existing test postings for a clean run
        await session.execute(
            delete(JobPosting).where(JobPosting.district_id == district.id)
        )
        await session.commit()

        ingest_svc = IngestionService()
        ingest_res = await ingest_svc.ingest_postings(
            db=session,
            district_id=district.id,
            trade_id=trade.id,
            use_mock=True,
        )
        print(
            f"  -> Ingested {ingest_res['ingested']} job postings "
            f"(Skipped duplicates: {ingest_res['duplicates_skipped']})"
        )

        # 2. NLP Extraction
        print(
            "\n[STEP 2: NLP EXTRACTION] Running spaCy EntityRuler skill extraction..."
        )
        parsed_count = await nlp_service.process_unparsed_postings(db=session)
        print(f"  -> Extracted trade skills from {parsed_count} raw job descriptions")

        # Fetch postings and aggregated skills
        jp_stmt = select(JobPosting).where(
            JobPosting.district_id == district.id,
            JobPosting.trade_id == trade.id,
        )
        postings = list((await session.execute(jp_stmt)).scalars().all())

        aggregated_skills: set[str] = set()
        confidences: list[float] = []
        ages: list[float] = []
        now_dt = datetime.now(UTC)

        for p in postings:
            if p.extracted_skills and "skills" in p.extracted_skills:
                aggregated_skills.update(p.extracted_skills["skills"])
                confidences.append(p.extracted_skills.get("confidence", 0.8))
            age_days = (now_dt - p.posted_at).total_seconds() / 86400.0
            ages.append(max(0.0, age_days))

        market_skills = sorted(list(aggregated_skills))
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
        avg_age = sum(ages) / len(ages) if ages else 7.0

        # We simulate a regional volume of 65 openings for this high-demand trade
        simulated_volume = 65

        print("  -> Extracted Market Skills:")
        print(f"     ({len(market_skills)} unique): {market_skills}")
        print(f"  -> Mean NLP Confidence: {avg_confidence:.2f}")

        # 3. Scoring
        print("\n[STEP 3: SCORING] Computing embeddings & formula...")
        curriculum = CURRICULUM_SKILL_PROFILES.get("Electrician", [])
        similarity = scoring_service.compute_similarity(curriculum, market_skills)

        gap_score, gap_type, breakdown = calculate_gap_score(
            similarity=similarity,
            volume=simulated_volume,
            avg_age_days=avg_age,
            seats_available=40,
        )

        print(f"  -> Cosine Similarity: {similarity:.4f}")
        print(f"  -> Computed Gap Score: {gap_score:.2f}")
        print(f"  -> Gap Classification: {gap_type.value}")

        # Record SkillGap in database
        skill_gap = SkillGap(
            district_id=district.id,
            trade_id=trade.id,
            gap_type=gap_type,
            nlp_confidence=avg_confidence,
            job_posting_volume=simulated_volume,
            gap_score=gap_score,
            score_breakdown=breakdown,
            status=GapStatus.DETECTED,
        )
        session.add(skill_gap)
        await session.commit()
        await session.refresh(skill_gap)
        print(
            f"  -> Created SkillGap record (ID: {skill_gap.id}) with status 'detected'"
        )

        # 4. Threshold Routing
        print("\n[STEP 4: THRESHOLD ROUTING] Evaluating against thresholds...")
        review = await panel_service.route_skill_gap(session, skill_gap)
        await session.refresh(skill_gap)
        print(
            f"  -> Routed to track: {review.track.value.upper()} "
            f"(Required Signoffs: {review.required_signoffs})"
        )
        print(f"  -> Updated SkillGap status to: '{skill_gap.status.value}'")

        # 5. Panel Voting
        print("\n[STEP 5: PANEL VOTING] Simulating panel member review signoffs...")
        pm_stmt = select(PanelMember).where(PanelMember.active.is_(True)).limit(2)
        panel_members = list((await session.execute(pm_stmt)).scalars().all())

        for idx, pm in enumerate(panel_members, 1):
            vote, updated_rev = await panel_service.cast_vote(
                db=session,
                review_id=review.id,
                voter_user_id=pm.user_id,
                vote=VoteChoice.APPROVE,
                comment=f"Signoff #{idx} - Demand alignment confirmed by panelist.",
            )
            print(
                f"  -> Panel Member {pm.user_id} voted APPROVE "
                f"(Current decision: {updated_rev.decision.value})"
            )

        await session.refresh(skill_gap)
        await session.refresh(review)

        # 6. Query and display final results
        alerts_stmt = select(Alert).where(Alert.skill_gap_id == skill_gap.id)
        created_alerts = list((await session.execute(alerts_stmt)).scalars().all())

        print("\n" + "=" * 80)
        print("FINAL RESULTS: APPROVED SKILL GAP RECORD")
        print("=" * 80)
        print(f"Skill Gap ID:        {skill_gap.id}")
        print(f"District:            {district.name} ({district.state})")
        print(f"Trade:               {trade.name} (NSQF: {trade.nsqf_code})")
        print(f"Status:              {skill_gap.status.value.upper()}")
        print(f"Gap Score:           {skill_gap.gap_score}")
        print(f"Gap Type:            {skill_gap.gap_type.value}")
        print(f"NLP Confidence:      {skill_gap.nlp_confidence:.4f}")
        print(f"Job Posting Volume:  {skill_gap.job_posting_volume}")
        print(f"Resolved At:         {skill_gap.resolved_at}")
        print(
            f"Review Decision:     {review.decision.value.upper()} "
            f"(Veto Used: {review.veto_used})"
        )
        print(f"Alerts Triggered:    {len(created_alerts)} notifications dispatched")
        print("\nSCORE BREAKDOWN JSON (Defensible Audit Trail):")
        print(json.dumps(skill_gap.score_breakdown, indent=2))
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_pipeline())

"""Tests for ingestion service, budget tracking, deduplication, and mock loading."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.district import District
from app.models.job_posting import JobPosting
from app.models.trade import Trade
from app.services.ingestion import (
    BudgetExceededError,
    CallBudgetTracker,
    IngestionService,
)


def test_budget_tracker_records_calls_and_warns() -> None:
    """Budget tracker tracks call counts and detects warning threshold at 80%."""
    tracker = CallBudgetTracker(monthly_budget=10, warning_threshold=0.8)

    assert tracker.can_make_call() is True
    assert tracker.remaining_quota == 10

    # Make 7 calls (70% - no warning)
    for _ in range(7):
        tracker.record_call()
    status = tracker.get_status()
    assert status["calls_used"] == 7
    assert status["remaining_quota"] == 3
    assert status["warning_active"] is False

    # 8th call (80% - warning threshold reached)
    tracker.record_call()
    status = tracker.get_status()
    assert status["calls_used"] == 8
    assert status["warning_active"] is True

    # Fill to 10 calls
    tracker.record_call()
    tracker.record_call()
    assert tracker.can_make_call() is False

    # 11th call raises BudgetExceededError
    with pytest.raises(BudgetExceededError):
        tracker.record_call()


@pytest.mark.asyncio
async def test_mock_ingestion_and_deduplication(db_session: AsyncSession) -> None:
    """Ingesting from mock fixtures inserts postings and skips
    duplicates on second run.
    """
    # Ensure district and trade exist for testing
    d_query = select(District).where(District.name == "Pune")
    dist = (await db_session.execute(d_query)).scalars().first()
    if not dist:
        dist = District(
            name="Pune",
            state="Maharashtra",
            centroid_lat=18.52,
            centroid_lng=73.85,
        )
        db_session.add(dist)
        await db_session.flush()

    t_query = select(Trade).where(Trade.name == "Electrician")
    trade = (await db_session.execute(t_query)).scalars().first()
    if not trade:
        trade = Trade(name="Electrician", nsqf_code="ELE-TEST-99")
        db_session.add(trade)
        await db_session.flush()

    await db_session.commit()

    # Clear any previous test postings for this district to ensure a clean first run
    from sqlalchemy import delete

    await db_session.execute(
        delete(JobPosting).where(JobPosting.district_id == dist.id)
    )
    await db_session.commit()

    service = IngestionService()

    # First ingestion run
    result1 = await service.ingest_postings(
        db=db_session,
        district_id=dist.id,
        trade_id=trade.id,
        use_mock=True,
    )
    assert result1["total_processed"] > 0
    assert result1["ingested"] > 0
    initial_ingested = result1["ingested"]

    # Second ingestion run with same mock data -> should be deduplicated
    result2 = await service.ingest_postings(
        db=db_session,
        district_id=dist.id,
        trade_id=trade.id,
        use_mock=True,
    )
    assert result2["ingested"] == 0
    assert result2["duplicates_skipped"] == initial_ingested

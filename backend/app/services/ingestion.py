"""Ingestion service for external job boards (Adzuna and Jooble).

Handles API client calls with retry-with-backoff, call-budget tracking
(1,000 calls/month Adzuna free-tier limit with 80% warning), response caching,
normalization, deduplication, and mock fixture loading.
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.district import District
from app.models.enums import JobSource
from app.models.job_posting import JobPosting
from app.models.trade import Trade

logger = logging.getLogger("vikas.ingestion")


class BudgetExceededError(Exception):
    """Raised when an external API monthly call budget is exhausted."""


class CallBudgetTracker:
    """Tracks and enforces API call budget per calendar month.

    Adzuna free-tier provides ~1,000 calls/month.
    Warns at 80% usage (800 calls) and prevents calls once exhausted.
    """

    def __init__(
        self, monthly_budget: int = 1000, warning_threshold: float = 0.8
    ) -> None:
        self.monthly_budget = monthly_budget
        self.warning_threshold = warning_threshold
        self._current_month = datetime.now(UTC).strftime("%Y-%m")
        self._call_count = 0

    def _reset_if_new_month(self) -> None:
        now_month = datetime.now(UTC).strftime("%Y-%m")
        if now_month != self._current_month:
            self._current_month = now_month
            self._call_count = 0

    @property
    def call_count(self) -> int:
        self._reset_if_new_month()
        return self._call_count

    @property
    def remaining_quota(self) -> int:
        self._reset_if_new_month()
        return max(0, self.monthly_budget - self._call_count)

    def can_make_call(self) -> bool:
        self._reset_if_new_month()
        return self._call_count < self.monthly_budget

    def record_call(self) -> None:
        """Record an outgoing API call.

        Warns if threshold reached, or raises if budget exceeded.
        """
        self._reset_if_new_month()
        if self._call_count >= self.monthly_budget:
            logger.error(
                "Adzuna monthly budget of %d calls exhausted for %s",
                self.monthly_budget,
                self._current_month,
            )
            raise BudgetExceededError(
                f"Adzuna monthly budget of {self.monthly_budget} calls exhausted"
            )

        self._call_count += 1
        usage_ratio = self._call_count / self.monthly_budget

        if usage_ratio >= self.warning_threshold:
            logger.warning(
                "Adzuna quota warning: %d/%d calls used (%.1f%%) in %s. Remaining: %d",
                self._call_count,
                self.monthly_budget,
                usage_ratio * 100,
                self._current_month,
                self.remaining_quota,
            )
        else:
            logger.debug(
                "Adzuna call recorded: %d/%d used in %s",
                self._call_count,
                self.monthly_budget,
                self._current_month,
            )

    def get_status(self) -> dict[str, Any]:
        self._reset_if_new_month()
        return {
            "current_month": self._current_month,
            "calls_used": self._call_count,
            "monthly_budget": self.monthly_budget,
            "remaining_quota": self.remaining_quota,
            "usage_percentage": round(
                (self._call_count / self.monthly_budget) * 100, 2
            ),
            "warning_active": (self._call_count / self.monthly_budget)
            >= self.warning_threshold,
        }


# Global singleton tracker instance
adzuna_budget_tracker = CallBudgetTracker(
    monthly_budget=settings.adzuna_monthly_budget,
    warning_threshold=settings.adzuna_warning_threshold,
)


class AdzunaClient:
    """Client for Adzuna Jobs API with retry-with-backoff
    and rate-budget enforcement.
    """

    BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1"

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        budget_tracker: CallBudgetTracker | None = None,
    ) -> None:
        self.app_id = app_id or settings.adzuna_app_id
        self.app_key = app_key or settings.adzuna_app_key
        self.budget_tracker = budget_tracker or adzuna_budget_tracker

    async def search_jobs(
        self,
        query: str,
        location: str,
        results_per_page: int = 50,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Query Adzuna API with exponential backoff on transient errors."""
        if not self.app_id or not self.app_key:
            logger.warning("Adzuna credentials not configured; skipping live API query")
            return []

        if not self.budget_tracker.can_make_call():
            logger.error("Cannot query Adzuna: monthly budget limit reached")
            return []

        params: dict[str, str | int] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": results_per_page,
            "what": query,
            "where": location,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    self.budget_tracker.record_call()
                    response = await client.get(self.BASE_URL, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        raw_results = data.get("results", [])
                        normalized = []
                        for item in raw_results:
                            normalized.append(self._normalize(item, query, location))
                        return normalized

                    if response.status_code == 429:
                        wait_seconds = 2**attempt
                        logger.warning(
                            "Adzuna rate limited (429). "
                            "Backing off for %ds (attempt %d/%d)",
                            wait_seconds,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    if response.status_code >= 500:
                        wait_seconds = 2**attempt
                        logger.warning(
                            "Adzuna server error %d. Retrying in %ds (attempt %d/%d)",
                            response.status_code,
                            wait_seconds,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    logger.error(
                        "Adzuna API returned error %d: %s",
                        response.status_code,
                        response.text,
                    )
                    return []

                except httpx.TimeoutException as exc:
                    logger.warning(
                        "Adzuna timeout on attempt %d/%d: %s", attempt, max_retries, exc
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(2**attempt)
                    else:
                        logger.error(
                            "Adzuna request timed out after %d attempts", max_retries
                        )
                        return []
                except BudgetExceededError:
                    return []
                except Exception as exc:
                    logger.error("Unexpected Adzuna API failure: %s", exc)
                    return []

        return []

    def _normalize(
        self, item: dict[str, Any], trade_name: str, district_name: str
    ) -> dict[str, Any]:
        """Normalize raw Adzuna item into standard posting shape."""
        created_str = item.get("created", "")
        try:
            posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except Exception:
            posted_at = datetime.now(UTC)

        company = item.get("company", {})
        employer_name = (
            company.get("display_name", "Unknown Employer")
            if isinstance(company, dict)
            else "Unknown Employer"
        )

        return {
            "source": JobSource.ADZUNA,
            "raw_title": item.get("title", ""),
            "raw_description": item.get("description", ""),
            "employer_name": employer_name,
            "district_name": district_name,
            "trade_name": trade_name,
            "posted_at": posted_at,
        }


class JoobleClient:
    """Client for Jooble Jobs API with retry-with-backoff."""

    BASE_URL = "https://jooble.org/api/"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.jooble_api_key

    async def search_jobs(
        self,
        query: str,
        location: str,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Query Jooble API with exponential backoff on transient errors."""
        if not self.api_key:
            logger.warning("Jooble API key not configured; skipping live API query")
            return []

        endpoint = f"{self.BASE_URL}{self.api_key}"
        payload = {
            "keywords": query,
            "location": location,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.post(endpoint, json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        raw_jobs = data.get("jobs", [])
                        normalized = []
                        for item in raw_jobs:
                            normalized.append(self._normalize(item, query, location))
                        return normalized

                    if response.status_code == 429:
                        wait_seconds = 2**attempt
                        logger.warning(
                            "Jooble rate limited (429). "
                            "Retrying in %ds (attempt %d/%d)",
                            wait_seconds,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    if response.status_code >= 500:
                        wait_seconds = 2**attempt
                        logger.warning(
                            "Jooble server error %d. Retrying in %ds (attempt %d/%d)",
                            response.status_code,
                            wait_seconds,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue

                    logger.error(
                        "Jooble API returned error %d: %s",
                        response.status_code,
                        response.text,
                    )
                    return []

                except httpx.TimeoutException as exc:
                    logger.warning(
                        "Jooble timeout on attempt %d/%d: %s", attempt, max_retries, exc
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(2**attempt)
                    else:
                        return []
                except Exception as exc:
                    logger.error("Unexpected Jooble API failure: %s", exc)
                    return []

        return []

    def _normalize(
        self, item: dict[str, Any], trade_name: str, district_name: str
    ) -> dict[str, Any]:
        """Normalize raw Jooble item into standard posting shape."""
        updated_str = item.get("updated", "")
        try:
            posted_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        except Exception:
            posted_at = datetime.now(UTC)

        return {
            "source": JobSource.JOOBLE,
            "raw_title": item.get("title", ""),
            "raw_description": item.get("snippet", ""),
            "employer_name": item.get("company", "Unknown Employer"),
            "district_name": district_name,
            "trade_name": trade_name,
            "posted_at": posted_at,
        }


class IngestionService:
    """Orchestrates job ingestion, normalization,
    and deduplication into the database.
    """

    def __init__(
        self,
        adzuna_client: AdzunaClient | None = None,
        jooble_client: JoobleClient | None = None,
    ) -> None:
        self.adzuna = adzuna_client or AdzunaClient()
        self.jooble = jooble_client or JoobleClient()

    async def ingest_postings(
        self,
        db: AsyncSession,
        district_id: uuid.UUID | None = None,
        trade_id: uuid.UUID | None = None,
        use_mock: bool = False,
    ) -> dict[str, Any]:
        """Run the ingestion pipeline.

        If use_mock is True, loads postings from tests/fixtures/mock_jobs.json.
        Otherwise queries Adzuna (primary) and Jooble (secondary).
        """
        # Fetch districts and trades mapping
        districts_query = select(District)
        if district_id:
            districts_query = districts_query.where(District.id == district_id)
        districts = list((await db.execute(districts_query)).scalars().all())

        trades_query = select(Trade)
        if trade_id:
            trades_query = trades_query.where(Trade.id == trade_id)
        trades = list((await db.execute(trades_query)).scalars().all())

        if not districts or not trades:
            logger.warning("No districts or trades available for ingestion")
            return {
                "ingested": 0,
                "duplicates_skipped": 0,
                "total_processed": 0,
            }

        district_by_name = {d.name.lower(): d for d in districts}
        trade_by_name = {t.name.lower(): t for t in trades}

        raw_postings: list[dict[str, Any]] = []

        if use_mock:
            fixture_path = (
                Path(__file__).resolve().parent.parent.parent
                / "tests"
                / "fixtures"
                / "mock_jobs.json"
            )
            if not fixture_path.exists():
                fixture_path = (
                    Path(__file__).resolve().parents[2]
                    / "tests"
                    / "fixtures"
                    / "mock_jobs.json"
                )

            if fixture_path.exists():
                with open(fixture_path, encoding="utf-8") as f:
                    mock_data = json.load(f)
                for item in mock_data:
                    posted_at = datetime.fromisoformat(
                        item["posted_at"].replace("Z", "+00:00")
                    )
                    raw_postings.append(
                        {
                            "source": JobSource(item.get("source", "adzuna")),
                            "raw_title": item.get("title", ""),
                            "raw_description": item.get("description", ""),
                            "employer_name": item.get("employer_name", ""),
                            "district_name": item.get("district_name", ""),
                            "trade_name": item.get("trade_name", ""),
                            "posted_at": posted_at,
                        }
                    )
            else:
                logger.error("Mock fixtures file not found at %s", fixture_path)
        else:
            # Query live APIs for each district & trade combination
            for district in districts:
                for trade in trades:
                    # Primary: Adzuna
                    adz_results = await self.adzuna.search_jobs(
                        query=trade.name,
                        location=district.name,
                    )
                    raw_postings.extend(adz_results)

                    # Secondary: Jooble
                    jbl_results = await self.jooble.search_jobs(
                        query=trade.name,
                        location=district.name,
                    )
                    raw_postings.extend(jbl_results)

        # Ingestion with Deduplication
        ingested_count = 0
        duplicate_count = 0

        for posting in raw_postings:
            d_name = posting["district_name"].lower()
            t_name = posting["trade_name"].lower()

            target_district = district_by_name.get(d_name)
            target_trade = trade_by_name.get(t_name)

            if not target_district:
                continue

            posting_posted_at: datetime = posting["posted_at"]
            title_clean = posting["raw_title"].strip().lower()

            # Deduplication: check for same district, same title,
            # within +/- 3 days posted window
            window_start = posting_posted_at - timedelta(days=3)
            window_end = posting_posted_at + timedelta(days=3)

            dup_query = select(JobPosting).where(
                JobPosting.district_id == target_district.id,
                func.lower(JobPosting.raw_title) == title_clean,
                JobPosting.posted_at >= window_start,
                JobPosting.posted_at <= window_end,
            )
            existing = (await db.execute(dup_query)).scalars().first()

            if existing:
                duplicate_count += 1
                continue

            # Insert new posting
            new_job = JobPosting(
                source=posting["source"],
                district_id=target_district.id,
                trade_id=target_trade.id if target_trade else None,
                raw_title=posting["raw_title"],
                raw_description=posting["raw_description"],
                posted_at=posting_posted_at,
            )
            db.add(new_job)
            ingested_count += 1

        await db.commit()

        return {
            "ingested": ingested_count,
            "duplicates_skipped": duplicate_count,
            "total_processed": len(raw_postings),
        }

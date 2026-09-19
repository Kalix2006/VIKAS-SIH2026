"""Standalone CLI script for job posting ingestion.

Usage:
    python scripts/ingest_jobs.py --mock
    python scripts/ingest_jobs.py --district Pune --trade Electrician
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.district import District
from app.models.trade import Trade
from app.services.ingestion import IngestionService, adzuna_budget_tracker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("vikas.cli.ingest")


async def run_cli(args: argparse.Namespace) -> None:
    service = IngestionService()

    async with async_session_maker() as session:
        district_id = None
        if args.district:
            d_query = select(District).where(District.name.ilike(args.district))
            district = (await session.execute(d_query)).scalars().first()
            if district:
                district_id = district.id
            else:
                logger.error("District '%s' not found.", args.district)
                return

        trade_id = None
        if args.trade:
            t_query = select(Trade).where(Trade.name.ilike(f"%{args.trade}%"))
            trade = (await session.execute(t_query)).scalars().first()
            if trade:
                trade_id = trade.id
            else:
                logger.error("Trade '%s' not found.", args.trade)
                return

        logger.info(
            "Starting ingestion job (mock=%s, district=%s, trade=%s)",
            args.mock,
            args.district or "ALL",
            args.trade or "ALL",
        )

        result = await service.ingest_postings(
            db=session,
            district_id=district_id,
            trade_id=trade_id,
            use_mock=args.mock,
        )

        logger.info("Ingestion completed:")
        logger.info("  - Processed: %d", result["total_processed"])
        logger.info("  - Ingested: %d", result["ingested"])
        logger.info("  - Duplicates Skipped: %d", result["duplicates_skipped"])

        budget_status = adzuna_budget_tracker.get_status()
        logger.info(
            "Adzuna Quota Status: %d/%d calls used (Remaining: %d)",
            budget_status["calls_used"],
            budget_status["monthly_budget"],
            budget_status["remaining_quota"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest job postings into VIKAS database."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use local mock fixtures instead of calling live external APIs",
    )
    parser.add_argument(
        "--district", type=str, help="Filter by district name (e.g., Pune)"
    )
    parser.add_argument(
        "--trade", type=str, help="Filter by trade name (e.g., Electrician)"
    )

    parsed_args = parser.parse_args()
    asyncio.run(run_cli(parsed_args))


if __name__ == "__main__":
    main()


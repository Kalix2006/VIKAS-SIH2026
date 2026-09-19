"""Internal administration and pipeline trigger endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.schemas.ingest import IngestRequest, IngestResponse
from app.schemas.panel import PanelReviewResponse
from app.services.ingestion import IngestionService
from app.services.nlp import nlp_service
from app.services.panel import panel_service

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_role("planner"))],
)


@router.post("/ingest/run", response_model=IngestResponse)
async def run_ingestion(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: IngestRequest | None = None,
) -> IngestResponse:
    """Trigger external job posting ingestion and NLP skill extraction.

    Supports mock fixture mode for testing without exhausting API quotas.
    """
    req = payload or IngestRequest()
    ingestion_svc = IngestionService()

    ingest_result = await ingestion_svc.ingest_postings(
        db=db,
        district_id=req.district_id,
        trade_id=req.trade_id,
        use_mock=req.mock,
    )

    # Process NLP skill extraction for unparsed postings
    parsed_count = await nlp_service.process_unparsed_postings(db=db)

    message = (
        f"Ingestion finished: {ingest_result['ingested']} new postings ingested, "
        f"{ingest_result['duplicates_skipped']} duplicates skipped, "
        f"{parsed_count} postings parsed with spaCy NLP."
    )

    return IngestResponse(
        ingested=ingest_result["ingested"],
        duplicates_skipped=ingest_result["duplicates_skipped"],
        total_processed=ingest_result["total_processed"],
        message=message,
    )


@router.post("/panel/route", response_model=list[PanelReviewResponse])
async def route_panel_reviews(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Apply threshold routing to any skill_gaps still in 'detected' status.

    Gaps crossing MIN_CONFIDENCE_THRESHOLD (0.75) and HIGH_VOLUME_THRESHOLD (50)
    are routed to urgent track (2 signoffs). Others are routed to standard
    track (4 signoffs).
    """
    reviews = await panel_service.route_all_detected_gaps(db=db)
    return reviews

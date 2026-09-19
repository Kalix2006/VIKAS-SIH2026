"""Pydantic schemas for internal ingestion endpoints."""

import uuid

from pydantic import BaseModel, ConfigDict


class IngestRequest(BaseModel):
    """POST /internal/ingest/run request body."""

    model_config = ConfigDict(extra="forbid")

    district_id: uuid.UUID | None = None
    trade_id: uuid.UUID | None = None
    mock: bool = False


class IngestResponse(BaseModel):
    """POST /internal/ingest/run response body."""

    ingested: int
    duplicates_skipped: int
    total_processed: int
    message: str

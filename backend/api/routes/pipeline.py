"""
Vision — Databank Pipeline API Routes.

Trigger processing of uploaded SAM.gov databank batches:
feed qualifying notices into the existing solicitation pipeline.

POST /api/pipeline/process-batch    — process a batch (supports dry_run)
POST /api/pipeline/reset-batch      — reset a batch for re-processing
GET  /api/pipeline/batch-status     — get processing status for a batch
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from core.pipeline import PipelineProcessor, get_batch_status

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_processor = PipelineProcessor()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ProcessBatchRequest(BaseModel):
    batch_id: str
    dry_run: bool = False


class ResetBatchRequest(BaseModel):
    batch_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/process-batch")
def process_batch_endpoint(
    body: ProcessBatchRequest,
    user: dict = Depends(get_current_user),
):
    """Process unprocessed rows in a SAM.gov databank upload batch.

    Applies business filters (NAICS category, set-aside, urgency,
    opportunity type) and creates solicitations for qualifying notices.
    Each created solicitation automatically enqueues a sam_fetch job.

    Set dry_run=true to preview counts without creating solicitations.
    """
    if not body.batch_id or not body.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id is required")

    try:
        results = _processor.process_batch(
            body.batch_id.strip(),
            dry_run=body.dry_run,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {exc}",
        )

    return results


@router.post("/reset-batch")
def reset_batch_endpoint(
    body: ResetBatchRequest,
    user: dict = Depends(get_current_user),
):
    """Reset processing status for all rows in a batch.

    Clears pipeline_status, category, urgency, skip_reason, and
    solicitation link. The batch can then be re-processed — useful
    after filter rule changes.

    Does NOT delete any solicitations that were already created.
    Those are protected by their own notice_id UNIQUE constraint.
    """
    if not body.batch_id or not body.batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id is required")

    try:
        reset_count = _processor.reset_batch(body.batch_id.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Batch reset failed: {exc}",
        )

    return {
        "batch_id": body.batch_id.strip(),
        "rows_reset": reset_count,
    }


@router.get("/batch-status/{batch_id}")
def batch_status_endpoint(
    batch_id: str,
    user: dict = Depends(get_current_user),
):
    """Get processing status summary for a batch.

    Returns counts for pending, queued, skipped, duplicate, and error rows.
    """
    if not batch_id or not batch_id.strip():
        raise HTTPException(status_code=400, detail="batch_id is required")

    try:
        status = get_batch_status(batch_id.strip())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch status: {exc}",
        )

    return {
        "batch_id": batch_id.strip(),
        **status,
    }

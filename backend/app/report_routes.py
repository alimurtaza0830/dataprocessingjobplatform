from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import get_processing_job_by_id
from app.dependencies import get_database_session
from app.schemas import ProcessingReportResponse


router = APIRouter(
    prefix="/jobs",
    tags=["Reports"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "/{job_id}/report",
    response_model=ProcessingReportResponse,
)
def get_processing_report(
    job_id: str,
    database_session: DatabaseSession,
) -> ProcessingReportResponse:
    """
    Return the generated data-quality report for a completed job.
    """
    processing_job = get_processing_job_by_id(
        database_session=database_session,
        job_id=job_id,
    )

    if processing_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found",
        )

    if processing_job.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                processing_job.error_message
                or "CSV processing failed"
            ),
        )

    if processing_job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Report is not ready. "
                f"Current status: {processing_job.status}"
            ),
        )

    if processing_job.report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Completed job does not contain a report",
        )

    return ProcessingReportResponse(
        job_id=processing_job.id,
        filename=processing_job.filename,
        status=processing_job.status,
        report=processing_job.report,
    )

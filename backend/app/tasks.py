from datetime import datetime, timezone

from app.analysis import analyze_csv
from app.database import SessionLocal
from app.models import ProcessingJob
from app.storage import UPLOAD_DIRECTORY


def process_csv_job(job_id: str) -> dict[str, str]:
    """
    Process one uploaded CSV file.

    This function will be executed by an RQ worker,
    not directly by the FastAPI request.
    """
    database_session = SessionLocal()

    try:
        processing_job = database_session.get(
            ProcessingJob,
            job_id,
        )

        if processing_job is None:
            raise ValueError(
                f"Processing job not found: {job_id}"
            )

        if not processing_job.stored_filename:
            raise ValueError(
                "Processing job does not have an uploaded file"
            )

        processing_job.status = "processing"
        processing_job.started_at = datetime.now(timezone.utc)
        processing_job.error_message = None

        database_session.commit()

        csv_path = (
            UPLOAD_DIRECTORY
            / processing_job.stored_filename
        )

        report = analyze_csv(csv_path)

        processing_job.report = report
        processing_job.status = "completed"
        processing_job.completed_at = datetime.now(timezone.utc)

        database_session.commit()

        return {
            "job_id": processing_job.id,
            "status": processing_job.status,
        }

    except Exception as error:
        database_session.rollback()

        processing_job = database_session.get(
            ProcessingJob,
            job_id,
        )

        if processing_job is not None:
            processing_job.status = "failed"
            processing_job.error_message = str(error)
            processing_job.completed_at = datetime.now(timezone.utc)

            database_session.commit()

        raise

    finally:
        database_session.close()

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcessingJob
from app.schemas import ProcessingJobCreate


def create_processing_job(
    database_session: Session,
    job_data: ProcessingJobCreate,
) -> ProcessingJob:
    """
    Create a job record without uploading a file.
    """
    processing_job = ProcessingJob(
        filename=job_data.filename,
        status="pending",
    )

    database_session.add(processing_job)
    database_session.commit()
    database_session.refresh(processing_job)

    return processing_job


def create_uploaded_processing_job(
    database_session: Session,
    original_filename: str,
    stored_filename: str,
    file_size_bytes: int,
) -> ProcessingJob:
    """
    Create a job record for an uploaded CSV file.
    """
    processing_job = ProcessingJob(
        filename=original_filename,
        stored_filename=stored_filename,
        file_size_bytes=file_size_bytes,
        status="pending",
    )

    database_session.add(processing_job)
    database_session.commit()
    database_session.refresh(processing_job)

    return processing_job


def get_processing_jobs(
    database_session: Session,
) -> list[ProcessingJob]:
    """
    Retrieve all processing jobs, newest first.
    """
    query = select(ProcessingJob).order_by(
        ProcessingJob.created_at.desc()
    )

    return list(database_session.scalars(query).all())


def get_processing_job_by_id(
    database_session: Session,
    job_id: str,
) -> ProcessingJob | None:
    """
    Retrieve one processing job by its ID.
    """
    query = select(ProcessingJob).where(
        ProcessingJob.id == job_id
    )

    return database_session.scalar(query)

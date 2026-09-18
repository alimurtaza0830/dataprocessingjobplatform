import time
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.propagate import extract

from app.analysis import analyze_csv
from app.database import SessionLocal
from app.models import ProcessingJob
from app.storage import UPLOAD_DIRECTORY
from app.worker_metrics import (
    JOB_PROCESSING_DURATION_SECONDS,
    JOBS_COMPLETED_TOTAL,
    JOBS_FAILED_TOTAL,
)


tracer = trace.get_tracer(__name__)


def process_csv_job(job_id: str, trace_context: dict[str, str] | None = None,) -> dict[str, str]:
    """
    Process one uploaded CSV file.

    This function is executed by the RQ worker,
    not directly by the FastAPI request.
    """
    parent_context = extract(
        trace_context or {}
    )
    with tracer.start_as_current_span(
        "process_csv_job",
        context=parent_context,
    ) as span:
        span.set_attribute(
            "job.id",
            job_id,
        )

        start_time = time.perf_counter()
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
            processing_job.started_at = datetime.now(
                timezone.utc
            )
            processing_job.error_message = None

            database_session.commit()

            csv_path = (
                UPLOAD_DIRECTORY
                / processing_job.stored_filename
            )

            with tracer.start_as_current_span(
                "analyze_csv"
            ):
                report = analyze_csv(csv_path)

            processing_job.report = report
            processing_job.status = "completed"
            processing_job.completed_at = datetime.now(
                timezone.utc
            )

            database_session.commit()

            JOBS_COMPLETED_TOTAL.inc()

            span.set_attribute(
                "job.status",
                "completed",
            )

            return {
                "job_id": processing_job.id,
                "status": processing_job.status,
            }

        except Exception as error:
            JOBS_FAILED_TOTAL.inc()

            span.set_attribute(
                "job.status",
                "failed",
            )

            span.set_attribute(
                "job.error",
                str(error),
            )

            database_session.rollback()

            processing_job = database_session.get(
                ProcessingJob,
                job_id,
            )

            if processing_job is not None:
                processing_job.status = "failed"
                processing_job.error_message = str(error)
                processing_job.completed_at = datetime.now(
                    timezone.utc
                )

                database_session.commit()

            raise

        finally:
            duration = (
                time.perf_counter()
                - start_time
            )

            JOB_PROCESSING_DURATION_SECONDS.observe(
                duration
            )

            span.set_attribute(
                "job.duration_seconds",
                duration,
            )

            database_session.close()
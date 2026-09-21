import os
import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.propagate import inject
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.crud import (
    create_processing_job,
    create_uploaded_processing_job,
    get_processing_job_by_id,
    get_processing_jobs,
)
from app.database import check_database_connection
from app.dependencies import get_database_session
from app.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    JOBS_UPLOADED_TOTAL,
    UPLOAD_SIZE_BYTES,
)
from app.queue import check_redis_connection, processing_queue
from app.report_routes import router as report_router
from app.schemas import ProcessingJobCreate, ProcessingJobResponse
from app.storage import UploadTooLargeError, save_uploaded_file
from app.tasks import process_csv_job
from app.tracing import configure_tracing


app = FastAPI(
    title="Data Quality Platform",
    description="Upload CSV files and generate data-quality reports.",
    version="0.1.0",
)

configure_tracing(app)

app.include_router(report_router)



allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@app.middleware("http")
async def prometheus_metrics(
    request: Request,
    call_next,
):
    start_time = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start_time

    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
    ).inc()

    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=request.method,
        path=request.url.path,
    ).observe(duration)

    return response


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/")
def application_info() -> dict[str, str]:
    return {
        "application": "Data Quality Platform",
        "purpose": "Analyze CSV files and generate data-quality reports",
        "version": app.version,
        "documentation": "/docs",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "backend-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/database")
def database_health_check() -> dict[str, str]:
    try:
        check_database_connection()

        return {
            "status": "healthy",
            "service": "postgresql",
            "message": "Backend successfully connected to PostgreSQL",
        }

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL is unavailable",
        ) from error


@app.post(
    "/jobs",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    job_data: ProcessingJobCreate,
    database_session: DatabaseSession,
) -> ProcessingJobResponse:
    processing_job = create_processing_job(
        database_session=database_session,
        job_data=job_data,
    )

    return ProcessingJobResponse.model_validate(processing_job)


@app.post(
    "/jobs/upload",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_csv_job(
    uploaded_file: Annotated[
        UploadFile,
        File(description="CSV file to analyze"),
    ],
    database_session: DatabaseSession,
) -> ProcessingJobResponse:
    """
    Save an uploaded CSV, create its database record,
    and send the job to the Redis processing queue.
    """
    try:
        (
            original_filename,
            stored_filename,
            file_size_bytes,
        ) = save_uploaded_file(uploaded_file)

    except UploadTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    finally:
        uploaded_file.file.close()

    processing_job = create_uploaded_processing_job(
        database_session=database_session,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size_bytes=file_size_bytes,
    )

    try:
        trace_context: dict[str, str] = {}
        inject(trace_context)

        processing_queue.enqueue(
            process_csv_job,
            processing_job.id,
            trace_context=trace_context,
        )

    except RedisError as error:
        processing_job.status = "failed"
        processing_job.error_message = (
            "The processing job could not be sent to Redis"
        )

        database_session.commit()
        database_session.refresh(processing_job)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Processing queue is unavailable",
        ) from error

    JOBS_UPLOADED_TOTAL.inc()
    UPLOAD_SIZE_BYTES.observe(file_size_bytes)

    return ProcessingJobResponse.model_validate(processing_job)


@app.get(
    "/jobs",
    response_model=list[ProcessingJobResponse],
)
def list_jobs(
    database_session: DatabaseSession,
) -> list[ProcessingJobResponse]:
    processing_jobs = get_processing_jobs(
        database_session=database_session,
    )

    return [
        ProcessingJobResponse.model_validate(job)
        for job in processing_jobs
    ]


@app.get(
    "/jobs/{job_id}",
    response_model=ProcessingJobResponse,
)
def get_job(
    job_id: str,
    database_session: DatabaseSession,
) -> ProcessingJobResponse:
    processing_job = get_processing_job_by_id(
        database_session=database_session,
        job_id=job_id,
    )

    if processing_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found",
        )

    return ProcessingJobResponse.model_validate(processing_job)


@app.get("/health/redis")
def redis_health_check() -> dict[str, str]:
    """
    Confirm that the backend can communicate with Redis.
    """
    try:
        check_redis_connection()

        return {
            "status": "healthy",
            "service": "redis",
            "message": "Backend successfully connected to Redis",
        }

    except RedisError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable",
        ) from error


@app.get("/health/ready")
def readiness_health_check() -> dict[str, object]:
    """
    Confirm that the backend and its required dependencies are ready.
    """
    dependencies = {
        "database": "healthy",
        "redis": "healthy",
    }

    try:
        check_database_connection()
    except SQLAlchemyError:
        dependencies["database"] = "unhealthy"

    try:
        check_redis_connection()
    except RedisError:
        dependencies["redis"] = "unhealthy"

    is_ready = all(
        dependency == "healthy"
        for dependency in dependencies.values()
    )

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        )

    return {
        "status": "ready",
        "service": "backend-api",
        "dependencies": dependencies,
    }

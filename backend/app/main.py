from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
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
from app.init_db import create_database_tables
from app.queue import check_redis_connection, processing_queue
from app.report_routes import router as report_router
from app.schemas import ProcessingJobCreate, ProcessingJobResponse
from app.storage import save_uploaded_file
from app.tasks import process_csv_job


@asynccontextmanager
async def lifespan(
    _: FastAPI,
) -> AsyncIterator[None]:
    """
    Ensure the application database schema exists
    before accepting requests.
    """
    create_database_tables()
    yield


app = FastAPI(
    title="Data Quality Platform",
    description="Upload CSV files and generate data-quality reports.",
    version="0.1.0",
    lifespan=lifespan,
)


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
        processing_queue.enqueue(
            process_csv_job,
            processing_job.id,
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

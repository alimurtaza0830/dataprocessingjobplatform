from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProcessingJobCreate(BaseModel):
    filename: str = Field(
        min_length=1,
        max_length=255,
        examples=["customers.csv"],
    )


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    stored_filename: str | None
    file_size_bytes: int | None
    status: str
    report: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProcessingReportResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    report: dict[str, Any]

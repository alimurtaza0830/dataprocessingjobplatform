from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import tasks
from app.database import Base
from app.models import ProcessingJob
from app.tasks import process_csv_job


@pytest.fixture
def session_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> sessionmaker[Session]:
    """
    Run the worker task against an in-memory SQLite database
    and a temporary upload directory.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    testing_session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    monkeypatch.setattr(tasks, "SessionLocal", testing_session_factory)
    monkeypatch.setattr(tasks, "UPLOAD_DIRECTORY", tmp_path)

    return testing_session_factory


def create_job(
    session_factory: sessionmaker[Session],
    stored_filename: str | None,
) -> str:
    with session_factory() as database_session:
        processing_job = ProcessingJob(
            filename="customers.csv",
            stored_filename=stored_filename,
        )
        database_session.add(processing_job)
        database_session.commit()

        return processing_job.id


def get_job(
    session_factory: sessionmaker[Session],
    job_id: str,
) -> ProcessingJob:
    with session_factory() as database_session:
        processing_job = database_session.get(ProcessingJob, job_id)

        assert processing_job is not None

        return processing_job


def test_process_csv_job_completes_and_stores_report(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    (tmp_path / "stored_customers.csv").write_text(
        "id,name,age\n"
        "1,Adam,35\n"
        "2,Sarah,\n",
        encoding="utf-8",
    )
    job_id = create_job(session_factory, "stored_customers.csv")

    result = process_csv_job(job_id)

    assert result == {"job_id": job_id, "status": "completed"}

    processing_job = get_job(session_factory, job_id)

    assert processing_job.status == "completed"
    assert processing_job.error_message is None
    assert processing_job.started_at is not None
    assert processing_job.completed_at is not None
    assert processing_job.report is not None
    assert processing_job.report["row_count"] == 2
    assert processing_job.report["total_missing_values"] == 1


def test_process_csv_job_marks_invalid_csv_as_failed(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    (tmp_path / "stored_empty.csv").write_text("", encoding="utf-8")
    job_id = create_job(session_factory, "stored_empty.csv")

    with pytest.raises(ValueError, match="empty"):
        process_csv_job(job_id)

    processing_job = get_job(session_factory, job_id)

    assert processing_job.status == "failed"
    assert "empty" in (processing_job.error_message or "")
    assert processing_job.completed_at is not None
    assert processing_job.report is None


def test_process_csv_job_marks_missing_file_as_failed(
    session_factory: sessionmaker[Session],
) -> None:
    job_id = create_job(session_factory, "does_not_exist.csv")

    with pytest.raises(FileNotFoundError):
        process_csv_job(job_id)

    processing_job = get_job(session_factory, job_id)

    assert processing_job.status == "failed"
    assert processing_job.error_message


def test_process_csv_job_fails_job_without_uploaded_file(
    session_factory: sessionmaker[Session],
) -> None:
    job_id = create_job(session_factory, None)

    with pytest.raises(ValueError, match="does not have an uploaded file"):
        process_csv_job(job_id)

    processing_job = get_job(session_factory, job_id)

    assert processing_job.status == "failed"
    assert processing_job.error_message == (
        "Processing job does not have an uploaded file"
    )


def test_process_csv_job_raises_for_unknown_job(
    session_factory: sessionmaker[Session],
) -> None:
    with pytest.raises(ValueError, match="Processing job not found"):
        process_csv_job("00000000-0000-0000-0000-000000000000")

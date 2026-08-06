import time

import httpx


BASE_URL = "http://backend:8000"


def wait_for_job_completion(
    client: httpx.Client,
    job_id: str,
    timeout_seconds: int = 15,
) -> dict:
    """
    Poll the job endpoint until the worker completes or fails the job.
    """
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        response = client.get(f"/jobs/{job_id}")
        response.raise_for_status()

        job = response.json()

        if job["status"] in {"completed", "failed"}:
            return job

        time.sleep(0.5)

    raise AssertionError(
        f"Job {job_id} did not finish within {timeout_seconds} seconds"
    )


def test_complete_csv_processing_workflow() -> None:
    csv_content = (
        "id,name,email,age\n"
        "1,Adam,adam@example.com,35\n"
        "2,Sarah,sarah@example.com,29\n"
        "3,John,,42\n"
        "2,Sarah,sarah@example.com,29\n"
    )

    with httpx.Client(
        base_url=BASE_URL,
        timeout=20,
    ) as client:
        upload_response = client.post(
            "/jobs/upload",
            files={
                "uploaded_file": (
                    "customers.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )

        assert upload_response.status_code == 201

        created_job = upload_response.json()

        assert created_job["filename"] == "customers.csv"
        assert created_job["status"] == "pending"
        assert created_job["stored_filename"] is not None
        assert created_job["file_size_bytes"] > 0

        completed_job = wait_for_job_completion(
            client=client,
            job_id=created_job["id"],
        )

        assert completed_job["status"] == "completed"
        assert completed_job["error_message"] is None
        assert completed_job["report"] is not None

        report_response = client.get(
            f"/jobs/{created_job['id']}/report"
        )

        assert report_response.status_code == 200

        report = report_response.json()["report"]

        assert report["row_count"] == 4
        assert report["column_count"] == 4
        assert report["total_missing_values"] == 1
        assert report["duplicate_rows"] == 1


def test_upload_rejects_non_csv_file() -> None:
    with httpx.Client(
        base_url=BASE_URL,
        timeout=10,
    ) as client:
        response = client.post(
            "/jobs/upload",
            files={
                "uploaded_file": (
                    "notes.txt",
                    "This is not a CSV file",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are supported"


def test_unknown_job_returns_not_found() -> None:
    with httpx.Client(
        base_url=BASE_URL,
        timeout=10,
    ) as client:
        response = client.get(
            "/jobs/unknown-job-id"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Processing job not found"


def test_readiness_endpoint() -> None:
    with httpx.Client(
        base_url=BASE_URL,
        timeout=10,
    ) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ready"
    assert body["dependencies"]["database"] == "healthy"
    assert body["dependencies"]["redis"] == "healthy"


def test_empty_csv_job_changes_to_failed() -> None:
    """
    Verify that worker errors are saved as failed jobs.
    """
    with httpx.Client(
        base_url=BASE_URL,
        timeout=20,
    ) as client:
        upload_response = client.post(
            "/jobs/upload",
            files={
                "uploaded_file": (
                    "empty.csv",
                    "",
                    "text/csv",
                )
            },
        )

        assert upload_response.status_code == 201

        created_job = upload_response.json()

        assert created_job["status"] == "pending"

        failed_job = wait_for_job_completion(
            client=client,
            job_id=created_job["id"],
        )

        assert failed_job["status"] == "failed"
        assert failed_job["report"] is None
        assert failed_job["error_message"] is not None
        assert "empty" in failed_job["error_message"].lower()

        report_response = client.get(
            f"/jobs/{created_job['id']}/report"
        )

        assert report_response.status_code == 409

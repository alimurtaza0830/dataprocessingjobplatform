import os
import uuid
from pathlib import Path

from fastapi import UploadFile


UPLOAD_DIRECTORY = Path(
    os.getenv("UPLOAD_DIRECTORY", "/data/uploads")
)


def ensure_upload_directory_exists() -> None:
    """
    Create the upload directory if it does not exist.
    """
    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def validate_csv_filename(filename: str | None) -> str:
    """
    Validate and sanitize the uploaded filename.
    """
    if not filename:
        raise ValueError("Uploaded file must have a filename")

    safe_filename = Path(filename).name

    if not safe_filename.lower().endswith(".csv"):
        raise ValueError("Only CSV files are supported")

    return safe_filename


def save_uploaded_file(
    uploaded_file: UploadFile,
) -> tuple[str, str, int]:
    """
    Save an uploaded CSV file to persistent storage.

    Returns:
        original_filename
        stored_filename
        file_size_bytes
    """
    original_filename = validate_csv_filename(
        uploaded_file.filename
    )

    ensure_upload_directory_exists()

    stored_filename = (
        f"{uuid.uuid4()}_{original_filename}"
    )

    destination = UPLOAD_DIRECTORY / stored_filename
    file_size_bytes = 0

    uploaded_file.file.seek(0)

    with destination.open("wb") as output_file:
        while chunk := uploaded_file.file.read(1024 * 1024):
            output_file.write(chunk)
            file_size_bytes += len(chunk)

    return (
        original_filename,
        stored_filename,
        file_size_bytes,
    )

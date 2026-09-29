import os
import uuid
from csv import Error as CsvError
from csv import reader as csv_reader
from io import StringIO
from pathlib import Path

from fastapi import UploadFile


UPLOAD_DIRECTORY = Path(
    os.getenv("UPLOAD_DIRECTORY", "/data/uploads")
)

MAX_UPLOAD_BYTES = int(
    os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024))
)

UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
CSV_SAMPLE_SIZE_BYTES = 64 * 1024

ALLOWED_CSV_CONTENT_TYPES = {
    "application/csv",
    "application/vnd.ms-excel",
    "text/csv",
}


class UploadTooLargeError(ValueError):
    """
    Raised when an uploaded file exceeds the configured size limit.
    """


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


def validate_csv_content_type(content_type: str | None) -> None:
    """
    Validate the uploaded file media type when the client provides one.
    """
    if not content_type:
        return

    media_type = content_type.split(";", maxsplit=1)[0].strip().lower()

    if media_type not in ALLOWED_CSV_CONTENT_TYPES:
        raise ValueError("Uploaded file must be sent as text/csv")


def validate_csv_sample(sample: bytes) -> None:
    """
    Validate that the uploaded bytes look like readable UTF-8 CSV data.
    """
    if not sample.strip():
        raise ValueError(
            "The uploaded CSV is empty or has no readable columns"
        )

    try:
        decoded_sample = sample.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Uploaded CSV must be UTF-8 encoded"
        ) from error

    try:
        rows = csv_reader(StringIO(decoded_sample))
        header = next(rows)
    except (CsvError, StopIteration) as error:
        raise ValueError(
            "The uploaded file is not a valid CSV"
        ) from error

    if not any(column.strip() for column in header):
        raise ValueError(
            "The uploaded CSV is empty or has no readable columns"
        )


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
    validate_csv_content_type(uploaded_file.content_type)

    ensure_upload_directory_exists()

    stored_filename = (
        f"{uuid.uuid4()}_{original_filename}"
    )

    destination = UPLOAD_DIRECTORY / stored_filename
    temporary_destination = destination.with_suffix(
        f"{destination.suffix}.part"
    )
    file_size_bytes = 0
    sample = bytearray()

    uploaded_file.file.seek(0)

    try:
        with temporary_destination.open("wb") as output_file:
            while chunk := uploaded_file.file.read(
                UPLOAD_CHUNK_SIZE_BYTES
            ):
                file_size_bytes += len(chunk)

                if file_size_bytes > MAX_UPLOAD_BYTES:
                    raise UploadTooLargeError(
                        "Uploaded file exceeds the maximum size "
                        f"of {MAX_UPLOAD_BYTES} bytes"
                    )

                if len(sample) < CSV_SAMPLE_SIZE_BYTES:
                    remaining_sample_bytes = (
                        CSV_SAMPLE_SIZE_BYTES - len(sample)
                    )
                    sample.extend(chunk[:remaining_sample_bytes])

                output_file.write(chunk)

        validate_csv_sample(bytes(sample))
        temporary_destination.replace(destination)

    except Exception:
        temporary_destination.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise

    return (
        original_filename,
        stored_filename,
        file_size_bytes,
    )

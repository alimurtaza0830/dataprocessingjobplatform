from io import BytesIO
from pathlib import Path

import pytest

from app import storage
from app.storage import UploadTooLargeError, save_uploaded_file


class SimpleUploadFile:
    def __init__(
        self,
        filename: str,
        content: bytes,
        content_type: str = "text/csv",
    ) -> None:
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(content)


def test_save_uploaded_file_writes_valid_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "UPLOAD_DIRECTORY", tmp_path)

    original_filename, stored_filename, file_size_bytes = (
        save_uploaded_file(
            SimpleUploadFile(
                filename="customers.csv",
                content=b"id,name\n1,Adam\n",
            )
        )
    )

    assert original_filename == "customers.csv"
    assert stored_filename.endswith("_customers.csv")
    assert file_size_bytes == 15
    assert (tmp_path / stored_filename).read_bytes() == (
        b"id,name\n1,Adam\n"
    )


def test_save_uploaded_file_rejects_non_csv_content_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "UPLOAD_DIRECTORY", tmp_path)

    with pytest.raises(
        ValueError,
        match="must be sent as text/csv",
    ):
        save_uploaded_file(
            SimpleUploadFile(
                filename="customers.csv",
                content=b"id,name\n1,Adam\n",
                content_type="text/plain",
            )
        )

    assert list(tmp_path.iterdir()) == []


def test_save_uploaded_file_rejects_oversized_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "UPLOAD_DIRECTORY", tmp_path)
    monkeypatch.setattr(storage, "MAX_UPLOAD_BYTES", 10)

    with pytest.raises(
        UploadTooLargeError,
        match="exceeds the maximum size",
    ):
        save_uploaded_file(
            SimpleUploadFile(
                filename="customers.csv",
                content=b"id,name\n1,Adam\n",
            )
        )

    assert list(tmp_path.iterdir()) == []


def test_save_uploaded_file_rejects_non_utf8_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage, "UPLOAD_DIRECTORY", tmp_path)

    with pytest.raises(
        ValueError,
        match="UTF-8 encoded",
    ):
        save_uploaded_file(
            SimpleUploadFile(
                filename="customers.csv",
                content=b"id,name\n1,\xff\n",
            )
        )

    assert list(tmp_path.iterdir()) == []

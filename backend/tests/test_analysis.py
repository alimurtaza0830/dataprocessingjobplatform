from pathlib import Path

import pytest

from app.analysis import analyze_csv


def test_analyze_csv_generates_expected_report(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "customers.csv"

    csv_file.write_text(
        "id,name,email,age\n"
        "1,Adam,adam@example.com,35\n"
        "2,Sarah,sarah@example.com,29\n"
        "3,John,,42\n"
        "2,Sarah,sarah@example.com,29\n",
        encoding="utf-8",
    )

    report = analyze_csv(csv_file)

    assert report["row_count"] == 4
    assert report["column_count"] == 4

    assert report["columns"] == [
        "id",
        "name",
        "email",
        "age",
    ]

    assert report["total_missing_values"] == 1
    assert report["missing_values"]["email"] == 1
    assert report["duplicate_rows"] == 1

    assert report["numeric_summary"]["age"] == {
        "minimum": 29.0,
        "maximum": 42.0,
        "mean": 33.75,
        "median": 32.0,
    }


def test_analyze_csv_rejects_empty_file(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="empty or has no readable columns",
    ):
        analyze_csv(csv_file)


def test_analyze_csv_rejects_missing_file(
    tmp_path: Path,
) -> None:
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(
        FileNotFoundError,
        match="CSV file does not exist",
    ):
        analyze_csv(missing_file)

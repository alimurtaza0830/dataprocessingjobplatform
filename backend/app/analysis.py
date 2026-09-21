import os
from pathlib import Path
from typing import Any

import pandas as pd


MAX_CSV_ROWS = int(
    os.getenv("MAX_CSV_ROWS", "100000")
)
MAX_CSV_COLUMNS = int(
    os.getenv("MAX_CSV_COLUMNS", "1000")
)


def analyze_csv(file_path: str | Path) -> dict[str, Any]:
    """
    Analyze a CSV file and return a JSON-compatible data-quality report.
    """
    csv_path = Path(file_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file does not exist: {csv_path}"
        )

    try:
        dataframe = pd.read_csv(
            csv_path,
            encoding="utf-8-sig",
            nrows=MAX_CSV_ROWS + 1,
            on_bad_lines="error",
        )
    except pd.errors.EmptyDataError as error:
        raise ValueError(
            "The uploaded CSV is empty or has no readable columns"
        ) from error
    except pd.errors.ParserError as error:
        raise ValueError(
            "The uploaded file is not a valid CSV"
        ) from error
    except UnicodeDecodeError as error:
        raise ValueError(
            "Uploaded CSV must be UTF-8 encoded"
        ) from error

    if len(dataframe) > MAX_CSV_ROWS:
        raise ValueError(
            "Uploaded CSV exceeds the maximum row count "
            f"of {MAX_CSV_ROWS}"
        )

    if len(dataframe.columns) > MAX_CSV_COLUMNS:
        raise ValueError(
            "Uploaded CSV exceeds the maximum column count "
            f"of {MAX_CSV_COLUMNS}"
        )

    missing_values = {
        str(column): int(count)
        for column, count in dataframe.isna().sum().items()
    }

    data_types = {
        str(column): str(data_type)
        for column, data_type in dataframe.dtypes.items()
    }

    numeric_summary: dict[str, dict[str, float | None]] = {}

    numeric_dataframe = dataframe.select_dtypes(
        include="number"
    )

    for column in numeric_dataframe.columns:
        values = numeric_dataframe[column].dropna()

        if values.empty:
            numeric_summary[str(column)] = {
                "minimum": None,
                "maximum": None,
                "mean": None,
                "median": None,
            }
            continue

        numeric_summary[str(column)] = {
            "minimum": float(values.min()),
            "maximum": float(values.max()),
            "mean": float(values.mean()),
            "median": float(values.median()),
        }

    return {
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": [
            str(column)
            for column in dataframe.columns
        ],
        "data_types": data_types,
        "missing_values": missing_values,
        "total_missing_values": int(
            dataframe.isna().sum().sum()
        ),
        "duplicate_rows": int(
            dataframe.duplicated().sum()
        ),
        "numeric_summary": numeric_summary,
    }

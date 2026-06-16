"""
Utility helpers for CSV I/O, column detection, chunking, and formatting.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import (
    CHUNK_SIZE,
    COUNTRY_COLUMN_KEYWORDS,
    DATE_COLUMN_KEYWORDS,
    EMAIL_COLUMN_KEYWORDS,
    NUMERIC_COLUMN_KEYWORDS,
    ORDER_ID_COLUMN_KEYWORDS,
    PAYMENT_COLUMN_KEYWORDS,
    PHONE_COLUMN_KEYWORDS,
)


def build_payment_lookup(modes: List[str]) -> Dict[str, str]:
    """Build a case-insensitive payment mode lookup from a mode list."""
    lookup: Dict[str, str] = {}
    for mode in modes:
        cleaned = mode.strip()
        if cleaned:
            lookup[cleaned.lower()] = cleaned
    return lookup


def read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """
    Read an uploaded CSV file into a DataFrame with basic error handling.

    Args:
        uploaded_file: Streamlit UploadedFile object or file-like buffer.

    Returns:
        Parsed DataFrame.

    Raises:
        ValueError: If the file cannot be parsed as CSV.
    """
    try:
        df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError(f"Unable to read CSV file: {exc}") from exc

    if df.empty and len(df.columns) == 0:
        raise ValueError("The uploaded CSV appears to be empty.")

    # Normalize column names: strip whitespace
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _match_column(columns: List[str], keywords: List[str]) -> Optional[str]:
    """Return the first column whose normalized name contains a keyword."""
    for col in columns:
        normalized = col.lower().replace(" ", "_").replace("-", "_")
        if any(keyword in normalized for keyword in keywords):
            return col
    return None


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Auto-detect relevant columns in the uploaded dataset.

    Returns:
        Dictionary mapping logical field names to actual column names.
    """
    columns = list(df.columns)
    return {
        "phone": _match_column(columns, PHONE_COLUMN_KEYWORDS),
        "date": _match_column(columns, DATE_COLUMN_KEYWORDS),
        "payment": _match_column(columns, PAYMENT_COLUMN_KEYWORDS),
        "email": _match_column(columns, EMAIL_COLUMN_KEYWORDS),
        "order_id": _match_column(columns, ORDER_ID_COLUMN_KEYWORDS),
        "country": _match_column(columns, COUNTRY_COLUMN_KEYWORDS),
        "numeric": _match_numeric_columns(columns),
    }


def _match_numeric_columns(columns: List[str]) -> List[str]:
    """Find columns that likely contain numeric transaction values."""
    matched: List[str] = []
    for col in columns:
        normalized = col.lower().replace(" ", "_").replace("-", "_")
        if any(keyword in normalized for keyword in NUMERIC_COLUMN_KEYWORDS):
            matched.append(col)
    return matched


def strip_phone(value: object) -> str:
    """Remove non-digit characters from a phone value."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    # Remove common prefixes like +91, 91-, etc. but keep digits
    digits = re.sub(r"\D", "", text)
    return digits


def is_blank(value: object) -> bool:
    """Check whether a cell value is empty or whitespace-only."""
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return str(value).strip() == ""


def is_valid_email(value: object) -> bool:
    """Basic RFC-inspired email format check."""
    if is_blank(value):
        return False
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(value).strip()))


def is_valid_numeric(value: object) -> bool:
    """Return True if value can be interpreted as a finite number."""
    if is_blank(value):
        return False
    text = str(value).strip().replace(",", "")
    try:
        float(text)
        return True
    except ValueError:
        return False


def is_empty_record(row: pd.Series) -> bool:
    """Return True if every field in the row is blank."""
    return all(is_blank(row[col]) for col in row.index)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes for Streamlit download buttons."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def chunk_dataframe(df: pd.DataFrame, chunk_size: int = CHUNK_SIZE) -> List[pd.DataFrame]:
    """
    Split a DataFrame into fixed-size chunks.

    Args:
        df: Source DataFrame.
        chunk_size: Maximum rows per chunk.

    Returns:
        List of DataFrame chunks (may be a single-element list).
    """
    if len(df) <= chunk_size:
        return [df.copy()]

    chunks: List[pd.DataFrame] = []
    for start in range(0, len(df), chunk_size):
        chunks.append(df.iloc[start : start + chunk_size].copy())
    return chunks


def build_summary_dataframe(
    report: Dict[str, object],
    insights: Optional[Dict[str, object]] = None,
    executive_summary: Optional[str] = None,
) -> pd.DataFrame:
    """Build a tabular validation summary for CSV export."""
    rows = [
        {"metric": "Total Records", "value": report["total_records"]},
        {"metric": "Valid Records", "value": report["valid_records"]},
        {"metric": "Invalid Records", "value": report["invalid_records"]},
        {"metric": "Validation Rate (%)", "value": report["validation_rate"]},
    ]

    if insights:
        rows.extend(
            [
                {"metric": "Data Quality Score", "value": f"{insights['quality_score']}/100"},
                {"metric": "Quality Tier", "value": insights.get("quality_label", "")},
                {"metric": "Missing Data (%)", "value": insights.get("missing_data_pct", 0)},
                {"metric": "Duplicate Records", "value": insights.get("duplicate_count", 0)},
                {
                    "metric": "Most Common Payment Mode",
                    "value": insights.get("most_common_payment", ""),
                },
            ]
        )

    if executive_summary:
        clean_summary = executive_summary.replace("**", "")
        rows.append({"metric": "Executive Summary", "value": clean_summary})

    for category, count in report.get("error_breakdown", {}).items():
        rows.append({"metric": f"Error: {category}", "value": count})
    return pd.DataFrame(rows)


def format_file_size(num_bytes: int) -> str:
    """Human-readable file size string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def safe_percentage(numerator: int, denominator: int) -> float:
    """Compute percentage safely, returning 0.0 when denominator is zero."""
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)

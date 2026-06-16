"""
Core validation engine for transaction datasets.

Runs phone, date, payment, and data-quality checks and produces
annotated output with validation_status and validation_errors columns.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from config import SUPPORTED_DATE_FORMATS
from utils import (
    build_payment_lookup,
    detect_columns,
    is_blank,
    is_empty_record,
    is_valid_email,
    is_valid_numeric,
    strip_phone,
)


# Error category constants used in reports and output columns
ERROR_EMPTY_RECORD = "Empty Record"
ERROR_DUPLICATE = "Duplicate Row"
ERROR_INVALID_PHONE = "Invalid Phone"
ERROR_INVALID_DATE = "Invalid Date"
ERROR_MISSING_PAYMENT = "Missing Payment Mode"
ERROR_INVALID_PAYMENT = "Invalid Payment Mode"
ERROR_INVALID_EMAIL = "Invalid Email"
ERROR_INVALID_NUMERIC = "Invalid Numeric Field"
ERROR_MISSING_VALUE = "Missing Value"


def parse_date(value: object) -> Tuple[bool, Optional[str]]:
    """
    Attempt to parse a date string against supported formats.

    Returns:
        Tuple of (is_valid, matched_format_label or None).
    """
    if is_blank(value):
        return False, None

    text = str(value).strip()
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return True, fmt
        except ValueError:
            continue
    return False, None


def validate_phone(value: object, phone_digits: int) -> bool:
    """Validate phone number length against the configured digit count."""
    if is_blank(value):
        return False

    digits = strip_phone(value)
    if not digits:
        return False

    return len(digits) == phone_digits and digits.isdigit()


def validate_payment_mode(
    value: object,
    payment_lookup: Dict[str, str],
) -> Tuple[bool, Optional[str]]:
    """
    Validate payment mode against allowed values.

    Returns:
        (is_valid, canonical_mode_or_None)
    """
    if is_blank(value):
        return False, None

    normalized = str(value).strip().lower()
    canonical = payment_lookup.get(normalized)
    if canonical:
        return True, canonical
    return False, None


def _collect_row_errors(
    row: pd.Series,
    row_index: int,
    columns: Dict[str, Optional[str]],
    phone_digits: int,
    payment_lookup: Dict[str, str],
    duplicate_indices: Set[int],
    numeric_columns: List[str],
) -> List[str]:
    """Run all validation checks for a single row and return error labels."""
    errors: List[str] = []

    if is_empty_record(row):
        errors.append(ERROR_EMPTY_RECORD)
        return errors

    if row_index in duplicate_indices:
        errors.append(ERROR_DUPLICATE)

    # Missing values on non-empty rows (any blank cell in detected key columns)
    key_cols = [
        c
        for c in [
            columns.get("phone"),
            columns.get("date"),
            columns.get("payment"),
            columns.get("email"),
        ]
        if c
    ]
    for col in key_cols:
        if is_blank(row[col]):
            if col == columns.get("payment"):
                if ERROR_MISSING_PAYMENT not in errors:
                    errors.append(ERROR_MISSING_PAYMENT)
            else:
                if ERROR_MISSING_VALUE not in errors:
                    errors.append(ERROR_MISSING_VALUE)

    phone_col = columns.get("phone")
    if phone_col and not is_blank(row[phone_col]):
        if not validate_phone(row[phone_col], phone_digits):
            errors.append(ERROR_INVALID_PHONE)

    date_col = columns.get("date")
    if date_col and not is_blank(row[date_col]):
        is_date_valid, _ = parse_date(row[date_col])
        if not is_date_valid:
            errors.append(ERROR_INVALID_DATE)

    payment_col = columns.get("payment")
    if payment_col:
        if is_blank(row[payment_col]):
            if ERROR_MISSING_PAYMENT not in errors:
                errors.append(ERROR_MISSING_PAYMENT)
        else:
            is_payment_valid, _ = validate_payment_mode(row[payment_col], payment_lookup)
            if not is_payment_valid:
                errors.append(ERROR_INVALID_PAYMENT)

    email_col = columns.get("email")
    if email_col and not is_blank(row[email_col]):
        if not is_valid_email(row[email_col]):
            errors.append(ERROR_INVALID_EMAIL)

    for num_col in numeric_columns:
        if num_col in row.index and not is_blank(row[num_col]):
            if not is_valid_numeric(row[num_col]):
                if ERROR_INVALID_NUMERIC not in errors:
                    errors.append(ERROR_INVALID_NUMERIC)

    return errors


def _find_duplicate_indices(
    df: pd.DataFrame,
    order_id_col: Optional[str] = None,
) -> Set[int]:
    """
    Return indices of duplicate rows.

    Flags both exact row duplicates and repeated order/transaction IDs.
    """
    if df.empty:
        return set()

    duplicate_indices: Set[int] = set()

    # Exact duplicate rows (all columns match)
    row_dup_mask = df.duplicated(keep=False)
    duplicate_indices.update(df.index[row_dup_mask].tolist())

    # Duplicate business keys (e.g. order_id appears more than once)
    if order_id_col and order_id_col in df.columns:
        non_blank_ids = df[order_id_col].apply(lambda v: not is_blank(v))
        keyed = df.loc[non_blank_ids]
        if not keyed.empty:
            id_dup_mask = keyed.duplicated(subset=[order_id_col], keep=False)
            duplicate_indices.update(keyed.index[id_dup_mask].tolist())

    return duplicate_indices


def validate_dataframe(
    df: pd.DataFrame,
    validation_rules: Optional[Dict[str, object]] = None,
    country: Optional[str] = None,
    column_map: Optional[Dict[str, Optional[str]]] = None,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """
    Validate an entire transaction DataFrame.

    Args:
        df: Source transaction data.
        validation_rules: Session validation rules (country, phone digits, payment modes).
        country: Deprecated alias for country name when rules dict is not provided.
        column_map: Optional override for auto-detected columns.

    Returns:
        Tuple of (annotated DataFrame, validation report dict).
    """
    if df.empty:
        raise ValueError("Cannot validate an empty dataset.")

    rules = validation_rules or {}
    country_name = str(rules.get("country_name") or country or "India")
    phone_digits = int(rules.get("phone_digits", 10))
    payment_modes = rules.get("allowed_payment_modes") or []
    payment_lookup = build_payment_lookup(list(payment_modes))

    working = df.copy()
    columns = column_map or detect_columns(working)
    numeric_columns = columns.get("numeric") or []

    duplicate_indices = _find_duplicate_indices(
        working,
        order_id_col=columns.get("order_id"),
    )

    statuses: List[str] = []
    error_lists: List[str] = []
    all_errors: List[List[str]] = []

    for idx, row in working.iterrows():
        row_errors = _collect_row_errors(
            row=row,
            row_index=int(idx),
            columns=columns,
            phone_digits=phone_digits,
            payment_lookup=payment_lookup,
            duplicate_indices=duplicate_indices,
            numeric_columns=numeric_columns,
        )
        all_errors.append(row_errors)
        if row_errors:
            statuses.append("Invalid")
            error_lists.append("; ".join(row_errors))
        else:
            statuses.append("Valid")
            error_lists.append("")

    working["validation_status"] = statuses
    working["validation_errors"] = error_lists

    report = _build_report(
        all_errors,
        statuses,
        columns,
        country_name,
        list(payment_modes),
    )
    return working, report


def _build_report(
    all_errors: List[List[str]],
    statuses: List[str],
    columns: Dict[str, Optional[str]],
    country: str,
    allowed_payment_modes: List[str],
) -> Dict[str, object]:
    """Aggregate row-level results into a dashboard-friendly report."""
    total = len(statuses)
    valid = statuses.count("Valid")
    invalid = total - valid

    breakdown: Dict[str, int] = {}
    for row_errors in all_errors:
        for error in row_errors:
            breakdown[error] = breakdown.get(error, 0) + 1

    validation_rate = round((valid / total) * 100, 2) if total else 0.0

    return {
        "total_records": total,
        "valid_records": valid,
        "invalid_records": invalid,
        "validation_rate": validation_rate,
        "error_breakdown": dict(sorted(breakdown.items(), key=lambda x: -x[1])),
        "detected_columns": columns,
        "country": country,
        "allowed_payment_modes": allowed_payment_modes,
    }


def get_invalid_records(df: pd.DataFrame) -> pd.DataFrame:
    """Filter rows marked as Invalid."""
    if "validation_status" not in df.columns:
        return pd.DataFrame()
    return df[df["validation_status"] == "Invalid"].copy()


def get_valid_records(df: pd.DataFrame) -> pd.DataFrame:
    """Filter rows marked as Valid."""
    if "validation_status" not in df.columns:
        return df.copy()
    return df[df["validation_status"] == "Valid"].copy()

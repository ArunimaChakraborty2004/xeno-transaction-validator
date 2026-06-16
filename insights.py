"""
Automated data insights, quality scoring, and executive summaries.

Rule-based analytics layer that transforms validation output into
client-ready intelligence — no external AI API required.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from utils import build_payment_lookup, is_blank, safe_percentage
from validator import ERROR_DUPLICATE


def _normalize_payment_mode(value: object, payment_lookup: Dict[str, str]) -> str:
    """Map raw payment values to canonical labels for analytics."""
    if is_blank(value):
        return "Unknown / Missing"
    text = str(value).strip()
    canonical = payment_lookup.get(text.lower())
    return canonical if canonical else text.title()


def _resolve_payment_lookup(
    validation_rules: Optional[RulesDict],
    report: Dict[str, object],
) -> Dict[str, str]:
    """Build payment lookup from rules or report metadata."""
    if validation_rules:
        modes = validation_rules.get("allowed_payment_modes") or []
        return build_payment_lookup(list(modes))
    modes = report.get("allowed_payment_modes") or []
    return build_payment_lookup(list(modes))


def compute_missing_data_percentage(df: pd.DataFrame) -> float:
    """
    Calculate the percentage of blank cells across the entire dataset.

    Returns:
        Missing data percentage rounded to two decimal places.
    """
    if df.empty:
        return 0.0

    total_cells = df.shape[0] * df.shape[1]
    if total_cells == 0:
        return 0.0

    missing_cells = sum(is_blank(df.iloc[r, c]) for r in range(df.shape[0]) for c in range(df.shape[1]))
    return safe_percentage(missing_cells, total_cells)


def get_payment_mode_distribution(
    df: pd.DataFrame,
    payment_col: Optional[str],
    payment_lookup: Dict[str, str],
) -> pd.Series:
    """Return normalized payment mode counts for charting."""
    if not payment_col or payment_col not in df.columns:
        return pd.Series(dtype=int)

    normalized = df[payment_col].apply(lambda v: _normalize_payment_mode(v, payment_lookup))
    return normalized.value_counts().sort_values(ascending=False)


def get_country_distribution(
    df: pd.DataFrame,
    country_col: Optional[str],
    fallback_country: str,
) -> Tuple[pd.Series, str]:
    """
    Return country value counts and a source label.

    Falls back to the validation country setting when no country column exists.
    """
    if country_col and country_col in df.columns:
        values = df[country_col].apply(
            lambda v: str(v).strip().title() if not is_blank(v) else "Unknown"
        )
        return values.value_counts().sort_values(ascending=False), "dataset"

    # Single-country fallback based on validation configuration
    return pd.Series({fallback_country: len(df)}), "validation_setting"


def get_validation_status_breakdown(validated_df: pd.DataFrame) -> pd.Series:
    """Return Valid vs Invalid record counts."""
    if "validation_status" not in validated_df.columns or validated_df.empty:
        return pd.Series(dtype=int)
    return validated_df["validation_status"].value_counts()


def get_duplicate_record_count(report: Dict[str, object]) -> int:
    """Extract duplicate row count from the validation error breakdown."""
    breakdown = report.get("error_breakdown", {})
    return int(breakdown.get(ERROR_DUPLICATE, 0))


def get_top_validation_failures(
    report: Dict[str, object],
    limit: int = 5,
) -> List[Tuple[str, int]]:
    """Return the most frequent validation failure categories."""
    breakdown = report.get("error_breakdown", {})
    sorted_items = sorted(breakdown.items(), key=lambda item: -item[1])
    return sorted_items[:limit]


def compute_data_quality_score(
    report: Dict[str, object],
    missing_data_pct: float,
    duplicate_count: int,
) -> float:
    """
    Compute a composite data quality score out of 100.

    Weighting:
        - 60% validation pass rate
        - 25% data completeness (inverse of missing cell rate)
        - 15% record uniqueness (inverse of duplicate rate)
    """
    total = int(report.get("total_records", 0))
    valid = int(report.get("valid_records", 0))

    if total == 0:
        return 0.0

    validation_component = (valid / total) * 100
    completeness_component = max(0.0, 100.0 - missing_data_pct)
    duplicate_pct = (duplicate_count / total) * 100
    uniqueness_component = max(0.0, 100.0 - duplicate_pct)

    score = (
        validation_component * 0.60
        + completeness_component * 0.25
        + uniqueness_component * 0.15
    )
    return round(min(100.0, max(0.0, score)), 1)


def _score_label(score: float) -> str:
    """Map numeric score to a human-readable quality tier."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Fair"
    return "Needs Improvement"


def generate_insights(
    validated_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    report: Dict[str, object],
    validation_rules: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """
    Build a structured insights payload from validated transaction data.

    Returns:
        Dictionary consumed by the Streamlit dashboard and summary export.
    """
    columns = report.get("detected_columns", {})
    payment_col = columns.get("payment")
    country_col = columns.get("country")
    fallback_country = str(report.get("country", "Unknown"))
    payment_lookup = _resolve_payment_lookup(validation_rules, report)

    missing_pct = compute_missing_data_percentage(raw_df)
    duplicate_count = get_duplicate_record_count(report)
    payment_distribution = get_payment_mode_distribution(
        validated_df, payment_col, payment_lookup
    )
    country_distribution, country_source = get_country_distribution(
        validated_df, country_col, fallback_country
    )
    status_breakdown = get_validation_status_breakdown(validated_df)
    top_failures = get_top_validation_failures(report)
    quality_score = compute_data_quality_score(report, missing_pct, duplicate_count)

    most_common_payment = (
        payment_distribution.index[0] if not payment_distribution.empty else "Not available"
    )
    most_common_payment_pct = (
        safe_percentage(int(payment_distribution.iloc[0]), len(validated_df))
        if not payment_distribution.empty
        else 0.0
    )

    insight_cards = [
        {
            "title": "Most Common Payment Mode",
            "value": str(most_common_payment),
            "detail": f"{most_common_payment_pct}% of transactions",
            "icon": "💳",
        },
        {
            "title": "Duplicate Records",
            "value": f"{duplicate_count:,}",
            "detail": "Rows flagged as duplicates",
            "icon": "🔁",
        },
        {
            "title": "Missing Data",
            "value": f"{missing_pct}%",
            "detail": "Blank cells across dataset",
            "icon": "📉",
        },
        {
            "title": "Top Validation Issue",
            "value": top_failures[0][0] if top_failures else "None",
            "detail": (
                f"{top_failures[0][1]:,} occurrences"
                if top_failures
                else "All checks passed"
            ),
            "icon": "⚠️",
        },
    ]

    return {
        "quality_score": quality_score,
        "quality_label": _score_label(quality_score),
        "missing_data_pct": missing_pct,
        "duplicate_count": duplicate_count,
        "most_common_payment": most_common_payment,
        "most_common_payment_pct": most_common_payment_pct,
        "payment_distribution": payment_distribution,
        "country_distribution": country_distribution,
        "country_source": country_source,
        "status_breakdown": status_breakdown,
        "top_failures": top_failures,
        "insight_cards": insight_cards,
    }


def _humanize_failure(failure: str) -> str:
    """Convert internal error labels to executive-friendly phrasing."""
    mapping = {
        "Invalid Phone": "invalid phone numbers",
        "Invalid Date": "invalid date formats",
        "Invalid Payment Mode": "unsupported payment modes",
        "Missing Payment Mode": "missing payment modes",
        "Invalid Email": "invalid email addresses",
        "Invalid Numeric Field": "invalid numeric values",
        "Missing Value": "missing required fields",
        "Duplicate Row": "duplicate records",
        "Empty Record": "empty records",
    }
    return mapping.get(failure, failure.lower())


def generate_executive_summary(report: Dict[str, object], insights: Dict[str, object]) -> str:
    """
    Generate a concise, human-readable executive summary paragraph.

    Example:
        "This dataset contains 523 records. 487 records passed validation.
         The most common issue is invalid phone numbers. UPI is the dominant payment method."
    """
    total = int(report.get("total_records", 0))
    valid = int(report.get("valid_records", 0))
    score = insights.get("quality_score", 0)
    payment = insights.get("most_common_payment", "Not available")
    missing_pct = insights.get("missing_data_pct", 0)
    duplicate_count = insights.get("duplicate_count", 0)
    top_failures = insights.get("top_failures", [])

    sentences: List[str] = [
        f"This dataset contains **{total:,}** records, of which **{valid:,}** passed validation "
        f"(Data Quality Score: **{score}/100** — {insights.get('quality_label', '')})."
    ]

    if top_failures:
        top_issue = _humanize_failure(top_failures[0][0])
        sentences.append(f"The most common issue is **{top_issue}** ({top_failures[0][1]:,} occurrences).")
    else:
        sentences.append("No validation issues were detected — the dataset is fully compliant.")

    if payment != "Not available":
        sentences.append(f"**{payment}** is the dominant payment method across transactions.")

    if missing_pct > 0:
        sentences.append(f"Missing data accounts for **{missing_pct}%** of all cells in the file.")

    if duplicate_count > 0:
        sentences.append(f"**{duplicate_count:,}** duplicate record(s) were identified and flagged.")

    country_source = insights.get("country_source")
    country_dist: pd.Series = insights.get("country_distribution", pd.Series(dtype=int))
    if country_source == "dataset" and not country_dist.empty and len(country_dist) > 1:
        top_country = country_dist.index[0]
        sentences.append(
            f"Geographic distribution is led by **{top_country}** "
            f"({safe_percentage(int(country_dist.iloc[0]), total)}% of records)."
        )

    return " ".join(sentences)

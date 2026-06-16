"""
Xeno Transaction Validator — Streamlit application entry point.

Upload transaction CSVs, run validation, review analytics and insights,
and download cleaned or invalid record exports. Deployable on Streamlit Cloud.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from config import (
    APP_BRAND,
    APP_TAGLINE,
    APP_TITLE,
    CHUNK_SIZE,
    MAX_PREVIEW_ROWS,
)
from insights import generate_executive_summary, generate_insights
from pdf_report import generate_validation_pdf
from rules import render_rules_editor
from utils import (
    build_summary_dataframe,
    chunk_dataframe,
    dataframe_to_csv_bytes,
    detect_columns,
    read_uploaded_csv,
)
from validator import get_invalid_records, validate_dataframe


# ---------------------------------------------------------------------------
# Page configuration & global styles
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)

CHART_COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"]

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }

    .brand-bar {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #2563eb 100%);
        border-radius: 16px;
        padding: 1.75rem 2rem;
        margin-bottom: 1.5rem;
        color: #ffffff;
        box-shadow: 0 10px 40px rgba(37, 99, 235, 0.18);
    }
    .brand-kicker {
        font-size: 0.75rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        opacity: 0.85;
        margin-bottom: 0.35rem;
    }
    .brand-title {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .brand-tagline {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }

    .score-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
    }
    .score-value {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1;
        margin: 0.5rem 0;
    }
    .score-label {
        font-size: 0.95rem;
        color: #64748b;
        font-weight: 500;
    }
    .score-excellent { color: #059669; }
    .score-good { color: #2563eb; }
    .score-fair { color: #d97706; }
    .score-poor { color: #dc2626; }

    .exec-summary {
        background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        color: #1e293b;
        line-height: 1.7;
        font-size: 1rem;
    }

    .insight-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        height: 100%;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }
    .insight-icon {
        font-size: 1.4rem;
        margin-bottom: 0.35rem;
    }
    .insight-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .insight-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.15rem;
    }
    .insight-detail {
        font-size: 0.85rem;
        color: #64748b;
    }

    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0 0 0.25rem 0;
    }
    .section-sub {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    .success-banner {
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-left: 4px solid #10b981;
        padding: 0.85rem 1.1rem;
        border-radius: 0 10px 10px 0;
        margin: 0.75rem 0 1rem 0;
        color: #065f46;
    }
    .error-banner {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-left: 4px solid #ef4444;
        padding: 0.85rem 1.1rem;
        border-radius: 0 10px 10px 0;
        margin: 0.75rem 0 1rem 0;
        color: #991b1b;
    }

    .chart-panel {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 0.5rem 0.75rem 0 0.75rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }

    .stDownloadButton button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state() -> None:
    """Initialize Streamlit session state keys."""
    defaults = {
        "raw_df": None,
        "validated_df": None,
        "report": None,
        "insights": None,
        "executive_summary": None,
        "filename": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def score_css_class(score: float) -> str:
    """Return CSS class for score color coding."""
    if score >= 90:
        return "score-excellent"
    if score >= 75:
        return "score-good"
    if score >= 60:
        return "score-fair"
    return "score-poor"


def render_header() -> None:
    """Render branded application header."""
    st.markdown(
        f"""
        <div class="brand-bar">
            <div class="brand-kicker">{APP_BRAND} Platform</div>
            <div class="brand-title">{APP_TITLE}</div>
            <div class="brand-tagline">{APP_TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_section(rules: dict) -> None:
    """Handle CSV upload and trigger validation."""
    st.markdown('<p class="section-header">Upload Transaction Data</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Import order-level, product-level, or payment CSV files for automated validation.</p>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Supports standard transaction exports with auto-detected columns.",
    )

    if uploaded is not None:
        try:
            df = read_uploaded_csv(uploaded)
            st.session_state["raw_df"] = df
            st.session_state["filename"] = uploaded.name

            column_map = detect_columns(df)
            validated_df, report = validate_dataframe(df, validation_rules=rules, column_map=column_map)
            insights = generate_insights(validated_df, df, report)
            summary = generate_executive_summary(report, insights)

            st.session_state["validated_df"] = validated_df
            st.session_state["report"] = report
            st.session_state["insights"] = insights
            st.session_state["executive_summary"] = summary

            if report["invalid_records"] == 0:
                st.markdown(
                    '<div class="success-banner">✅ Validation complete — all records passed quality checks.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="error-banner">⚠️ Validation complete — '
                    f'{report["invalid_records"]:,} of {report["total_records"]:,} '
                    f"record(s) require remediation.</div>",
                    unsafe_allow_html=True,
                )

        except ValueError as exc:
            st.error(str(exc))
            st.session_state["validated_df"] = None
            st.session_state["report"] = None
            st.session_state["insights"] = None
            st.session_state["executive_summary"] = None


def render_executive_summary(insights: dict, summary: str) -> None:
    """Render data quality score and executive summary narrative."""
    st.markdown('<p class="section-header">Executive Summary</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">AI-generated overview for stakeholders and client reporting.</p>',
        unsafe_allow_html=True,
    )

    score = insights["quality_score"]
    score_class = score_css_class(score)

    col_score, col_summary = st.columns([1, 3])
    with col_score:
        st.markdown(
            f"""
            <div class="score-card">
                <div class="score-label">Data Quality Score</div>
                <div class="score-value {score_class}">{score}<span style="font-size:1.5rem;color:#94a3b8;">/100</span></div>
                <div class="score-label">{insights['quality_label']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_summary:
        st.markdown("**Key findings**")
        st.markdown(summary)


def render_insights(insights: dict) -> None:
    """Render AI data insights cards."""
    st.markdown('<p class="section-header">AI Data Insights</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Automatically generated patterns and quality signals from your dataset.</p>',
        unsafe_allow_html=True,
    )

    cards = insights.get("insight_cards", [])
    cols = st.columns(len(cards) if cards else 4)

    for col_widget, card in zip(cols, cards):
        with col_widget:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-icon">{card['icon']}</div>
                    <div class="insight-title">{card['title']}</div>
                    <div class="insight-value">{card['value']}</div>
                    <div class="insight-detail">{card['detail']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    top_failures = insights.get("top_failures", [])
    if top_failures:
        st.markdown("**Top validation failures**")
        failure_df = pd.DataFrame(
            [{"Failure Category": cat, "Occurrences": count} for cat, count in top_failures]
        )
        st.dataframe(failure_df, width='stretch', hide_index=True)


def _series_to_chart_df(series: pd.Series, label_col: str, value_col: str = "Count") -> pd.DataFrame:
    """Convert a value-counts Series to a chart-friendly DataFrame."""
    if series.empty:
        return pd.DataFrame(columns=[label_col, value_col])
    df = series.reset_index()
    df.columns = [label_col, value_col]
    return df


def _donut_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str) -> alt.Chart:
    """Build a styled Altair donut chart."""
    base = alt.Chart(df).encode(
        theta=alt.Theta(f"{value_col}:Q", stack=True),
        color=alt.Color(
            f"{label_col}:N",
            scale=alt.Scale(range=CHART_COLORS),
            legend=alt.Legend(title=None, orient="bottom"),
        ),
        tooltip=[label_col, value_col],
    )
    return base.mark_arc(innerRadius=55, outerRadius=95).properties(
        title=title,
        height=280,
    )


def _bar_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str) -> alt.Chart:
    """Build a styled Altair horizontal bar chart."""
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{value_col}:Q", title="Records"),
            y=alt.Y(f"{label_col}:N", sort="-x", title=None),
            color=alt.Color(f"{label_col}:N", scale=alt.Scale(range=CHART_COLORS), legend=None),
            tooltip=[label_col, value_col],
        )
        .properties(title=title, height=max(220, len(df) * 36))
    )


def render_visual_analytics(insights: dict) -> None:
    """Render visual analytics charts."""
    st.markdown('<p class="section-header">Visual Analytics</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Interactive distribution charts for payment, geography, and validation outcomes.</p>',
        unsafe_allow_html=True,
    )

    chart1, chart2, chart3 = st.columns(3)

    payment_series: pd.Series = insights.get("payment_distribution", pd.Series(dtype=int))
    country_series: pd.Series = insights.get("country_distribution", pd.Series(dtype=int))
    status_series: pd.Series = insights.get("status_breakdown", pd.Series(dtype=int))
    country_source = insights.get("country_source", "dataset")

    with chart1:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        if not payment_series.empty:
            payment_df = _series_to_chart_df(payment_series, "Payment Mode")
            st.altair_chart(_bar_chart(payment_df, "Payment Mode", "Count", "Payment Mode Distribution"), width='stretch')
        else:
            st.info("No payment column detected.")
        st.markdown("</div>", unsafe_allow_html=True)

    with chart2:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        if not country_series.empty:
            country_df = _series_to_chart_df(country_series, "Country")
            title = "Country Distribution" if country_source == "dataset" else "Validation Region"
            st.altair_chart(_donut_chart(country_df, "Country", "Count", title), width='stretch')
            if country_source == "validation_setting":
                st.caption("Based on phone validation country setting (no country column found).")
        else:
            st.info("Country data unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)

    with chart3:
        st.markdown('<div class="chart-panel">', unsafe_allow_html=True)
        if not status_series.empty:
            status_df = _series_to_chart_df(status_series, "Status")
            st.altair_chart(_donut_chart(status_df, "Status", "Count", "Validation Status"), width='stretch')
        else:
            st.info("Validation status unavailable.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_metrics(report: dict) -> None:
    """Display validation dashboard metrics."""
    st.markdown('<p class="section-header">Validation Report</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Record-level validation outcomes and error category breakdown.</p>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", f"{report['total_records']:,}")
    col2.metric("Valid Records", f"{report['valid_records']:,}")
    col3.metric("Invalid Records", f"{report['invalid_records']:,}")
    col4.metric("Pass Rate", f"{report['validation_rate']}%")

    if report.get("error_breakdown"):
        breakdown_df = pd.DataFrame(
            [{"Category": cat, "Count": count} for cat, count in report["error_breakdown"].items()]
        )
        st.bar_chart(breakdown_df.set_index("Category"), height=260, color="#2563eb")
    else:
        st.success("No validation errors detected.")


def render_column_detection(report: dict) -> None:
    """Show which columns were auto-detected."""
    detected = report.get("detected_columns", {})
    st.markdown("**Detected schema mapping**")
    cols = st.columns(5)
    labels = [
        ("Phone", detected.get("phone") or "—"),
        ("Date", detected.get("date") or "—"),
        ("Payment", detected.get("payment") or "—"),
        ("Email", detected.get("email") or "—"),
        ("Country", detected.get("country") or "—"),
    ]
    for col_widget, (label, value) in zip(cols, labels):
        col_widget.markdown(f"**{label}:** `{value}`")

    numeric_cols = detected.get("numeric") or []
    if numeric_cols:
        st.caption(f"Numeric fields: {', '.join(f'`{c}`' for c in numeric_cols)}")


def render_preview(df: pd.DataFrame) -> None:
    """Display dataset preview with row/column counts."""
    st.markdown('<p class="section-header">Data Preview</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Validated dataset with status annotations appended.</p>',
        unsafe_allow_html=True,
    )

    row_count, col_count = df.shape
    p1, p2 = st.columns(2)
    p1.metric("Rows", f"{row_count:,}")
    p2.metric("Columns", col_count)

    display_df = df.head(MAX_PREVIEW_ROWS)
    st.dataframe(display_df, width='stretch', hide_index=True)

    if row_count > MAX_PREVIEW_ROWS:
        st.caption(f"Showing first {MAX_PREVIEW_ROWS} of {row_count:,} rows.")


def render_download_section(
    validated_df: pd.DataFrame,
    report: dict,
    insights: dict,
    summary: str,
    filename: str,
    rules: dict,
) -> None:
    """Provide download buttons for cleaned, invalid, and summary exports."""
    st.markdown('<p class="section-header">Download Center</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Export cleaned data, invalid records, and client-ready summary reports.</p>',
        unsafe_allow_html=True,
    )

    base_name = filename.rsplit(".", 1)[0] if filename else "transactions"
    invalid_df = get_invalid_records(validated_df)
    summary_df = build_summary_dataframe(report, insights=insights, executive_summary=summary)

    dl1, dl2, dl3, dl4 = st.columns(4)

    with dl1:
        st.download_button(
            label="⬇️ Download Cleaned CSV",
            data=dataframe_to_csv_bytes(validated_df),
            file_name=f"{base_name}_cleaned.csv",
            mime="text/csv",
            width='stretch',
        )

    with dl2:
        st.download_button(
            label="⬇️ Download Invalid Records",
            data=dataframe_to_csv_bytes(invalid_df),
            file_name=f"{base_name}_invalid.csv",
            mime="text/csv",
            width='stretch',
            disabled=invalid_df.empty,
        )

    with dl3:
        st.download_button(
            label="⬇️ Download Validation Summary (CSV)",
            data=dataframe_to_csv_bytes(summary_df),
            file_name=f"{base_name}_validation_summary.csv",
            mime="text/csv",
            width='stretch',
        )

    with dl4:
        pdf_bytes = generate_validation_pdf(report, insights, summary, filename, rules)
        st.download_button(
            label="⬇️ Download Validation Summary (PDF)",
            data=pdf_bytes,
            file_name=f"{base_name}_validation_summary.pdf",
            mime="application/pdf",
            width='stretch',
        )

    chunk_size = rules.get("chunk_size", CHUNK_SIZE)
    if len(validated_df) > chunk_size:
        st.divider()
        st.markdown(
            f"**Chunked exports** — dataset exceeds **{chunk_size}** rows. "
            "Download split parts for downstream processing."
        )
        chunks = chunk_dataframe(validated_df, chunk_size)
        chunk_cols = st.columns(min(len(chunks), 4))

        for i, chunk in enumerate(chunks):
            part_num = i + 1
            with chunk_cols[i % len(chunk_cols)]:
                st.download_button(
                    label=f"cleaned_part_{part_num}.csv ({len(chunk)} rows)",
                    data=dataframe_to_csv_bytes(chunk),
                    file_name=f"{base_name}_cleaned_part_{part_num}.csv",
                    mime="text/csv",
                    width='stretch',
                    key=f"chunk_download_{part_num}",
                )


def render_empty_state() -> None:
    """Show placeholder when no file has been uploaded."""
    st.info(
        "Upload a transaction CSV to begin validation and generate AI-powered insights."
    )

    with st.expander("Expected CSV columns (examples)", expanded=False):
        st.markdown(
            """
            | Field | Example column names |
            |-------|---------------------|
            | Phone | `phone`, `mobile`, `contact_number` |
            | Date | `order_date`, `transaction_date`, `date` |
            | Payment | `payment_mode`, `payment_method` |
            | Email | `email`, `customer_email` |
            | Country | `country`, `customer_country`, `region` |
            | Numeric | `amount`, `quantity`, `price`, `total` |
            """
        )


def main() -> None:
    """Application main loop."""
    init_session_state()
    render_header()
    rules = render_rules_editor()
    render_upload_section(rules)

    if (
        st.session_state["validated_df"] is not None
        and st.session_state["report"] is not None
        and st.session_state["insights"] is not None
    ):
        validated_df = st.session_state["validated_df"]
        report = st.session_state["report"]
        insights = st.session_state["insights"]
        summary = st.session_state["executive_summary"] or ""
        filename = st.session_state["filename"] or "transactions.csv"

        st.divider()
        render_executive_summary(insights, summary)

        st.divider()
        render_insights(insights)

        st.divider()
        render_visual_analytics(insights)

        st.divider()
        render_metrics(report)
        render_column_detection(report)

        st.divider()
        render_preview(validated_df)

        st.divider()
        render_download_section(validated_df, report, insights, summary, filename, rules)
    else:
        render_empty_state()


if __name__ == "__main__":
    main()

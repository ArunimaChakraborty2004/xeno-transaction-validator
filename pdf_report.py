"""
PDF validation summary report generator.

Produces a client-ready PDF containing dataset statistics, quality score,
validation breakdown, executive summary, and generation timestamp.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional

from fpdf import FPDF

from config import APP_TITLE


class ValidationSummaryPDF(FPDF):
    """Custom PDF document with branded header/footer."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(15, 23, 42)
        self.cell(0, 10, APP_TITLE, ln=True)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, "Validation Summary Report", ln=True)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _sanitize_text(text: str) -> str:
    """Replace characters that Helvetica cannot render reliably."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "**": "",
    }
    cleaned = text
    for src, dst in replacements.items():
        cleaned = cleaned.replace(src, dst)
    return cleaned.encode("latin-1", errors="replace").decode("latin-1")


def _section_title(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 8, title, ln=True)
    pdf.set_text_color(15, 23, 42)
    pdf.ln(1)


def _body_text(pdf: FPDF, text: str, line_height: float = 6.0) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, line_height, _sanitize_text(text))
    pdf.ln(2)


def _key_value_table(pdf: FPDF, rows: List[tuple[str, str]]) -> None:
    pdf.set_font("Helvetica", "", 10)
    col_width = pdf.w - pdf.l_margin - pdf.r_margin
    label_width = col_width * 0.45
    value_width = col_width * 0.55

    for label, value in rows:
        pdf.set_fill_color(248, 250, 252)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_width, 7, _sanitize_text(label), border=1, fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(value_width, 7, _sanitize_text(str(value)), border=1, ln=True)


def generate_validation_pdf(
    report: Dict[str, object],
    insights: Dict[str, object],
    executive_summary: str,
    filename: str,
    validation_rules: Dict[str, object],
    generated_at: Optional[datetime] = None,
) -> bytes:
    """
    Build a validation summary PDF and return raw bytes for download.

    Args:
        report: Validation report dictionary.
        insights: Insights dictionary from the analytics layer.
        executive_summary: Human-readable summary text (markdown allowed).
        filename: Original uploaded filename for reference.
        validation_rules: Active session validation rules.
        generated_at: Report timestamp (defaults to now).

    Returns:
        PDF file contents as bytes.
    """
    timestamp = generated_at or datetime.now()
    pdf = ValidationSummaryPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    _section_title(pdf, "Report Metadata")
    _key_value_table(
        pdf,
        [
            ("Generated at", timestamp.strftime("%Y-%m-%d %H:%M:%S")),
            ("Source file", filename or "Unknown"),
            ("Validation country", str(validation_rules.get("country_name", ""))),
            ("Phone digit rule", str(validation_rules.get("phone_digits", ""))),
            ("Chunk size", str(validation_rules.get("chunk_size", ""))),
        ],
    )
    pdf.ln(4)

    _section_title(pdf, "Dataset Statistics")
    _key_value_table(
        pdf,
        [
            ("Total records", f"{int(report.get('total_records', 0)):,}"),
            ("Valid records", f"{int(report.get('valid_records', 0)):,}"),
            ("Invalid records", f"{int(report.get('invalid_records', 0)):,}"),
            ("Pass rate", f"{report.get('validation_rate', 0)}%"),
            ("Missing data", f"{insights.get('missing_data_pct', 0)}%"),
            ("Duplicate records", f"{int(insights.get('duplicate_count', 0)):,}"),
        ],
    )
    pdf.ln(4)

    _section_title(pdf, "Data Quality Score")
    score = insights.get("quality_score", 0)
    label = insights.get("quality_label", "")
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 12, f"{score} / 100", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, f"Quality tier: {label}", ln=True)
    pdf.ln(4)

    _section_title(pdf, "Validation Breakdown")
    breakdown = report.get("error_breakdown", {})
    if breakdown:
        pdf.set_font("Helvetica", "B", 10)
        col_width = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.cell(col_width * 0.65, 7, "Category", border=1, fill=True)
        pdf.cell(col_width * 0.35, 7, "Count", border=1, ln=True, fill=True)
        pdf.set_font("Helvetica", "", 10)
        for category, count in breakdown.items():
            pdf.cell(col_width * 0.65, 7, _sanitize_text(str(category)), border=1)
            pdf.cell(col_width * 0.35, 7, str(count), border=1, ln=True)
    else:
        _body_text(pdf, "No validation errors were detected.")
    pdf.ln(4)

    _section_title(pdf, "Executive Summary")
    _body_text(pdf, executive_summary)

    _section_title(pdf, "Active Validation Rules")
    modes = validation_rules.get("allowed_payment_modes", [])
    modes_text = ", ".join(str(m) for m in modes) if modes else "None configured"
    _body_text(
        pdf,
        f"Country: {validation_rules.get('country_name', '')}. "
        f"Phone length: {validation_rules.get('phone_digits', '')} digits. "
        f"Allowed payment modes: {modes_text}.",
    )

    # Use the universal output method that works in both fpdf (legacy) and fpdf2
    # In legacy fpdf, this returns a string. In fpdf2, it returns a bytearray.
    try:
        out = pdf.output(dest="S")
        if isinstance(out, str):
            return out.encode("latin-1")
        return bytes(out)
    except Exception:
        # Fallback for fpdf2 if dest="S" is ever fully removed
        out = pdf.output()
        return bytes(out) if out else b""

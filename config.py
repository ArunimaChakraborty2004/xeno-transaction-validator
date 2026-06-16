"""
Configuration module for Xeno Transaction Validator.

Centralizes validation rules, allowed values, and application settings
so new countries or rules can be added without touching core logic.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Phone validation rules by country (digits only, after stripping formatting)
# ---------------------------------------------------------------------------
PHONE_COUNTRY_RULES: Dict[str, Dict[str, object]] = {
    "India": {
        "code": "IN",
        "digits": 10,
        "description": "10-digit mobile number",
    },
    "Singapore": {
        "code": "SG",
        "digits": 8,
        "description": "8-digit phone number",
    },
    "United States": {
        "code": "US",
        "digits": 10,
        "description": "10-digit phone number",
    },
    "United Kingdom": {
        "code": "GB",
        "digits": 10,
        "description": "10-digit phone number",
    },
}

DEFAULT_COUNTRY: str = "India"

# ---------------------------------------------------------------------------
# Payment mode validation
# ---------------------------------------------------------------------------
ALLOWED_PAYMENT_MODES: List[str] = [
    "UPI",
    "Card",
    "Cash",
    "Net Banking",
    "Wallet",
]

# Case-insensitive lookup map (normalized key -> canonical value)
PAYMENT_MODE_LOOKUP: Dict[str, str] = {
    mode.lower(): mode for mode in ALLOWED_PAYMENT_MODES
}

# ---------------------------------------------------------------------------
# Date format patterns (strftime-compatible)
# ---------------------------------------------------------------------------
SUPPORTED_DATE_FORMATS: List[str] = [
    "%Y-%m-%d",   # YYYY-MM-DD
    "%d-%m-%Y",   # DD-MM-YYYY
    "%d/%m/%Y",   # DD/MM/YYYY
    "%Y/%m/%d",   # YYYY/MM/DD
    "%m-%d-%Y",   # MM-DD-YYYY
    "%d.%m.%Y",   # DD.MM.YYYY
]

DATE_FORMAT_LABELS: Dict[str, str] = {
    "%Y-%m-%d": "YYYY-MM-DD",
    "%d-%m-%Y": "DD-MM-YYYY",
    "%d/%m/%Y": "DD/MM/YYYY",
    "%Y/%m/%d": "YYYY/MM/DD",
    "%m-%d-%Y": "MM-DD-YYYY",
    "%d.%m.%Y": "DD.MM.YYYY",
}

# ---------------------------------------------------------------------------
# Column name heuristics for auto-detection in uploaded CSVs
# ---------------------------------------------------------------------------
PHONE_COLUMN_KEYWORDS: List[str] = [
    "phone",
    "mobile",
    "contact",
    "telephone",
    "cell",
    "phone_number",
    "mobile_number",
    "contact_number",
]

DATE_COLUMN_KEYWORDS: List[str] = [
    "date",
    "order_date",
    "transaction_date",
    "payment_date",
    "created_at",
    "order_time",
    "txn_date",
]

PAYMENT_COLUMN_KEYWORDS: List[str] = [
    "payment_mode",
    "payment_method",
    "payment_type",
    "pay_mode",
    "mode_of_payment",
    "payment",
]

EMAIL_COLUMN_KEYWORDS: List[str] = [
    "email",
    "email_address",
    "customer_email",
    "user_email",
    "e_mail",
]

ORDER_ID_COLUMN_KEYWORDS: List[str] = [
    "order_id",
    "order_number",
    "order_no",
    "transaction_id",
    "txn_id",
    "invoice_id",
]

COUNTRY_COLUMN_KEYWORDS: List[str] = [
    "country",
    "nation",
    "region",
    "customer_country",
    "billing_country",
    "shipping_country",
    "country_name",
    "geo",
]

NUMERIC_COLUMN_KEYWORDS: List[str] = [
    "amount",
    "price",
    "total",
    "quantity",
    "qty",
    "cost",
    "value",
    "subtotal",
    "tax",
    "discount",
    "unit_price",
]

# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = 100
MAX_PREVIEW_ROWS: int = 50
APP_TITLE: str = "Xeno Transaction Validator"
APP_TAGLINE: str = "Enterprise-grade transaction validation, analytics, and export."
APP_BRAND: str = "Xeno"

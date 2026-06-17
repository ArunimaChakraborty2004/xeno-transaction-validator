"""
Validation rules management for dynamic, session-scoped configuration.

Rules are stored in Streamlit session state and applied immediately
to the validation engine without restarting the application.
"""

from __future__ import annotations

import re
from typing import Dict, List

import streamlit as st

from config import ALLOWED_PAYMENT_MODES, CHUNK_SIZE, DEFAULT_COUNTRY, PHONE_COUNTRY_RULES
from utils import build_payment_lookup


RulesDict = Dict[str, object]


def get_default_rules() -> RulesDict:
    """Return factory-default validation rules from static configuration."""
    default_country = DEFAULT_COUNTRY
    phone_digits = int(PHONE_COUNTRY_RULES[default_country]["digits"])
    return {
        "country_name": default_country,
        "phone_digits": phone_digits,
        "allowed_payment_modes": list(ALLOWED_PAYMENT_MODES),
        "chunk_size": CHUNK_SIZE,
    }


def build_payment_lookup(modes: List[str]) -> Dict[str, str]:
    """Build a case-insensitive payment mode lookup from a mode list."""
    return {m.strip().lower(): m.strip() for m in modes if m.strip()}


def parse_payment_modes_text(text: str) -> List[str]:
    """Parse comma- or newline-separated payment modes from editor text."""
    if not text or not text.strip():
        return []

    modes: List[str] = []
    seen = set()
    for part in re.split(r"[\n,]+", text):
        cleaned = part.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            modes.append(cleaned)
    return modes


def payment_modes_to_text(modes: List[str]) -> str:
    """Serialize payment modes for the rules editor text area."""
    return "\n".join(modes)


def normalize_rules(rules: RulesDict) -> RulesDict:
    """Normalize and validate rule values before applying them."""
    country_name = str(rules.get("country_name", DEFAULT_COUNTRY)).strip() or DEFAULT_COUNTRY
    phone_digits = int(rules.get("phone_digits", 10))
    phone_digits = max(6, min(15, phone_digits))

    modes_raw = rules.get("allowed_payment_modes", [])
    if isinstance(modes_raw, str):
        modes = parse_payment_modes_text(modes_raw)
    else:
        modes = [str(m).strip() for m in modes_raw if str(m).strip()]

    if not modes:
        modes = list(ALLOWED_PAYMENT_MODES)

    chunk_size = int(rules.get("chunk_size", CHUNK_SIZE))
    chunk_size = max(10, min(1000, chunk_size))

    return {
        "country_name": country_name,
        "phone_digits": phone_digits,
        "allowed_payment_modes": modes,
        "chunk_size": chunk_size,
    }


def rules_equal(left: RulesDict, right: RulesDict) -> bool:
    """Compare two rule dictionaries for equality."""
    left_norm = normalize_rules(left)
    right_norm = normalize_rules(right)
    return left_norm == right_norm


def init_rules_session_state() -> None:
    """Initialize validation rules in Streamlit session state."""
    if "validation_rules" not in st.session_state:
        st.session_state.validation_rules = get_default_rules()
    if "rules_version" not in st.session_state:
        st.session_state.rules_version = 0


def render_rules_editor() -> RulesDict:
    """
    Render the sidebar validation rules editor.

    Returns:
        Normalized rules dictionary reflecting current widget values.
    """
    init_rules_session_state()
    current = normalize_rules(st.session_state.validation_rules)

    st.sidebar.markdown("### Validation Rules Editor")
    st.sidebar.caption("Changes apply immediately to the active dataset.")

    country_name = st.sidebar.text_input(
        "Country name",
        value=str(current["country_name"]),
        help="Display name used in reports and phone validation context.",
        key="rules_country_name",
    )

    phone_digits = st.sidebar.number_input(
        "Required phone length (digits)",
        min_value=6,
        max_value=15,
        value=int(current["phone_digits"]),
        step=1,
        help="Phone numbers must contain exactly this many digits.",
        key="rules_phone_digits",
    )

    payment_text = st.sidebar.text_area(
        "Allowed payment modes",
        value=payment_modes_to_text(list(current["allowed_payment_modes"])),
        height=120,
        help="Enter one payment mode per line (or comma-separated).",
        key="rules_payment_modes",
    )

    chunk_size = st.sidebar.number_input(
        "Maximum chunk size (rows)",
        min_value=10,
        max_value=1000,
        value=int(current["chunk_size"]),
        step=10,
        help="CSV exports are split when row count exceeds this value.",
        key="rules_chunk_size",
    )

    btn_col1, btn_col2 = st.sidebar.columns(2)
    with btn_col1:
        if st.button("Reset defaults", width='stretch', key="rules_reset"):
            st.session_state.validation_rules = get_default_rules()
            st.session_state.rules_version += 1
            for widget_key in ["rules_country_name", "rules_phone_digits", "rules_payment_modes", "rules_chunk_size"]:
                if widget_key in st.session_state:
                    del st.session_state[widget_key]
            st.rerun()

    new_rules = normalize_rules(
        {
            "country_name": country_name,
            "phone_digits": phone_digits,
            "allowed_payment_modes": parse_payment_modes_text(payment_text),
            "chunk_size": chunk_size,
        }
    )

    with btn_col2:
        if st.button("Apply now", width='stretch', key="rules_apply"):
            st.session_state.validation_rules = new_rules
            st.session_state.rules_version += 1
            st.rerun()

    if not rules_equal(new_rules, st.session_state.validation_rules):
        st.session_state.validation_rules = new_rules
        st.session_state.rules_version += 1

    st.sidebar.info(
        f"**{new_rules['country_name']}** — {new_rules['phone_digits']} digit phones · "
        f"{len(new_rules['allowed_payment_modes'])} payment modes · "
        f"chunk size {new_rules['chunk_size']}"
    )

    st.sidebar.divider()
    return new_rules

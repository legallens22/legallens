"""
lm_rules_2011.py

Encodes the mandatory declarations required on pre-packaged commodities
under the Legal Metrology (Packaged Commodities) Rules, 2011 (India).

This file has ONE job: define what fields are required, and for each
field, a function that decides whether a piece of OCR'd text is a VALID
value for that field. It does NOT touch OCR data directly and does NOT
know anything about bounding boxes/images - that's rule_engine.py's job.

Each rule is intentionally kept as a small, testable, pure function so
that:
  1. You can unit test each validator in isolation.
  2. When a judge asks "why did this fail?", you can point to one function.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional


@dataclass
class FieldRule:
    field_key: str          # internal key, matches field_classifier.py output
    display_name: str       # human-readable, shown on the dashboard
    required: bool          # is this one of the 6 mandatory declarations?
    validator: Callable[[str], bool]   # returns True if the text is a valid value
    description: str        # shown in the report / used in pitch Q&A
    # Best-effort pointer into Rule 6 of the Legal Metrology (Packaged
    # Commodities) Rules, 2011. ASSUMPTION: sub-clause lettering below is
    # our best-effort mapping for the pitch/demo, not a verified legal
    # citation - worth double-checking against the actual gazette text
    # before quoting it to a judge as authoritative.
    legal_reference: str = ""


# ---------------------------------------------------------------------------
# Individual validators
# Each takes the raw text string for a field and returns True/False.
# Keep these permissive-but-strict: real labels are messy (OCR noise, odd
# spacing), but we still need to catch genuinely missing/malformed info.
# ---------------------------------------------------------------------------

def validate_mrp(text: str) -> bool:
    """
    MRP must contain a currency indicator (Rs/₹/INR) and a positive
    number. A price of 0 or negative isn't a plausible MRP - almost
    certainly an OCR/classification error, not a real declaration.
    """
    if not text:
        return False
    has_currency = bool(re.search(r"(₹|rs\.?|inr)", text, re.IGNORECASE))
    match = re.search(r"(\d+(\.\d{1,2})?)", text)
    if not (has_currency and match):
        return False
    value = float(match.group(1))
    return value > 0


def validate_net_quantity(text: str) -> bool:
    """
    Net quantity must have a number followed by a standard unit.
    NOTE: a bare "n" as a unit was removed - it matched too many
    unrelated digit+letter OCR fragments (false positives). Count-based
    quantities now require an explicit word like "pcs"/"pieces"/"units".
    """
    if not text:
        return False
    units = r"(g|kg|mg|ml|l|litre|liter|gram|kilogram|pcs|pieces?|units?)"
    pattern = rf"\d+(\.\d+)?\s*{units}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def validate_manufacturer(text: str) -> bool:
    """
    Manufacturer/packer/importer name + address.

    Primary signal: the "Mfg/Marketed/Packed by" style keyword together
    with a 6-digit PIN-code-shaped token, since a real Indian address
    declaration almost always ends in one.

    Fallback signal (kept from the original check, for cases where OCR
    missed the PIN code): keyword + minimum length + enough distinct
    words that it's plausibly a real name/address rather than the
    keyword itself repeated to pad length out past the threshold.
    """
    if not text:
        return False
    keyword = bool(re.search(r"(mfg|manufactur|market(ed)?|pack(ed)?|import)", text, re.IGNORECASE))
    if not keyword:
        return False

    has_pin_code = bool(re.search(r"\b\d{6}\b", text))
    if has_pin_code:
        return True

    long_enough = len(text.strip()) >= 15
    distinct_words = {w.lower() for w in re.findall(r"[A-Za-z]+", text)}
    # ASSUMPTION: requiring 4+ distinct words is a heuristic floor for
    # "this looks like a real name/address" rather than a keyword padded
    # out with repetition (e.g. "Mfg by Mfg by Mfg by Mfg by Mfg by").
    plausible_content = len(distinct_words) >= 4
    return long_enough and plausible_content


def validate_consumer_care(text: str) -> bool:
    """Consumer care needs a phone number OR an email address."""
    if not text:
        return False
    has_phone = bool(re.search(r"(\+?\d[\d\-\s]{7,}\d)", text))
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text))
    return has_phone or has_email


# ASSUMPTION: a manufacture date more than ~15 years in the past is
# implausible for a packaged commodity label (shelf life, printing
# equipment, business existence, etc. all make this a reasonable floor
# for a prototype) - flagged here as a named constant so it's easy to
# revisit rather than a silent magic number.
MAX_PLAUSIBLE_AGE_YEARS = 15


def _parsed_month_year(text: str):
    """
    Best-effort extraction of a (year, month) tuple from the date
    formats validate_mfg_date accepts, for plausibility checking.
    Returns None if nothing parseable was found.
    """
    month_names = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    m = re.search(r"\b(\d{1,2})/(\d{4})\b", text)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return year, month

    m = re.search(r"\b\d{1,2}/(\d{1,2})/(\d{2,4})\b", text)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if year < 100:
            year += 2000
        if 1 <= month <= 12:
            return year, month

    m = re.search(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})\b",
        text, re.IGNORECASE,
    )
    if m:
        return int(m.group(2)), month_names[m.group(1).lower()]

    return None


def validate_mfg_date(text: str) -> bool:
    """
    Date of manufacture/import - accept common formats (MM/YYYY,
    DD/MM/YYYY, Month YYYY), and reject dates that aren't plausible:
    a date after today (can't manufacture in the future) or one more
    than MAX_PLAUSIBLE_AGE_YEARS in the past (see assumption above).
    """
    if not text:
        return False
    patterns = [
        r"\b\d{1,2}/\d{4}\b",                     # 03/2026
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",            # 15/03/2026
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b",
    ]
    if not any(re.search(p, text, re.IGNORECASE) for p in patterns):
        return False

    parsed = _parsed_month_year(text)
    if parsed is None:
        # Matched a pattern above but couldn't be parsed for plausibility
        # (shouldn't normally happen) - fall back to format-only pass
        # rather than silently failing a validly-formatted date.
        return True

    year, month = parsed
    today = date.today()
    parsed_date = date(year, month, 1)
    if parsed_date > date(today.year, today.month, 1):
        return False
    earliest_plausible = date(today.year - MAX_PLAUSIBLE_AGE_YEARS, today.month, 1)
    if parsed_date < earliest_plausible:
        return False
    return True


def validate_country_of_origin(text: str) -> bool:
    """Must explicitly name a country - most commonly 'Made in India'."""
    if not text:
        return False
    return bool(re.search(r"(made in|country of origin|origin\s*:)\s*[a-zA-Z]+", text, re.IGNORECASE))


def validate_commodity_name(text: str) -> bool:
    """
    Common/generic name of the commodity (e.g. "Refined Sunflower Oil").
    Deliberately simple for this pass: just checks for plausible,
    non-trivial text rather than parsing/validating against a product
    taxonomy.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < 2:
        return False
    return bool(re.search(r"[A-Za-z]{2,}", stripped))


# ---------------------------------------------------------------------------
# The 6 mandatory fields under LM Rules 2011, Rule 6
# ---------------------------------------------------------------------------

MANDATORY_FIELDS: list[FieldRule] = [
    FieldRule(
        field_key="mrp",
        display_name="Maximum Retail Price (MRP)",
        required=True,
        validator=validate_mrp,
        description="Must be inclusive of all taxes, shown with currency symbol.",
        legal_reference="Rule 6(1)(e)",
    ),
    FieldRule(
        field_key="net_quantity",
        display_name="Net Quantity",
        required=True,
        validator=validate_net_quantity,
        description="Standard unit of weight/measure/number, per Rule 6/8.",
        legal_reference="Rule 6(1)(b)",
    ),
    FieldRule(
        field_key="manufacturer",
        display_name="Manufacturer / Packer / Importer Name & Address",
        required=True,
        validator=validate_manufacturer,
        description="Name and complete address of the entity responsible for the product.",
        legal_reference="Rule 6(1)(a)",
    ),
    FieldRule(
        field_key="consumer_care",
        display_name="Consumer Care Details",
        required=True,
        validator=validate_consumer_care,
        description="Phone number and/or email for consumer complaints.",
        legal_reference="Rule 6(1)(f)",
    ),
    FieldRule(
        field_key="mfg_date",
        display_name="Date of Manufacture / Import",
        required=True,
        validator=validate_mfg_date,
        description="Month and year, at minimum.",
        legal_reference="Rule 6(1)(d)",
    ),
    FieldRule(
        field_key="country_of_origin",
        display_name="Country of Origin",
        required=True,
        validator=validate_country_of_origin,
        description="Mandatory since 2020 amendment, esp. relevant for imported goods.",
        legal_reference="Rule 6(1)(g) (2020 amendment)",
    ),
    FieldRule(
        field_key="commodity_name",
        display_name="Common / Generic Name of Commodity",
        required=True,
        validator=validate_commodity_name,
        description="The generic name of the product itself (e.g. 'Refined Sunflower Oil').",
        legal_reference="Rule 6(1)(a)",
    ),
]


def get_rule(field_key: str) -> Optional[FieldRule]:
    """Convenience lookup used by rule_engine.py."""
    for rule in MANDATORY_FIELDS:
        if rule.field_key == field_key:
            return rule
    return None

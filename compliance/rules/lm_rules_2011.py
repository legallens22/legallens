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
from typing import Callable, Optional


@dataclass
class FieldRule:
    field_key: str          # internal key, matches field_classifier.py output
    display_name: str       # human-readable, shown on the dashboard
    required: bool          # is this one of the 6 mandatory declarations?
    validator: Callable[[str], bool]   # returns True if the text is a valid value
    description: str        # shown in the report / used in pitch Q&A


# ---------------------------------------------------------------------------
# Individual validators
# Each takes the raw text string for a field and returns True/False.
# Keep these permissive-but-strict: real labels are messy (OCR noise, odd
# spacing), but we still need to catch genuinely missing/malformed info.
# ---------------------------------------------------------------------------

def validate_mrp(text: str) -> bool:
    """MRP must contain a currency indicator (Rs/₹/INR) and a number."""
    if not text:
        return False
    has_currency = bool(re.search(r"(₹|rs\.?|inr)", text, re.IGNORECASE))
    has_number = bool(re.search(r"\d+(\.\d{1,2})?", text))
    return has_currency and has_number


def validate_net_quantity(text: str) -> bool:
    """Net quantity must have a number followed by a standard unit."""
    if not text:
        return False
    units = r"(g|kg|mg|ml|l|litre|liter|gram|kilogram|pcs|piece|n|units?)"
    pattern = rf"\d+(\.\d+)?\s*{units}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def validate_manufacturer(text: str) -> bool:
    """
    Manufacturer/packer/importer name + address.
    We can't verify a real address exists, so we check for a plausible
    signal: a "Mfg/Marketed/Packed by" style keyword AND enough length
    to plausibly contain a name + address (avoids false-passing on a
    stray short OCR fragment).
    """
    if not text:
        return False
    keyword = bool(re.search(r"(mfg|manufactur|market(ed)?|pack(ed)?|import)", text, re.IGNORECASE))
    long_enough = len(text.strip()) >= 15
    return keyword and long_enough


def validate_consumer_care(text: str) -> bool:
    """Consumer care needs a phone number OR an email address."""
    if not text:
        return False
    has_phone = bool(re.search(r"(\+?\d[\d\-\s]{7,}\d)", text))
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text))
    return has_phone or has_email


def validate_mfg_date(text: str) -> bool:
    """
    Date of manufacture/import - accept common formats:
    MM/YYYY, DD/MM/YYYY, Month YYYY, etc.
    """
    if not text:
        return False
    patterns = [
        r"\b\d{1,2}/\d{4}\b",                     # 03/2026
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",            # 15/03/2026
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def validate_country_of_origin(text: str) -> bool:
    """Must explicitly name a country - most commonly 'Made in India'."""
    if not text:
        return False
    return bool(re.search(r"(made in|country of origin|origin\s*:)\s*[a-zA-Z]+", text, re.IGNORECASE))


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
    ),
    FieldRule(
        field_key="net_quantity",
        display_name="Net Quantity",
        required=True,
        validator=validate_net_quantity,
        description="Standard unit of weight/measure/number, per Rule 6/8.",
    ),
    FieldRule(
        field_key="manufacturer",
        display_name="Manufacturer / Packer / Importer Name & Address",
        required=True,
        validator=validate_manufacturer,
        description="Name and complete address of the entity responsible for the product.",
    ),
    FieldRule(
        field_key="consumer_care",
        display_name="Consumer Care Details",
        required=True,
        validator=validate_consumer_care,
        description="Phone number and/or email for consumer complaints.",
    ),
    FieldRule(
        field_key="mfg_date",
        display_name="Date of Manufacture / Import",
        required=True,
        validator=validate_mfg_date,
        description="Month and year, at minimum.",
    ),
    FieldRule(
        field_key="country_of_origin",
        display_name="Country of Origin",
        required=True,
        validator=validate_country_of_origin,
        description="Mandatory since 2020 amendment, esp. relevant for imported goods.",
    ),
]


def get_rule(field_key: str) -> Optional[FieldRule]:
    """Convenience lookup used by rule_engine.py."""
    for rule in MANDATORY_FIELDS:
        if rule.field_key == field_key:
            return rule
    return None

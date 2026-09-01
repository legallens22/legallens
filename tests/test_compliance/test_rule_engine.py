"""
Run with:  pytest tests/test_compliance/ -v
(from the project root, so the `compliance` package is importable)
"""

import json
import os
import sys

# Make sure the project root is on the path when running this file directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from compliance.rules.lm_rules_2011 import (
    validate_mrp,
    validate_net_quantity,
    validate_manufacturer,
    validate_consumer_care,
    validate_mfg_date,
    validate_country_of_origin,
)
from compliance.rule_engine import evaluate_label, overall_verdict, Verdict
from compliance.report_generator import generate_report

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "sample_ocr_outputs")


def load_sample(filename: str) -> dict:
    with open(os.path.join(SAMPLE_DIR, filename)) as f:
        return json.load(f)


# --- Validator unit tests ---------------------------------------------------

def test_validate_mrp():
    assert validate_mrp("MRP Rs. 120.00 (incl. of all taxes)") is True
    assert validate_mrp("Rs 85") is True
    assert validate_mrp("just a random string") is False
    assert validate_mrp("") is False


def test_validate_net_quantity():
    assert validate_net_quantity("Net Qty: 500 g") is True
    assert validate_net_quantity("500ml") is True
    assert validate_net_quantity("no units here") is False


def test_validate_manufacturer():
    assert validate_manufacturer("Mfg by: Sunrise Foods Pvt Ltd, Pune") is True
    assert validate_manufacturer("Mfg") is False  # keyword present but too short
    assert validate_manufacturer("Sunrise Foods") is False  # no keyword


def test_validate_consumer_care():
    assert validate_consumer_care("Customer Care: 1800-123-4567") is True
    assert validate_consumer_care("care@sunrisefoods.in") is True
    assert validate_consumer_care("no contact info") is False


def test_validate_mfg_date():
    assert validate_mfg_date("Mfg Date: 03/2026") is True
    assert validate_mfg_date("15/03/2026") is True
    assert validate_mfg_date("March 2026") is True
    assert validate_mfg_date("sometime recently") is False


def test_validate_country_of_origin():
    assert validate_country_of_origin("Made in India") is True
    assert validate_country_of_origin("Country of Origin: China") is True
    assert validate_country_of_origin("India") is False  # no explicit signal keyword


# --- End-to-end pipeline tests using the fake sample JSONs ------------------

def test_label_001_fully_compliant():
    """label_001.json has all 6 fields present with decent confidence -> PASS."""
    payload = load_sample("label_001.json")
    results = evaluate_label(payload)
    assert len(results) == 6
    assert overall_verdict(results) == Verdict.PASS

    report = generate_report("label_001", payload)
    assert report["overall_verdict"] == "PASS"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["missing"] == 0


def test_label_002_missing_and_low_confidence():
    """
    label_002.json only has MRP (low confidence), net_quantity, and
    manufacturer -> expect MRP to be NEEDS_MANUAL_REVIEW, three fields
    MISSING, overall verdict FAIL (because of the missing fields).
    """
    payload = load_sample("label_002.json")
    results = evaluate_label(payload)
    by_key = {r.field_key: r for r in results}

    assert by_key["mrp"].verdict == Verdict.NEEDS_MANUAL_REVIEW
    assert by_key["net_quantity"].verdict == Verdict.PASS
    assert by_key["consumer_care"].verdict == Verdict.MISSING
    assert by_key["mfg_date"].verdict == Verdict.MISSING
    assert by_key["country_of_origin"].verdict == Verdict.MISSING

    assert overall_verdict(results) == Verdict.FAIL


def test_empty_ocr_payload_does_not_crash():
    """Per the contract, OCR failure means blocks=[], never null/missing."""
    payload = {"image_id": "blank", "blocks": []}
    results = evaluate_label(payload)
    assert len(results) == 6
    assert all(r.verdict == Verdict.MISSING for r in results)
    assert overall_verdict(results) == Verdict.FAIL

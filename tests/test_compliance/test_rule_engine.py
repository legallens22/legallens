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
from compliance.rule_engine import evaluate_label, overall_verdict, Verdict, FieldResult
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
    assert validate_manufacturer("Mfg by Sunrise Foods, Pune 411019") is True  # PIN present
    assert validate_manufacturer("Mfg") is False  # keyword present but too short
    assert validate_manufacturer("Sunrise Foods") is False  # no keyword
    # Keyword repeated to pad length past the threshold, no real address
    # content and no PIN code - must fail even though it's "long enough".
    assert validate_manufacturer("Mfg by Mfg by Mfg by Mfg by") is False


def test_validate_consumer_care():
    assert validate_consumer_care("Customer Care: 1800-123-4567") is True
    assert validate_consumer_care("care@sunrisefoods.in") is True
    assert validate_consumer_care("no contact info") is False


def test_validate_mfg_date():
    assert validate_mfg_date("Mfg Date: 03/2026") is True
    assert validate_mfg_date("15/03/2026") is True
    assert validate_mfg_date("March 2026") is True
    assert validate_mfg_date("sometime recently") is False


# --- Plausibility-edge tests (Step 3: reject implausible values) -----------

def test_validate_mrp_rejects_zero():
    assert validate_mrp("Rs. 0.00") is False


def test_validate_mfg_date_rejects_future_date():
    assert validate_mfg_date("Mfg Date: 01/2035") is False


def test_validate_manufacturer_rejects_keyword_padding_without_pin():
    """A manufacturer string that pads length by repeating the keyword,
    with no real address content and no PIN code, must not pass."""
    assert validate_manufacturer("Mfg by Mfg by Mfg by Mfg by") is False


def test_validate_country_of_origin():
    assert validate_country_of_origin("Made in India") is True
    assert validate_country_of_origin("Country of Origin: China") is True
    assert validate_country_of_origin("India") is False  # no explicit signal keyword


# --- End-to-end pipeline tests using the fake sample JSONs ------------------

def test_label_001_fully_compliant():
    """label_001.json has all 7 mandatory fields present with decent confidence -> PASS."""
    payload = load_sample("label_001.json")
    results = evaluate_label(payload)
    assert len(results) == 7  # 6 original fields + commodity_name (Step 3)
    assert overall_verdict(results) == Verdict.PASS

    report = generate_report("label_001", payload)
    assert report["overall_verdict"] == "PASS"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["missing"] == 0
    assert report["scan_issue_message"] is None


def test_label_002_missing_and_low_confidence():
    """
    label_002.json only has MRP (low confidence), net_quantity, and
    manufacturer -> expect MRP to be NEEDS_MANUAL_REVIEW, remaining
    fields (including the new commodity_name) MISSING, overall verdict
    FAIL (because of the missing fields).
    """
    payload = load_sample("label_002.json")
    results = evaluate_label(payload)
    by_key = {r.field_key: r for r in results}

    assert by_key["mrp"].verdict == Verdict.NEEDS_MANUAL_REVIEW
    assert by_key["net_quantity"].verdict == Verdict.PASS
    assert by_key["consumer_care"].verdict == Verdict.MISSING
    assert by_key["mfg_date"].verdict == Verdict.MISSING
    assert by_key["country_of_origin"].verdict == Verdict.MISSING
    assert by_key["commodity_name"].verdict == Verdict.MISSING

    assert overall_verdict(results) == Verdict.FAIL


def test_empty_ocr_payload_returns_unable_to_determine():
    """
    Per the contract, OCR failure means blocks=[], never null/missing.
    Step 2 changed this from a blanket MISSING/FAIL to a distinct
    UNABLE_TO_DETERMINE outcome: a failed scan is a different claim than
    "we checked and the label is missing a declaration."
    """
    payload = {"image_id": "blank", "blocks": []}
    results = evaluate_label(payload)
    assert len(results) == 7
    assert all(r.verdict == Verdict.UNABLE_TO_DETERMINE for r in results)
    assert overall_verdict(results) == Verdict.UNABLE_TO_DETERMINE

    report = generate_report("blank", payload)
    assert report["overall_verdict"] == "UNABLE_TO_DETERMINE"
    assert report["scan_issue_message"] is not None
    assert "rescan" in report["scan_issue_message"].lower()


def test_ocr_text_present_but_none_classified_is_also_unable_to_determine():
    """
    OCR found text, but none of it matched any expected field - still a
    scan-quality problem, not a compliance failure.
    """
    payload = {
        "image_id": "gibberish",
        "blocks": [
            {"text": "xzqv wkpl", "bbox": [0, 0, 10, 10], "confidence": 0.9, "engine": "paddleocr"},
        ],
    }
    results = evaluate_label(payload)
    assert all(r.verdict == Verdict.UNABLE_TO_DETERMINE for r in results)
    assert overall_verdict(results) == Verdict.UNABLE_TO_DETERMINE


# --- Regression tests: multi-candidate handling in rule_engine.py ----------

def test_split_field_value_across_two_blocks_now_passes():
    """
    Regression test for Step 1/2: previously, best_block_per_field kept
    only the single top-ranked block per field and discarded the rest.
    If that top block failed validation (e.g. OCR split "MRP" from its
    number into two separate blocks), the field was wrongly reported
    FAIL/MISSING even though a second OCR block for the same field DID
    have a valid, well-formatted value. Now the engine falls back to a
    lower-ranked passing candidate instead of giving up.
    """
    payload = {
        "image_id": "split_mrp",
        "blocks": [
            # Higher-ranked (keyword-only, no number) - fails validation.
            {"text": "Maximum Retail Price MRP:", "bbox": [0, 0, 10, 10],
             "confidence": 0.9, "engine": "paddleocr"},
            # Lower-ranked but has the actual value - passes validation.
            {"text": "Rs. 45.00", "bbox": [0, 20, 10, 10],
             "confidence": 0.5, "engine": "paddleocr"},
        ],
    }
    results = evaluate_label(payload)
    by_key = {r.field_key: r for r in results}

    assert by_key["mrp"].verdict == Verdict.PASS
    assert by_key["mrp"].matched_text == "Rs. 45.00"
    assert "secondary" in by_key["mrp"].reason.lower()


def test_conflicting_valid_values_flagged_for_review():
    """
    Regression test for Step 2: two candidate blocks for the same field
    both independently pass validation but disagree on the actual value
    (e.g. two different prices printed/stickered on the same label).
    The engine must not silently pick one - it should flag the conflict.
    """
    payload = {
        "image_id": "conflicting_mrp",
        "blocks": [
            {"text": "Rs. 45.00", "bbox": [0, 0, 10, 10], "confidence": 0.9, "engine": "paddleocr"},
            {"text": "Rs. 60.00", "bbox": [0, 20, 10, 10], "confidence": 0.85, "engine": "paddleocr"},
        ],
    }
    results = evaluate_label(payload)
    by_key = {r.field_key: r for r in results}

    assert by_key["mrp"].verdict == Verdict.NEEDS_MANUAL_REVIEW
    assert "conflict" in by_key["mrp"].reason.lower()


def test_overall_verdict_needs_manual_review_branch():
    """Direct unit test for the NEEDS_MANUAL_REVIEW branch of overall_verdict,
    which previously had no dedicated test even though the code path existed."""
    field_results = [
        FieldResult(
            field_key="mrp", display_name="MRP", verdict=Verdict.PASS,
            matched_text="Rs. 10", confidence=0.9, reason="ok",
        ),
        FieldResult(
            field_key="net_quantity", display_name="Net Quantity",
            verdict=Verdict.NEEDS_MANUAL_REVIEW, matched_text="50g",
            confidence=0.3, reason="low confidence",
        ),
    ]
    assert overall_verdict(field_results) == Verdict.NEEDS_MANUAL_REVIEW


def test_malformed_blocks_entry_does_not_raise():
    """A blocks list containing a non-dict entry (e.g. upstream bug) must
    not crash the evaluation - the malformed entry is skipped cleanly."""
    payload = {
        "image_id": "malformed",
        "blocks": [
            {"text": "Made in India", "bbox": [0, 0, 10, 10], "confidence": 0.9, "engine": "paddleocr"},
            "this is not a dict",
            None,
            42,
        ],
    }
    results = evaluate_label(payload)  # must not raise
    by_key = {r.field_key: r for r in results}
    assert by_key["country_of_origin"].verdict == Verdict.PASS

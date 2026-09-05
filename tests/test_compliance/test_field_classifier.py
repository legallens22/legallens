"""
Direct unit tests for field_classifier.py. Before this pass, this file
did not exist - field_classifier.py was only exercised indirectly through
rule_engine.py's end-to-end tests.

Run with:  pytest tests/test_compliance/ -v
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from compliance.field_classifier import (
    ClassifiedBlock,
    classify_block,
    classify_blocks,
    best_block_per_field,
)


def test_unclassifiable_block_returns_empty_list():
    block = {"text": "xyzabc qwerty", "bbox": [0, 0, 1, 1], "confidence": 0.9, "engine": "paddleocr"}
    assert classify_block(block) == []


def test_clear_single_field_match_returns_one_candidate():
    block = {"text": "Made in India", "bbox": [0, 0, 1, 1], "confidence": 0.9, "engine": "paddleocr"}
    result = classify_block(block)
    assert len(result) == 1
    assert result[0].field_key == "country_of_origin"


def test_tied_block_becomes_candidate_for_both_fields():
    """
    A block that scores near-equally for two fields (within TIE_MARGIN)
    must become a candidate for both, not just the top scorer - this is
    the Step 1 fix. "Mfg by ..." scores 1 for manufacturer; "email"/"@"
    scores 2 for consumer_care; the 1-point gap is within TIE_MARGIN.
    """
    block = {
        "text": "Mfg by ABC Foods, email: abc@example.com",
        "bbox": [0, 0, 1, 1],
        "confidence": 0.9,
        "engine": "paddleocr",
    }
    result = classify_block(block)
    field_keys = {cb.field_key for cb in result}
    assert "manufacturer" in field_keys
    assert "consumer_care" in field_keys
    assert len(result) == 2


def test_classify_blocks_skips_non_dict_entries():
    payload = {
        "image_id": "x",
        "blocks": [
            {"text": "Made in India", "bbox": [0, 0, 1, 1], "confidence": 0.9, "engine": "paddleocr"},
            "not a dict",
            None,
        ],
    }
    classified = classify_blocks(payload)  # must not raise
    assert len(classified) == 1
    assert classified[0].field_key == "country_of_origin"


def test_best_block_per_field_returns_ranked_list_not_single_winner():
    """
    Regression test for Step 1: best_block_per_field used to return a
    single ClassifiedBlock per field_key (the top scorer), discarding
    every other candidate. It must now return a list, ranked best-first
    by confidence * classification_score.
    """
    high = ClassifiedBlock(text="high", bbox=[0, 0, 1, 1], confidence=0.9,
                            engine="paddleocr", field_key="mrp", classification_score=2)
    low = ClassifiedBlock(text="low", bbox=[0, 0, 1, 1], confidence=0.3,
                           engine="paddleocr", field_key="mrp", classification_score=1)
    mid = ClassifiedBlock(text="mid", bbox=[0, 0, 1, 1], confidence=0.6,
                           engine="paddleocr", field_key="mrp", classification_score=1)

    # Feed them in a deliberately unsorted order.
    grouped = best_block_per_field([low, high, mid])

    assert isinstance(grouped["mrp"], list)
    assert len(grouped["mrp"]) == 3
    assert [cb.text for cb in grouped["mrp"]] == ["high", "mid", "low"]


def test_best_block_per_field_groups_by_field_key():
    a = ClassifiedBlock(text="a", bbox=[0, 0, 1, 1], confidence=0.9,
                         engine="paddleocr", field_key="mrp", classification_score=1)
    b = ClassifiedBlock(text="b", bbox=[0, 0, 1, 1], confidence=0.9,
                         engine="paddleocr", field_key="net_quantity", classification_score=1)
    grouped = best_block_per_field([a, b])
    assert set(grouped.keys()) == {"mrp", "net_quantity"}

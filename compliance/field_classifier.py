"""
field_classifier.py

Input:  the raw OCR contract blocks (see shared/ocr_contract.json)
Output: the same blocks, each tagged with a `field_key` guess
        (e.g. "mrp", "net_quantity", ...) or None if unclassified.

Approach: simple keyword-density scoring per field. For each block of
OCR text, we score it against a keyword list for every candidate field
and assign it to whichever field scores highest (if above a minimum
threshold). This is intentionally simple/explainable for a prototype -
swap in an ML classifier later without changing the output shape.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# Keyword signals per field. Lowercased, matched as substrings.
# Order doesn't matter here - scoring handles ties.
FIELD_KEYWORDS: dict[str, list[str]] = {
    "mrp": ["mrp", "rs.", "rs ", "₹", "inr", "price", "maximum retail"],
    "net_quantity": ["net qty", "net quantity", "net wt", "net weight", "contents"],
    "manufacturer": ["mfg by", "manufactured by", "marketed by", "packed by",
                      "imported by", "mfg.", "manufacturer"],
    "consumer_care": ["customer care", "consumer care", "helpline", "toll free",
                       "complaint", "email", "@"],
    "mfg_date": ["mfg date", "mfd", "manufacture date", "date of mfg",
                 "packed on", "pkd"],
    "country_of_origin": ["made in", "country of origin", "origin"],
}

# Some fields (net_quantity especially) often appear on real labels as a
# bare value with no keyword prefix at all - e.g. a block that just says
# "500ml" or "1 kg". Keyword matching alone misses these, so we also give
# a point for matching a field's expected *shape* via regex. This mirrors
# the validators in lm_rules_2011.py but is deliberately kept separate:
# classification (which field is this?) and validation (is it correctly
# formatted?) are different questions, even though they overlap here.
FIELD_SHAPE_PATTERNS: dict[str, str] = {
    "net_quantity": r"\d+(\.\d+)?\s*(g|kg|mg|ml|l|litre|liter|gram|kilogram|pcs|piece|n)\b",
    "mrp": r"(₹|rs\.?|inr)\s*\d+(\.\d{1,2})?",
    "mfg_date": r"\d{1,2}/\d{4}|\d{1,2}/\d{1,2}/\d{2,4}",
}

MIN_SCORE = 1  # a block needs at least 1 keyword/shape hit to be classified


@dataclass
class ClassifiedBlock:
    text: str
    bbox: list
    confidence: float
    engine: str
    field_key: Optional[str] = None
    classification_score: int = 0


def _score_block_for_field(text_lower: str, field_key: str, keywords: list[str]) -> int:
    score = sum(1 for kw in keywords if kw in text_lower)
    shape_pattern = FIELD_SHAPE_PATTERNS.get(field_key)
    if shape_pattern and re.search(shape_pattern, text_lower, re.IGNORECASE):
        score += 1
    return score


def classify_block(block: dict) -> ClassifiedBlock:
    """Classify a single OCR block (as defined by the shared contract)."""
    text = block.get("text", "") or ""
    text_lower = text.lower()

    best_field: Optional[str] = None
    best_score = 0

    for field_key, keywords in FIELD_KEYWORDS.items():
        score = _score_block_for_field(text_lower, field_key, keywords)
        if score > best_score:
            best_score = score
            best_field = field_key

    if best_score < MIN_SCORE:
        best_field = None

    return ClassifiedBlock(
        text=text,
        bbox=block.get("bbox", [0, 0, 0, 0]),
        confidence=block.get("confidence", 0.0),
        engine=block.get("engine", "unknown"),
        field_key=best_field,
        classification_score=best_score,
    )


def classify_blocks(ocr_payload: dict) -> list[ClassifiedBlock]:
    """
    Takes a full contract payload (with 'image_id' and 'blocks') and
    returns a list of ClassifiedBlock. Safe against an empty blocks list
    (per contract note: OCR failure -> blocks = [], never null).
    """
    blocks = ocr_payload.get("blocks", []) or []
    return [classify_block(b) for b in blocks]


def best_block_per_field(classified: list[ClassifiedBlock]) -> dict[str, ClassifiedBlock]:
    """
    If multiple blocks got classified into the same field (e.g. OCR split
    one line into two blocks), keep the one with the highest OCR
    confidence * classification_score as the representative block for
    that field. Returns a dict of field_key -> ClassifiedBlock.
    """
    best: dict[str, ClassifiedBlock] = {}
    for cb in classified:
        if cb.field_key is None:
            continue
        current = best.get(cb.field_key)
        rank = cb.confidence * (cb.classification_score or 1)
        current_rank = (current.confidence * (current.classification_score or 1)) if current else -1
        if current is None or rank > current_rank:
            best[cb.field_key] = cb
    return best

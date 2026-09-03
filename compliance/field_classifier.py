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
    # ASSUMPTION / deviation note: lm_rules_2011.py's Step-3 pass added a
    # new mandatory "commodity_name" field, but without a keyword entry
    # here it could never be classified (permanently MISSING on every
    # label). Added minimal keyword support so the field is actually
    # reachable end-to-end - kept intentionally small, matching the
    # "don't overbuild" instruction for the new field's validator.
    "commodity_name": ["commodity", "product name", "generic name"],
}

# Some fields (net_quantity especially) often appear on real labels as a
# bare value with no keyword prefix at all - e.g. a block that just says
# "500ml" or "1 kg". Keyword matching alone misses these, so we also give
# a point for matching a field's expected *shape* via regex. This mirrors
# the validators in lm_rules_2011.py but is deliberately kept separate:
# classification (which field is this?) and validation (is it correctly
# formatted?) are different questions, even though they overlap here.
FIELD_SHAPE_PATTERNS: dict[str, str] = {
    # NOTE: a bare "n" unit was removed here - it matched too many
    # unrelated digit+letter OCR fragments as false-positive quantities.
    # Count-based quantities now require an explicit word.
    "net_quantity": r"\d+(\.\d+)?\s*(g|kg|mg|ml|l|litre|liter|gram|kilogram|pcs|pieces?|units?)\b",
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


# A block whose second-best field score is within this many points of its
# best field score is ambiguous enough that we keep it as a candidate for
# BOTH fields, rather than silently discarding the second reading. This
# matters because real OCR often produces one block that legitimately
# matches keywords for two different fields (e.g. a block mentioning both
# "Mfg by" and a date), and picking only the top scorer can throw away the
# correct attribution for the other field entirely.
TIE_MARGIN = 1


def classify_block(block: dict) -> list[ClassifiedBlock]:
    """
    Classify a single OCR block (as defined by the shared contract).

    Returns a LIST of ClassifiedBlock, not a single winner: if the block's
    score is tied (within TIE_MARGIN) between its best and second-best
    field, it becomes a candidate for both. Unclassified blocks (score
    below MIN_SCORE for every field) return an empty list rather than a
    single field_key=None entry, since there's nothing for
    best_block_per_field to collect in that case.
    """
    text = block.get("text", "") or ""
    text_lower = text.lower()
    bbox = block.get("bbox", [0, 0, 0, 0])
    confidence = block.get("confidence", 0.0)
    engine = block.get("engine", "unknown")

    # Score every field, keep all of them (not just the max) so we can
    # detect near-ties.
    scores: dict[str, int] = {
        field_key: _score_block_for_field(text_lower, field_key, keywords)
        for field_key, keywords in FIELD_KEYWORDS.items()
    }

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] < MIN_SCORE:
        return []

    best_field, best_score = ranked[0]
    candidates = [best_field]

    if len(ranked) > 1:
        second_field, second_score = ranked[1]
        if second_score >= MIN_SCORE and (best_score - second_score) <= TIE_MARGIN:
            candidates.append(second_field)

    return [
        ClassifiedBlock(
            text=text,
            bbox=bbox,
            confidence=confidence,
            engine=engine,
            field_key=field_key,
            classification_score=scores[field_key],
        )
        for field_key in candidates
    ]


def classify_blocks(ocr_payload: dict) -> list[ClassifiedBlock]:
    """
    Takes a full contract payload (with 'image_id' and 'blocks') and
    returns a FLAT list of ClassifiedBlock. A single source OCR block can
    contribute more than one entry here if it was ambiguous between two
    fields (see classify_block). Safe against an empty blocks list (per
    contract note: OCR failure -> blocks = [], never null). Non-dict
    entries in the blocks list are skipped rather than raising, since a
    single malformed entry from an upstream bug shouldn't crash the whole
    evaluation.
    """
    blocks = ocr_payload.get("blocks", []) or []
    classified: list[ClassifiedBlock] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        classified.extend(classify_block(b))
    return classified


def best_block_per_field(classified: list[ClassifiedBlock]) -> dict[str, list[ClassifiedBlock]]:
    """
    Groups classified blocks by field_key and returns each field's
    candidates as a list, RANKED by (confidence * classification_score)
    descending -- not just the single top scorer. This preserves lower-
    ranked candidates (e.g. a block that failed format validation) so
    rule_engine.py can fall back to them, and lets it detect when two
    candidates disagree on the value (a conflict) instead of one silently
    winning.

    Returns a dict of field_key -> list[ClassifiedBlock], best first.
    """
    grouped: dict[str, list[ClassifiedBlock]] = {}
    for cb in classified:
        if cb.field_key is None:
            continue
        grouped.setdefault(cb.field_key, []).append(cb)

    for field_key, candidates in grouped.items():
        candidates.sort(
            key=lambda cb: cb.confidence * (cb.classification_score or 1),
            reverse=True,
        )
    return grouped

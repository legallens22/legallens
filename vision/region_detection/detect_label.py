"""
Stage 3 of the vision pipeline: label region detection.

SIMPLIFIED FOR V1: full contour-based detection was attempted and
abandoned — busy real-world backgrounds (wood grain, grass) caused
edge-merging that made confident region detection unreliable within
our time budget. Since PaddleOCR and EasyOCR both run their own
internal text-region detection as part of OCR, this stage now only
does a light margin trim (removes obvious frame edges/borders) rather
than trying to out-detect the OCR engines' own detector.

This is a deliberate, documented v1 limitation — not an oversight.
Revisit only if OCR accuracy testing shows background clutter is
actually hurting results.
"""

import numpy as np


def detect_label(cleaned_image: np.ndarray, margin_pct: float = 0.05) -> np.ndarray:
    """
    Args:
        cleaned_image: output of clean_image() — a BGR numpy array.
        margin_pct: fraction of width/height to trim from each edge
            (default 5%) — removes camera frame borders without
            risking cropping into the actual product.

    Returns:
        A lightly-trimmed numpy array. Falls back to the untrimmed
        image if the trim would leave too small a region.
    """
    h, w = cleaned_image.shape[:2]

    trim_x = int(w * margin_pct)
    trim_y = int(h * margin_pct)

    # Safety check — never trim so much that we lose the actual content
    if trim_x * 2 >= w or trim_y * 2 >= h:
        return cleaned_image

    trimmed = cleaned_image[trim_y:h - trim_y, trim_x:w - trim_x]
    return trimmed
    
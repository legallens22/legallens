"""
Stage 4b of the vision pipeline: EasyOCR text extraction.

Used as a multilingual fallback (Hindi/regional scripts) alongside
PaddleOCR, per CONTRACT_NOTES.md decision 5 — ocr_router.py decides
which engine's result to keep per region, this file just runs one
engine and returns its raw output.
"""

import easyocr

# Initialize once at module load — loading model weights per-call
# would be extremely slow.
_easyocr_reader = easyocr.Reader(["en", "hi"], gpu=False)


def run_easyocr(image_path: str):
    """
    Args:
        image_path: path to an image file (cropped/cleaned label).

    Returns:
        Raw EasyOCR result — a list of
        [ [ [x1,y1],[x2,y2],[x3,y3],[x4,y4] ], text, confidence ]
        entries, exactly as EasyOCR's readtext() returns them.
    """
    result = _easyocr_reader.readtext(image_path)
    return result
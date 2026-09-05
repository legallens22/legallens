"""
Stage 4c of the vision pipeline: OCR result merging.

Takes raw output from both engines, converts each to the locked
contract format (CONTRACT_NOTES.md), and merges overlapping regions
by keeping whichever engine had higher confidence — per decision 5.
"""

import cv2
from vision.ocr.paddle_engine import run_paddle_ocr
from vision.ocr.easyocr_engine import run_easyocr


def _paddle_to_contract_blocks(paddle_result):
    """Converts PaddleOCR's native dict output into contract-shaped blocks."""
    blocks = []
    if not paddle_result:
        return blocks

    first = paddle_result[0]
    texts = first.get("rec_texts", [])
    scores = first.get("rec_scores", [])
    boxes = first.get("rec_boxes", [])  # already [x1,y1,x2,y2] per contract note research needed

    for i in range(len(texts)):
        box = boxes[i]
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        blocks.append({
            "text": texts[i],
            "bbox": [x1, y1, x2 - x1, y2 - y1],  # convert to [x, y, w, h]
            "confidence": float(scores[i]),
            "engine": "paddleocr",
        })
    return blocks


def _easyocr_to_contract_blocks(easyocr_result):
    """Converts EasyOCR's native list output into contract-shaped blocks."""
    blocks = []
    for polygon, text, score in easyocr_result:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))
        blocks.append({
            "text": text,
            "bbox": [x1, y1, x2 - x1, y2 - y1],
            "confidence": float(score),
            "engine": "easyocr",
        })
    return blocks


def _boxes_overlap(box_a, box_b, threshold=0.2):
    """
    Returns True if two [x,y,w,h] boxes overlap more than `threshold`
    fraction of the smaller box's area — per decision 5, this is how
    we decide two blocks are "the same physical text."
    """
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)

    if ix2 <= ix1 or iy2 <= iy1:
        return False

    intersection = (ix2 - ix1) * (iy2 - iy1)
    smaller_area = min(aw * ah, bw * bh)

    return smaller_area > 0 and (intersection / smaller_area) > threshold


def run_ocr_pipeline(image_path: str) -> dict:
    """
    Args:
        image_path: path to the label image (post-preprocessing).

    Returns:
        A dict matching shared/ocr_contract.json exactly.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    height, width = img.shape[:2]

    paddle_raw = run_paddle_ocr(image_path)
    easyocr_raw = run_easyocr(image_path)

    paddle_blocks = _paddle_to_contract_blocks(paddle_raw)
    easyocr_blocks = _easyocr_to_contract_blocks(easyocr_raw)

    # --- Merge: for each easyocr block, check if it overlaps a paddle
    # block. If so, keep whichever has higher confidence. If not,
    # keep both — they're different text regions. ---
    merged = list(paddle_blocks)  # start with all paddle blocks

    for eb in easyocr_blocks:
        overlap_found = False
        for i, pb in enumerate(merged):
            if _boxes_overlap(eb["bbox"], pb["bbox"]):
                overlap_found = True
                if eb["confidence"] > pb["confidence"]:
                    merged[i] = eb  # easyocr wins this region
                break
        if not overlap_found:
            merged.append(eb)

    status = "ok" if merged else "no_text_found"

    return {
        "image_id": image_path,
        "image_width": width,
        "image_height": height,
        "status": status,
        "blocks": merged,
    }
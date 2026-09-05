"""
Manual test for run_paddle_ocr() — prints a CLEAN view of the parts
we actually care about (text, boxes, scores), not the full raw dict
which is unreadably noisy (contains font object internals).
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.ocr.paddle_engine import run_paddle_ocr

TEST_IMAGE = os.path.join("sample_data", "sample_labels", "label_clean_01.jpg")

if __name__ == "__main__":
    print(f"Running PaddleOCR on: {TEST_IMAGE}")
    result = run_paddle_ocr(TEST_IMAGE)

    print(f"\ntype(result) = {type(result)}")
    print(f"len(result) = {len(result)}")

    # result is typically a list with one entry per input image
    first = result[0]
    print(f"\ntype(result[0]) = {type(first)}")

    # Try dict-style access first (PaddleOCR 3.x structured result)
    try:
        keys = list(first.keys())
        print(f"Keys available: {keys}")

        texts = first.get("rec_texts", None)
        scores = first.get("rec_scores", None)
        boxes = first.get("rec_boxes", None)

        print(f"\nNumber of text regions found: {len(texts) if texts else 0}")

        if texts:
            print("\n--- First 10 detected text blocks ---")
            for i in range(min(10, len(texts))):
                score = scores[i] if scores is not None else "N/A"
                box = boxes[i] if boxes is not None else "N/A"
                print(f"[{i}] text={texts[i]!r}  score={score}  box={box}")

    except AttributeError as e:
        print(f"Dict-style access failed: {e}")
        print("Falling back to raw repr of result[0]:")
        print(first)
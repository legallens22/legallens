"""
Manual test for run_paddle_ocr().
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.ocr.paddle_engine import run_paddle_ocr

TEST_IMAGE = os.path.join("sample_data", "sample_labels", "label_hindi_01.jpg")

if __name__ == "__main__":
    print(f"Running PaddleOCR on: {TEST_IMAGE}")
    result = run_paddle_ocr(TEST_IMAGE)

    first = result[0]
    texts = first.get("rec_texts", None)
    scores = first.get("rec_scores", None)
    boxes = first.get("rec_boxes", None)

    if boxes is not None:
        print(f"\nboxes shape: {boxes.shape}")
        print(f"First raw box (full): {boxes[0].tolist()}")
        print(f"Second raw box (full): {boxes[1].tolist()}")

    if texts:
        print("\n--- First 5 detected text blocks ---")
        for i in range(min(5, len(texts))):
            score = scores[i] if scores is not None else "N/A"
            box = boxes[i].tolist() if boxes is not None else "N/A"
            print(f"[{i}] text={texts[i]!r}  score={score}  box={box}")
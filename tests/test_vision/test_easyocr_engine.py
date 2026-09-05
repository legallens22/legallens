"""
Manual test for run_easyocr().
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.ocr.easyocr_engine import run_easyocr

TEST_IMAGE = os.path.join("sample_data", "sample_labels", "label_hindi_01.jpg")

if __name__ == "__main__":
    print(f"Running EasyOCR on: {TEST_IMAGE}")
    result = run_easyocr(TEST_IMAGE)

    print(f"\nNumber of text regions found: {len(result)}")
    print("\n--- First 10 detected text blocks ---")
    for i, (box, text, score) in enumerate(result[:10]):
        print(f"[{i}] text={text!r}  score={score:.3f}  box={box}")
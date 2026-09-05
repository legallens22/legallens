"""
Debug script — NOT part of the pipeline.
"""

import cv2
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.preprocessing.clean_image import clean_image
from vision.region_detection.detect_label import find_label_box

INPUT_DIR = os.path.join("sample_data", "sample_labels")
OUTPUT_DIR = os.path.join("sample_data", "debug_contours")

TEST_IMAGES = [
    "label_clean_01.jpg",
    "label_glare_01.jpg",
    "label_angled_01.jpg",
    "label_blurry_01.jpg",
]

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in TEST_IMAGES:
        input_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(input_path):
            continue

        cleaned = clean_image(input_path)
        x, y, w, h, used_fallback = find_label_box(cleaned)

        img_w, img_h = cleaned.shape[1], cleaned.shape[0]
        box_pct = (w * h) / (img_w * img_h) * 100

        status = "FALLBACK" if used_fallback else "DETECTED"
        print(f"{filename}: {status} — box {w}x{h} at ({x},{y}), "
              f"{box_pct:.1f}% of image, image size = {img_w}x{img_h}")

        debug_image = cleaned.copy()
        if not used_fallback:
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 4)

        debug_path = os.path.join(OUTPUT_DIR, f"debug_{filename}")
        cv2.imwrite(debug_path, debug_image)

if __name__ == "__main__":
    run()
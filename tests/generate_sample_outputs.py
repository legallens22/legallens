"""
One-off script: runs the full vision pipeline on all sample labels
and saves real contract JSON for Amey's compliance testing.
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from vision.pipeline import run_vision_pipeline

IMAGES = [
    "label_clean_01.jpg",
    "label_clean_02.jpg",
    "label_clean_03.jpg",
    "label_glare_01.jpg",
    "label_angled_01.jpg",
    "label_blurry_01.jpg",
    "label_hindi_01.jpg",
]

INPUT_DIR = os.path.join("sample_data", "sample_labels")
OUTPUT_DIR = os.path.join("sample_data", "sample_ocr_outputs")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for img in IMAGES:
        path = os.path.join(INPUT_DIR, img)
        if not os.path.exists(path):
            print(f"SKIP: {img} not found")
            continue

        result = run_vision_pipeline(path)
        out_name = f"real_{img.replace('.jpg', '.json')}"
        out_path = os.path.join(OUTPUT_DIR, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"{img}: {len(result['blocks'])} blocks -> {out_path}")
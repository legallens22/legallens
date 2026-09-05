"""
Manual test script for clean_image().
"""

import cv2
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.preprocessing.clean_image import clean_image

INPUT_DIR = os.path.join("sample_data", "sample_labels")
OUTPUT_DIR = os.path.join("sample_data", "cleaned_previews")

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
            print(f"SKIP: {filename} not found at {input_path}")
            continue

        print(f"Processing: {filename}")
        cleaned = clean_image(input_path)

        output_path = os.path.join(OUTPUT_DIR, f"cleaned_{filename}")
        cv2.imwrite(output_path, cleaned)
        print(f"  -> saved to {output_path}")

if __name__ == "__main__":
    run()
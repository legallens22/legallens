"""
Manual test for run_ocr_pipeline() — the merged, contract-shaped output.
"""

import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from vision.ocr.ocr_router import run_ocr_pipeline

TEST_IMAGES = [
    "label_clean_01.jpg",
    "label_hindi_01.jpg",
]

INPUT_DIR = os.path.join("sample_data", "sample_labels")
OUTPUT_DIR = os.path.join("sample_data", "sample_ocr_outputs")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in TEST_IMAGES:
        input_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(input_path):
            print(f"SKIP: {filename} not found")
            continue

        print(f"\nRunning merged OCR pipeline on: {filename}")
        contract_json = run_ocr_pipeline(input_path)

        print(f"  status: {contract_json['status']}")
        print(f"  total blocks: {len(contract_json['blocks'])}")
        print(f"  image size: {contract_json['image_width']}x{contract_json['image_height']}")

        print("\n  --- First 5 merged blocks ---")
        for b in contract_json["blocks"][:5]:
            print(f"  [{b['engine']}] text={b['text']!r}  "
                  f"conf={b['confidence']:.3f}  bbox={b['bbox']}")

        # Save the real contract JSON for Amey to use
        out_name = filename.replace(".jpg", ".json")
        out_path = os.path.join(OUTPUT_DIR, f"real_{out_name}")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(contract_json, f, ensure_ascii=False, indent=2)
        print(f"\n  -> saved to {out_path}")
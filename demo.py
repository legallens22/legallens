"""
Quick manual demo - run this to see the compliance pipeline work end to end
against the fake sample OCR JSONs, with no server/API needed yet.

Usage:
    python demo.py sample_data/sample_ocr_outputs/label_001.json
    python demo.py sample_data/sample_ocr_outputs/label_002.json
"""

import json
import sys

from compliance.report_generator import generate_report


def main():
    if len(sys.argv) != 2:
        print("Usage: python demo.py <path_to_ocr_json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        ocr_payload = json.load(f)

    image_id = ocr_payload.get("image_id", "unknown")
    report = generate_report(image_id, ocr_payload)

    print(json.dumps(report, indent=2))
    print()
    print(f"Overall verdict for '{image_id}': {report['overall_verdict']}")


if __name__ == "__main__":
    main()

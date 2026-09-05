"""
Stage: full vision pipeline.

Chains preprocessing -> region detection -> merged OCR into one
function. This is what api/routes/scan.py will call.
"""

from vision.preprocessing.clean_image import clean_image
from vision.region_detection.detect_label import detect_label
from vision.ocr.ocr_router import run_ocr_pipeline
import cv2
import os


def run_vision_pipeline(image_path: str) -> dict:
    """
    Args:
        image_path: path to a raw label photo.

    Returns:
        A dict matching shared/ocr_contract.json exactly.
    """
    cleaned = clean_image(image_path)
    cropped = detect_label(cleaned)

    # OCR functions expect a file path, not an in-memory array, so we
    # save the processed image to a temp file before running OCR on it.
    temp_dir = "sample_data/_temp_pipeline"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, "processed.jpg")
    cv2.imwrite(temp_path, cropped)

    contract_json = run_ocr_pipeline(temp_path)

    # Restore the original image_id (the temp path isn't meaningful
    # to whoever consumes this contract JSON).
    contract_json["image_id"] = os.path.basename(image_path)

    return contract_json
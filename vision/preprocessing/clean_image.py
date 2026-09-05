"""
Stage 2 of the vision pipeline: image preprocessing.

Takes a raw label photo and returns a cleaned version, fixing common
real-world capture problems (glare, uneven lighting, slight rotation)
before region detection and OCR run on it.
"""

import cv2
import numpy as np


def clean_image(image_path: str) -> np.ndarray:
    """
    Args:
        image_path: path to a raw label photo (jpg/png).

    Returns:
        A cleaned image as a numpy array (BGR, OpenCV's default format),
        ready to hand to region_detection/detect_label.py.
    """
    # --- Step 1: Load the image ---
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image at: {image_path}")

    # --- Step 2: Convert to LAB color space for CLAHE ---
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # --- Step 3: Apply CLAHE to the lightness channel ---
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_channel)

    # --- Step 4: Merge back and convert to BGR ---
    lab_clahe = cv2.merge((l_clahe, a_channel, b_channel))
    contrast_fixed = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)

    # --- Step 5: Denoise ---
    denoised = cv2.fastNlMeansDenoisingColored(
        contrast_fixed, None, h=10, hColor=10,
        templateWindowSize=7, searchWindowSize=21
    )

    # --- Step 6: Deskew ---
    # Not implemented yet — deliberately a pass-through for now.
    cleaned = denoised

    return cleaned
"""
Stage 3 of the vision pipeline: label region detection.
"""

import cv2
import numpy as np


def detect_label(cleaned_image: np.ndarray) -> np.ndarray:
    """
    Args:
        cleaned_image: output of clean_image() — a BGR numpy array.

    Returns:
        A cropped numpy array containing just the detected label
        region, or the original image if no confident region is found.
    """
    gray = cv2.cvtColor(cleaned_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    # --- Dilation: merge nearby edge fragments into solid blobs ---
    # A label has dense text/lines that are individually small edges;
    # dilating connects them into one blob. A stray background crack
    # (e.g. wood grain) stays thin and isolated, so it won't compete
    # with the label's merged blob after this step.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    dilated = cv2.dilate(edges, kernel, iterations=2)

    contours, _ = cv2.findContours(
        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return cleaned_image

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)

    image_area = cleaned_image.shape[0] * cleaned_image.shape[1]
    box_area = w * h

    # Reject boxes that are too small (noise) OR suspiciously thin
    # (aspect ratio check) — a wood-grain crack produces a very wide,
    # very short box; a real label is roughly proportioned.
    aspect_ratio = w / h if h > 0 else 0
    too_small = box_area < 0.05 * image_area
    too_thin = aspect_ratio > 8 or aspect_ratio < 0.125

    if too_small or too_thin:
        return cleaned_image

    cropped = cleaned_image[y:y+h, x:x+w]
    return cropped
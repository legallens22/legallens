"""
Stage 4a of the vision pipeline: PaddleOCR text extraction.
"""

import os

# Must be set BEFORE importing paddleocr — disables oneDNN CPU
# acceleration, which has a known compatibility bug with PaddlePaddle
# 3.x's PIR executor on Windows (NotImplementedError on
# ConvertPirAttribute2RuntimeAttribute). We lose some CPU speed but
# gain the ability to actually run.
os.environ["FLAGS_use_mkldnn"] = "false"

from paddleocr import PaddleOCR

_paddle_engine = PaddleOCR(
    use_angle_cls=True,
    lang="en",
    enable_mkldnn=False,
)


def run_paddle_ocr(image_path: str):
    """
    Args:
        image_path: path to an image file (cropped/cleaned label).

    Returns:
        Raw PaddleOCR result.
    """
    result = _paddle_engine.predict(image_path)
    return result
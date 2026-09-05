# OCR Contract Decisions — LOCKED, do not change without both people agreeing

1. CONFIDENCE FORMAT
   Confidence is always a float between 0 and 1 (not 0-100).
   Both PaddleOCR and EasyOCR return values in this range natively,
   so ocr_router.py should NOT need to convert anything — just pass through.

2. BBOX FORMAT
   bbox is always [x, y, width, height] — top-left corner + width/height,
   in pixel coordinates of the ORIGINAL (not cropped) image.
   NOTE: Both PaddleOCR and EasyOCR return 4-point polygons natively —
   ocr_router.py is responsible for converting polygon -> [x, y, w, h]
   before output. This conversion never leaks into compliance/.

3. NO TEXT FOUND
   If OCR finds nothing usable on an image:
     "status": "no_text_found"
     "blocks": []
   compliance/ must handle an empty blocks array without crashing —
   this should route straight to "needs manual review", not a silent fail.

4. LOW-CONFIDENCE THRESHOLD
   Any block with confidence < 0.70 is NOT dropped or hidden by vision/ —
   it's still included in blocks[], full confidence value shown.
   Deciding what to DO with a low-confidence block (flag it? ignore it?)
   is compliance/'s job, not vision/'s. vision/ never filters, only reports.

5. MULTIPLE ENGINES ON ONE BLOCK
   If both PaddleOCR and EasyOCR return a result for roughly the same
   region, ocr_router.py picks ONE (higher confidence wins) rather than
   emitting duplicate blocks. compliance/ should never see two blocks
   for the same physical text.

6. IMAGE DIMENSIONS
   image_width / image_height are always included, in pixels, matching
   the ORIGINAL uploaded image (not any resized/preprocessed version) —
   needed later if the dashboard draws bounding boxes back onto the photo.

7. FIELD NAMES ARE FINAL
   image_id, image_width, image_height, status, blocks, text, bbox,
   confidence, engine — these exact key names, this exact casing.
   Renaming any of these requires both people's sign-off, logged as a
   new numbered decision below.

9. KNOWN LIMITATION — CROSS-ENGINE MERGE ON MISALIGNED BOXES
   When PaddleOCR and EasyOCR detect the same physical text region but
   with non-overlapping bounding boxes (common on Hindi/Devanagari
   script, where PaddleOCR's English-trained detector sometimes
   misreads it as garbled text with a different box location),
   ocr_router.py's overlap-based merge does not catch this — both
   readings survive independently in the output blocks[] array.
   This means the contract can contain a low-value garbled PaddleOCR
   reading alongside a correct EasyOCR reading for the same text,
   uncorrected. All confidence scores remain visible in the output,
   so a downstream consumer (compliance layer or human review) can
   still identify the more trustworthy reading. Not fixed for v1 —
   flagged as a real, tested limitation rather than an unknown gap.

Last updated: [1-09-2026] — by bhavesh,amey
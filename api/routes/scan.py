
"""
api/routes/scan.py
 
Wires the full LegalLens compliance pipeline:
  upload -> vision.pipeline.run_vision_pipeline -> compliance.report_generator.generate_report
 
CONFIRMED INTERFACE:
    vision.pipeline.run_vision_pipeline(image_path: str) -> dict
        # Returns a dict matching shared/ocr_contract.json:
        # {
        #   "image_id": str, "image_width": int, "image_height": int, "status": str,
        #   "blocks": [{"text": str, "bbox": [x,y,w,h], "confidence": float, "engine": str}, ...]
        # }
        # NOTE: takes a file PATH, not bytes — writes internally to a temp file.
        # scan.py must save the upload to disk first.
 
    compliance.report_generator.generate_report(image_id: str, ocr_payload: dict) -> dict
        # Runs classification + rule evaluation + report building in ONE call.
        # field_classifier and rule_engine are called internally — scan.py
        # does NOT call them directly.
"""
 
import os
import uuid
import logging
from dataclasses import asdict, is_dataclass
 
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
 
from vision.pipeline import run_vision_pipeline
from compliance.report_generator import generate_report
 
logger = logging.getLogger("legallens.scan")
 
router = APIRouter()
 
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE_MB = 10
UPLOAD_TEMP_DIR = "sample_data/_temp_pipeline"
 
 
def _validate_upload(file: UploadFile, content: bytes) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f}MB). Max {MAX_FILE_SIZE_MB}MB.",
        )
 
 
def _save_upload_to_temp(content: bytes, original_filename: str) -> str:
    os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"upload_{uuid.uuid4().hex}{ext}")
    with open(temp_path, "wb") as f:
        f.write(content)
    return temp_path
 
 
def _make_json_safe(obj):
    """Recursively convert any dataclass instances (e.g. leftover
    ClassifiedBlock/FieldResult that end up in a debug payload) into
    plain dicts so JSONResponse doesn't choke. report_generator already
    returns plain dicts/strings for the main report, but ocr_contract
    passed straight into debug output is already JSON-safe too — this
    is a safety net, not the primary path."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return _make_json_safe(asdict(obj))
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj
 
 
def run_pipeline(image_path: str, image_id: str, *, debug: bool = False) -> dict:
    """
    Runs the full pipeline starting from a saved file path and returns
    the final response payload. Raises RuntimeError on any stage failure.
    """
    # 1. Vision/OCR — clean_image -> detect_label -> run_ocr_pipeline
    try:
        ocr_contract = run_vision_pipeline(image_path)
    except Exception as e:
        logger.exception("Vision pipeline failed")
        raise RuntimeError(f"Vision pipeline failed: {e}") from e
 
    if not ocr_contract or ocr_contract.get("status") != "ok" or not ocr_contract.get("blocks"):
        raise RuntimeError(
            f"Vision pipeline returned no usable blocks "
            f"(status={ocr_contract.get('status') if ocr_contract else 'None'})"
        )
 
    # 2. Classification + rule evaluation + report — all done internally
    #    by generate_report(). Do NOT call field_classifier or rule_engine
    #    directly here; they're wired together inside report_generator.py.
    try:
        report = generate_report(image_id, ocr_contract)
    except Exception as e:
        logger.exception("Report generation failed")
        raise RuntimeError(f"Report generation failed: {e}") from e
 
    response = {"report": report}
 
    if debug:
        response["debug"] = {"ocr_contract": _make_json_safe(ocr_contract)}
 
    return response
 
 
@router.post("/api/scan")
async def scan_document(file: UploadFile = File(...), debug: bool = False):
    """
    Accepts a label/document image or PDF, runs it through the full
    compliance pipeline, and returns the generated report.
    """
    content = await file.read()
    _validate_upload(file, content)
 
    temp_path = _save_upload_to_temp(content, file.filename or "upload.jpg")
    image_id = os.path.splitext(file.filename or "upload")[0]
 
    try:
        result = run_pipeline(temp_path, image_id, debug=debug)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        # clean up temp upload regardless of success/failure
        try:
            os.remove(temp_path)
        except OSError:
            pass
 
    return JSONResponse(content=_make_json_safe(result))
 
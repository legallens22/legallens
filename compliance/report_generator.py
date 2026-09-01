"""
report_generator.py

Input:  the list of FieldResult from rule_engine.evaluate_label(), plus
        the original image_id.
Output: a single JSON-serializable dict - this is what api/routes/scan.py
        will return to the frontend/dashboard.

Keeping this separate from rule_engine.py means the *decision* logic and
the *presentation* logic don't get tangled - useful when the dashboard
team (or future you) wants to change the report format without touching
how pass/fail is decided.
"""

from datetime import datetime, timezone

from compliance.rule_engine import FieldResult, Verdict, evaluate_label, overall_verdict


def generate_report(image_id: str, ocr_payload: dict) -> dict:
    """
    Full convenience entrypoint: run evaluation + build the final report
    in one call. This is what api/routes/scan.py will call directly.
    """
    field_results = evaluate_label(ocr_payload)
    return build_report(image_id, field_results)


def build_report(image_id: str, field_results: list[FieldResult]) -> dict:
    overall = overall_verdict(field_results)

    fields_report = []
    for r in field_results:
        fields_report.append({
            "field_key": r.field_key,
            "display_name": r.display_name,
            "verdict": r.verdict.value,
            "matched_text": r.matched_text,
            "ocr_confidence": r.confidence,
            "reason": r.reason,
        })

    failed_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.FAIL.value]
    missing_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.MISSING.value]
    review_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.NEEDS_MANUAL_REVIEW.value]

    return {
        "image_id": image_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_verdict": overall.value,
        "summary": {
            "total_fields_checked": len(field_results),
            "passed": sum(1 for f in fields_report if f["verdict"] == Verdict.PASS.value),
            "failed": len(failed_fields),
            "missing": len(missing_fields),
            "needs_manual_review": len(review_fields),
        },
        "failed_field_names": failed_fields,
        "missing_field_names": missing_fields,
        "needs_review_field_names": review_fields,
        "fields": fields_report,
    }

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
from compliance.rules.lm_rules_2011 import get_rule


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
        rule = get_rule(r.field_key)
        fields_report.append({
            "field_key": r.field_key,
            "display_name": r.display_name,
            "verdict": r.verdict.value,
            "matched_text": r.matched_text,
            "ocr_confidence": r.confidence,
            "reason": r.reason,
            "bbox": r.bbox,
            "classification_score": r.classification_score,
            "legal_reference": rule.legal_reference if rule else None,
        })

    failed_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.FAIL.value]
    missing_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.MISSING.value]
    review_fields = [f["display_name"] for f in fields_report if f["verdict"] == Verdict.NEEDS_MANUAL_REVIEW.value]
    undetermined_fields = [
        f["display_name"] for f in fields_report if f["verdict"] == Verdict.UNABLE_TO_DETERMINE.value
    ]

    top_level_message = None
    if overall == Verdict.UNABLE_TO_DETERMINE:
        # All fields share the same scan-quality reason in this case
        # (see rule_engine._scan_quality_reason), so surface it once at
        # the top level instead of only inside each per-field entry.
        top_level_message = field_results[0].reason if field_results else None

    return {
        "image_id": image_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_verdict": overall.value,
        # Populated only when overall_verdict is UNABLE_TO_DETERMINE -
        # explicitly distinct from a FAIL summary, since it means the
        # scan couldn't be evaluated at all rather than that the label
        # failed compliance checks.
        "scan_issue_message": top_level_message,
        "summary": {
            "total_fields_checked": len(field_results),
            "passed": sum(1 for f in fields_report if f["verdict"] == Verdict.PASS.value),
            "failed": len(failed_fields),
            "missing": len(missing_fields),
            "needs_manual_review": len(review_fields),
            "unable_to_determine": len(undetermined_fields),
        },
        "failed_field_names": failed_fields,
        "missing_field_names": missing_fields,
        "needs_review_field_names": review_fields,
        "undetermined_field_names": undetermined_fields,
        "fields": fields_report,
    }

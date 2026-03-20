"""Build human review queue structures from judge outcomes."""
import json
import uuid
from pathlib import Path


def _load_mapping_results(mapping_results_dir) -> dict[str, dict]:
    mapping_dir = Path(mapping_results_dir)
    mapping_results: dict[str, dict] = {}

    for result_file in sorted(mapping_dir.glob("*.json")):
        with open(result_file, "r") as f:
            payload = json.load(f)
        control_id = payload.get("internal_control_id") or result_file.stem
        mapping_results[control_id] = payload

    return mapping_results


def _build_internal_index(internal_controls_db) -> dict[str, dict]:
    if isinstance(internal_controls_db, dict):
        return internal_controls_db

    index: dict[str, dict] = {}
    for control in internal_controls_db:
        control_id = control.get("CCF ID") or control.get("internal_control_id") or control.get("id")
        if control_id:
            index[control_id] = control
    return index


def _build_external_index(external_controls_db) -> dict[str, dict]:
    index: dict[str, dict] = {}

    if isinstance(external_controls_db, list):
        for control in external_controls_db:
            control_id = control.get("safeguard_id") or control.get("external_id") or control.get("id")
            if control_id:
                index[control_id] = control
        return index

    controls = external_controls_db.get("controls", []) if isinstance(external_controls_db, dict) else []
    for control in controls:
        for safeguard in control.get("safeguards", []):
            safeguard_id = safeguard.get("safeguard_id")
            if not safeguard_id:
                continue
            merged = dict(safeguard)
            merged["framework"] = external_controls_db.get("framework")
            merged["control_id"] = control.get("control_id")
            merged["control_title"] = control.get("control_title")
            merged["control_description"] = control.get("control_description")
            index[safeguard_id] = merged

    return index


def build_review_queue(judge_results, internal_controls_db, external_controls_db, mapping_results_dir) -> dict:
    """Build accepted, review, and quarantine queues from judge outputs."""
    mapping_results = _load_mapping_results(mapping_results_dir)
    internal_index = _build_internal_index(internal_controls_db)
    external_index = _build_external_index(external_controls_db)

    accepted_results: list[dict] = []
    review_queue: list[dict] = []
    quarantine_queue: list[dict] = []

    for judge_result in judge_results:
        control_id = judge_result.get("internal_control_id")
        verdict = judge_result.get("overall_verdict")
        false_negatives = judge_result.get("false_negatives") or []

        mapping_payload = mapping_results.get(control_id, {
            "internal_control_id": control_id,
            "mappings": [],
        })

        if verdict == "APPROVED" and not false_negatives:
            accepted_results.append(mapping_payload)
            continue

        per_mapping_verdicts = {
            item.get("external_id"): item
            for item in judge_result.get("per_mapping_verdicts", [])
            if item.get("external_id")
        }

        mappings_for_review = []
        for mapping in mapping_payload.get("mappings", []):
            external_id = mapping.get("safeguard_id") or mapping.get("external_id") or mapping.get("id")
            judge_mapping = per_mapping_verdicts.get(external_id, {})
            external_control = external_index.get(external_id, {
                "safeguard_id": external_id,
            })

            mappings_for_review.append({
                "external_control": external_control,
                "mapping_type": mapping.get("mapping") or mapping.get("mapping_type"),
                "mapper_rationale": mapping.get("reason") or mapping.get("mapper_rationale"),
                "judge_verdict": judge_mapping.get("verdict"),
                "judge_rationale_rating": judge_mapping.get("rationale_rating"),
                "judge_rule_violations": judge_mapping.get("rule_violations", []),
                "judge_note": judge_mapping.get("judge_note"),
                "human_decision": None,
                "human_note": None,
            })

        flagged_false_negatives = []
        for item in false_negatives:
            external_id = item.get("external_id")
            external_control = external_index.get(external_id, {
                "external_id": external_id,
                "external_title": item.get("external_title"),
            })
            flagged_false_negatives.append({
                "external_control": external_control,
                "judge_reason": item.get("reason_should_be_included"),
                "human_decision": None,
                "human_note": None,
            })

        quarantine_reason = judge_result.get("quarantine_reason")
        recovery_hint = judge_result.get("recovery_hint")
        quarantine_banner = None
        if verdict == "QUARANTINED":
            quarantine_banner = f"{quarantine_reason} | {recovery_hint}"

        review_card = {
            "review_id": str(uuid.uuid4()),
            "status_tag": "QUARANTINED" if verdict == "QUARANTINED" else "WARNING",
            "quarantine_banner": quarantine_banner,
            "judge_overall_summary": judge_result.get("overall_summary"),
            "judge_confidence": judge_result.get("overall_confidence"),
            "internal_control": internal_index.get(control_id, {"CCF ID": control_id}),
            "mappings_for_review": mappings_for_review,
            "flagged_false_negatives": flagged_false_negatives,
            "review_completed": False,
            "reviewed_by": None,
            "reviewed_at": None,
            "quarantine_reason": quarantine_reason,
            "recovery_hint": recovery_hint,
        }

        if verdict == "QUARANTINED":
            quarantine_queue.append(review_card)
        else:
            review_queue.append(review_card)

    return {
        "accepted_results": accepted_results,
        "review_queue": review_queue,
        "quarantine_queue": quarantine_queue,
        "summary": {
            "total_controls": len(judge_results),
            "auto_approved": len(accepted_results),
            "review_required": len(review_queue),
            "quarantined": len(quarantine_queue),
        },
    }

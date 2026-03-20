"""Build final outputs and audit trail from completed human review decisions."""
import json
from pathlib import Path

from src.review.queue_writer import load_queue


def _build_audit_trail(
    *,
    auto_approved: bool,
    judge_verdict: str | None,
    judge_confidence: float | None,
    human_decision: str | None,
    human_note: str | None,
    reviewed_by: str | None,
    reviewed_at: str | None,
    was_quarantined: bool,
    quarantine_reason: str | None,
) -> dict:
    return {
        "auto_approved": auto_approved,
        "judge_verdict": judge_verdict,
        "judge_confidence": judge_confidence,
        "human_decision": human_decision,
        "human_note": human_note,
        "reviewed_by": reviewed_by,
        "reviewed_at": reviewed_at,
        "was_quarantined": was_quarantined,
        "quarantine_reason": quarantine_reason,
    }


def _convert_accepted_results(accepted_results: list[dict], final_output: list[dict], audit_trail: list[dict]) -> int:
    auto_approved_count = 0

    for result in accepted_results:
        internal_control_id = result.get("internal_control_id")
        internal_control_name = result.get("internal_control_name")
        mappings = result.get("mappings") or []

        for mapping in mappings:
            record = {
                "internal_control_id": internal_control_id,
                "internal_control_name": internal_control_name,
                "external_id": mapping.get("safeguard_id") or mapping.get("external_id") or mapping.get("id"),
                "mapping_type": mapping.get("mapping") or mapping.get("mapping_type"),
                "mapper_rationale": mapping.get("reason") or mapping.get("mapper_rationale"),
                "audit_trail": _build_audit_trail(
                    auto_approved=True,
                    judge_verdict="APPROVED",
                    judge_confidence=1.0,
                    human_decision=None,
                    human_note=None,
                    reviewed_by=None,
                    reviewed_at=None,
                    was_quarantined=False,
                    quarantine_reason=None,
                ),
            }
            final_output.append(record)
            audit_trail.append(record)
            auto_approved_count += 1

    return auto_approved_count


def _process_review_queue_items(
    queue_items: list[dict],
    *,
    was_quarantined: bool,
    final_output: list[dict],
    rejected_results: list[dict],
    pending_results: list[dict],
    audit_trail: list[dict],
) -> tuple[int, int, int]:
    human_approved = 0
    human_rejected = 0
    false_negatives_added = 0

    for card in queue_items:
        if not card.get("review_completed"):
            continue

        internal_control = card.get("internal_control", {})
        internal_control_id = internal_control.get("CCF ID") or internal_control.get("internal_control_id") or internal_control.get("id")
        reviewed_by = card.get("reviewed_by")
        reviewed_at = card.get("reviewed_at")
        quarantine_reason = card.get("quarantine_reason")
        judge_confidence = card.get("judge_confidence")

        for mapping in card.get("mappings_for_review", []):
            external_control = mapping.get("external_control", {})
            external_id = (
                external_control.get("safeguard_id")
                or external_control.get("external_id")
                or external_control.get("id")
            )
            decision = mapping.get("human_decision")

            record = {
                "internal_control_id": internal_control_id,
                "internal_control": internal_control,
                "external_control": external_control,
                "external_id": external_id,
                "mapping_type": mapping.get("mapping_type"),
                "mapper_rationale": mapping.get("mapper_rationale"),
                "audit_trail": _build_audit_trail(
                    auto_approved=False,
                    judge_verdict=mapping.get("judge_verdict"),
                    judge_confidence=judge_confidence,
                    human_decision=decision,
                    human_note=mapping.get("human_note"),
                    reviewed_by=reviewed_by,
                    reviewed_at=reviewed_at,
                    was_quarantined=was_quarantined,
                    quarantine_reason=quarantine_reason,
                ),
            }

            if decision == "APPROVE":
                final_output.append(record)
                human_approved += 1
            elif decision == "REJECT":
                rejected_results.append(record)
                human_rejected += 1
            else:
                pending_results.append(record)

            audit_trail.append(record)

        for flagged_false_negative in card.get("flagged_false_negatives", []):
            external_control = flagged_false_negative.get("external_control", {})
            decision = flagged_false_negative.get("human_decision")

            record = {
                "internal_control_id": internal_control_id,
                "internal_control": internal_control,
                "external_control": external_control,
                "mapping_type": "ADDED_FALSE_NEGATIVE",
                "mapper_rationale": flagged_false_negative.get("judge_reason"),
                "audit_trail": _build_audit_trail(
                    auto_approved=False,
                    judge_verdict="WARN",
                    judge_confidence=judge_confidence,
                    human_decision=decision,
                    human_note=flagged_false_negative.get("human_note"),
                    reviewed_by=reviewed_by,
                    reviewed_at=reviewed_at,
                    was_quarantined=was_quarantined,
                    quarantine_reason=quarantine_reason,
                ),
            }

            if decision == "ADD_TO_MAPPING":
                final_output.append(record)
                false_negatives_added += 1
            elif decision is None:
                pending_results.append(record)

            audit_trail.append(record)

    return human_approved, human_rejected, false_negatives_added


def build_final_output(queue_dir: str) -> dict:
    """Build final, rejected, pending outputs from completed review queues."""
    queue_data = load_queue(queue_dir)

    final_output: list[dict] = []
    rejected_results: list[dict] = []
    pending_results: list[dict] = []
    audit_trail: list[dict] = []

    auto_approved = _convert_accepted_results(queue_data.get("accepted_results", []), final_output, audit_trail)

    review_queue = queue_data.get("review_queue", [])
    review_human_approved, review_human_rejected, review_false_negative_additions = _process_review_queue_items(
        review_queue,
        was_quarantined=False,
        final_output=final_output,
        rejected_results=rejected_results,
        pending_results=pending_results,
        audit_trail=audit_trail,
    )

    quarantine_queue = queue_data.get("quarantine_queue", [])
    quarantine_human_approved, quarantine_human_rejected, quarantine_false_negative_additions = _process_review_queue_items(
        quarantine_queue,
        was_quarantined=True,
        final_output=final_output,
        rejected_results=rejected_results,
        pending_results=pending_results,
        audit_trail=audit_trail,
    )

    human_approved = review_human_approved + quarantine_human_approved
    human_rejected = review_human_rejected + quarantine_human_rejected
    false_negatives_added = review_false_negative_additions + quarantine_false_negative_additions

    internal_ids = set()
    for record in final_output + rejected_results + pending_results:
        if record.get("internal_control_id"):
            internal_ids.add(record.get("internal_control_id"))

    return {
        "final_output": final_output,
        "rejected_results": rejected_results,
        "pending_results": pending_results,
        "audit_trail": audit_trail,
        "statistics": {
            "total_internal_controls": len(internal_ids),
            "total_mappings_in_output": len(final_output),
            "auto_approved": auto_approved,
            "human_approved": human_approved,
            "human_rejected": human_rejected,
            "false_negatives_added": false_negatives_added,
            "pending": len(pending_results),
        },
    }


def write_final_output(final_output: dict, output_dir: str) -> None:
    """Write final output bundles to disk."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "final_output.json", "w") as f:
        json.dump(final_output.get("final_output", []), f, indent=2)

    with open(out_dir / "rejected_results.json", "w") as f:
        json.dump(final_output.get("rejected_results", []), f, indent=2)

    with open(out_dir / "audit_trail.json", "w") as f:
        json.dump(final_output.get("audit_trail", []), f, indent=2)

    with open(out_dir / "statistics.json", "w") as f:
        json.dump(final_output.get("statistics", {}), f, indent=2)

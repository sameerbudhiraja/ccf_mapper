"""Interactive human-in-the-loop CLI for mapping review."""
from datetime import datetime, timezone

from src.review.queue_writer import load_queue, save_queue


class _SessionExit(Exception):
    """Raised when reviewer requests early exit."""


def _safe_get(control: dict, *keys):
    for key in keys:
        if key in control:
            return control[key]
    return None


def _print_internal_control(internal_control: dict) -> None:
    print("INTERNAL CONTROL (full details):")
    for key, value in internal_control.items():
        print(f"  {key}: {value}")


def _prompt_choice(prompt: str, allowed: set[str]) -> str:
    while True:
        value = input(prompt).strip()
        if value.lower() == "exit":
            raise _SessionExit()

        upper_value = value.upper()
        if upper_value in allowed:
            return upper_value

        print(f"Invalid input. Expected one of: {', '.join(sorted(allowed))}")


def _prompt_optional_note() -> str | None:
    note = input("Add a note? (press Enter to skip): ").strip()
    if note.lower() == "exit":
        raise _SessionExit()
    return note or None


def _render_mapping(mapping: dict, index: int, total: int) -> None:
    external_control = mapping.get("external_control", {})
    external_id = _safe_get(external_control, "safeguard_id", "external_id", "id")
    external_title = _safe_get(external_control, "safeguard_title", "external_title", "title")
    external_description = _safe_get(external_control, "safeguard_description", "external_description", "description")

    print("────────────────────────────")
    print(f"Mapping [{index} of {total}]")
    print(f"External Control ID    : {external_id}")
    print(f"External Control Title : {external_title}")
    print(f"External Description   : {external_description}")
    print(f"Mapping Type           : {mapping.get('mapping_type')}")
    print(f"Mapper Rationale       : {mapping.get('mapper_rationale')}")
    print(f"Judge Verdict          : {mapping.get('judge_verdict')}")
    print(f"Rationale Rating       : {mapping.get('judge_rationale_rating')}")

    rule_violations = mapping.get("judge_rule_violations") or []
    if rule_violations:
        print(f"Rule Violations        : {rule_violations}")
    else:
        print("Rule Violations        : None")

    print(f"Judge Note             : {mapping.get('judge_note')}")
    print("────────────────────────────")


def _render_false_negative(flagged_item: dict) -> None:
    external_control = flagged_item.get("external_control", {})
    external_id = _safe_get(external_control, "safeguard_id", "external_id", "id")
    external_title = _safe_get(external_control, "safeguard_title", "external_title", "title")
    external_description = _safe_get(external_control, "safeguard_description", "external_description", "description")

    print("────────────────────────────")
    print("⚠ Flagged False Negative")
    print(f"External Control ID    : {external_id}")
    print(f"External Control Title : {external_title}")
    print(f"Full Description       : {external_description}")
    print(f"Judge Reason           : {flagged_item.get('judge_reason')}")
    print("────────────────────────────")


def _process_quarantine_queue(queue_data: dict, reviewer_name: str, queue_dir: str) -> None:
    quarantine_queue = queue_data.get("quarantine_queue", [])

    for card in quarantine_queue:
        if card.get("review_completed"):
            continue

        internal_control = card.get("internal_control", {})
        control_id = _safe_get(internal_control, "CCF ID", "internal_control_id", "id")

        print("─────────────────────────────────────────")
        print(f"[QUARANTINED] — Control {control_id}")
        print(f"Judge confidence : {card.get('judge_confidence')}")
        print("─────────────────────────────────────────")
        print(f"⛔ QUARANTINE REASON : {str(card.get('quarantine_reason')).upper()}")
        print(f"💡 RECOVERY HINT    : {str(card.get('recovery_hint')).upper()}")

        _print_internal_control(internal_control)

        print("Judge Summary:")
        print(card.get("judge_overall_summary"))

        mappings = card.get("mappings_for_review", [])
        for index, mapping in enumerate(mappings, 1):
            _render_mapping(mapping, index, len(mappings))
            print("Decision for this mapping:")
            print("  [A] Approve   [R] Reject   [S] Skip (decide later)")
            decision = _prompt_choice("> ", {"A", "R", "S"})
            mapping["human_decision"] = {"A": "APPROVE", "R": "REJECT", "S": None}[decision]
            mapping["human_note"] = _prompt_optional_note()
            save_queue(queue_data, queue_dir)

        for flagged_item in card.get("flagged_false_negatives", []):
            _render_false_negative(flagged_item)
            print("Decision:")
            print("  [A] Add to mapping   [D] Dismiss   [S] Skip")
            decision = _prompt_choice("> ", {"A", "D", "S"})
            flagged_item["human_decision"] = {"A": "ADD_TO_MAPPING", "D": "DISMISS", "S": None}[decision]
            flagged_item["human_note"] = _prompt_optional_note()
            save_queue(queue_data, queue_dir)

        mark_complete = _prompt_choice("Mark this control review as complete? [Y/N]: ", {"Y", "N"})
        if mark_complete == "Y":
            card["review_completed"] = True
            card["reviewed_by"] = reviewer_name
            card["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(queue_data, queue_dir)


def _process_review_queue(queue_data: dict, reviewer_name: str, queue_dir: str) -> None:
    review_queue = queue_data.get("review_queue", [])

    for card in review_queue:
        if card.get("review_completed"):
            continue

        internal_control = card.get("internal_control", {})
        control_id = _safe_get(internal_control, "CCF ID", "internal_control_id", "id")

        print("─────────────────────────────────────────")
        print(f"[WARNING] — Control {control_id}")
        print(f"Judge confidence : {card.get('judge_confidence')}")
        print("─────────────────────────────────────────")

        _print_internal_control(internal_control)

        print("Judge Summary:")
        print(card.get("judge_overall_summary"))

        mappings = card.get("mappings_for_review", [])
        for index, mapping in enumerate(mappings, 1):
            _render_mapping(mapping, index, len(mappings))
            print("Decision for this mapping:")
            print("  [A] Approve   [R] Reject   [S] Skip (decide later)")
            decision = _prompt_choice("> ", {"A", "R", "S"})
            mapping["human_decision"] = {"A": "APPROVE", "R": "REJECT", "S": None}[decision]
            mapping["human_note"] = _prompt_optional_note()
            save_queue(queue_data, queue_dir)

        for flagged_item in card.get("flagged_false_negatives", []):
            _render_false_negative(flagged_item)
            print("Decision:")
            print("  [A] Add to mapping   [D] Dismiss   [S] Skip")
            decision = _prompt_choice("> ", {"A", "D", "S"})
            flagged_item["human_decision"] = {"A": "ADD_TO_MAPPING", "D": "DISMISS", "S": None}[decision]
            flagged_item["human_note"] = _prompt_optional_note()
            save_queue(queue_data, queue_dir)

        mark_complete = _prompt_choice("Mark this control review as complete? [Y/N]: ", {"Y", "N"})
        if mark_complete == "Y":
            card["review_completed"] = True
            card["reviewed_by"] = reviewer_name
            card["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(queue_data, queue_dir)


def _calculate_session_summary(queue_data: dict) -> dict:
    approved_mappings = 0
    rejected_mappings = 0
    false_negatives_added = 0
    reviews_completed = 0
    reviews_pending = 0

    quarantine_queue = queue_data.get("quarantine_queue", [])
    for card in quarantine_queue:
        if card.get("review_completed"):
            reviews_completed += 1
        else:
            reviews_pending += 1

        for mapping in card.get("mappings_for_review", []):
            if mapping.get("human_decision") == "APPROVE":
                approved_mappings += 1
            elif mapping.get("human_decision") == "REJECT":
                rejected_mappings += 1

        for flagged_item in card.get("flagged_false_negatives", []):
            if flagged_item.get("human_decision") == "ADD_TO_MAPPING":
                false_negatives_added += 1

    review_queue = queue_data.get("review_queue", [])
    for card in review_queue:
        if card.get("review_completed"):
            reviews_completed += 1
        else:
            reviews_pending += 1

        for mapping in card.get("mappings_for_review", []):
            if mapping.get("human_decision") == "APPROVE":
                approved_mappings += 1
            elif mapping.get("human_decision") == "REJECT":
                rejected_mappings += 1

        for flagged_item in card.get("flagged_false_negatives", []):
            if flagged_item.get("human_decision") == "ADD_TO_MAPPING":
                false_negatives_added += 1

    return {
        "approved_mappings": approved_mappings,
        "rejected_mappings": rejected_mappings,
        "false_negatives_added": false_negatives_added,
        "reviews_completed": reviews_completed,
        "reviews_pending": reviews_pending,
    }


def run_review_session(queue_dir: str, reviewer_name: str) -> None:
    """Run an interactive, resumable CLI review session."""
    queue_data = load_queue(queue_dir)

    quarantine_queue = queue_data.get("quarantine_queue", [])
    review_queue = queue_data.get("review_queue", [])

    pending_quarantined = sum(1 for card in quarantine_queue if not card.get("review_completed"))
    pending_review = sum(1 for card in review_queue if not card.get("review_completed"))
    total_pending = pending_quarantined + pending_review

    print("═══════════════════════════════════════════")
    print("COMPLIANCE MAPPING REVIEW SESSION")
    print(f"Reviewer : {reviewer_name}")
    print(f"Pending  : {total_pending} controls to review")
    print("═══════════════════════════════════════════")
    print(f"⛔ Quarantined pending first: {pending_quarantined}")

    try:
        _process_quarantine_queue(queue_data, reviewer_name, queue_dir)
        _process_review_queue(queue_data, reviewer_name, queue_dir)
    except _SessionExit:
        print("Review session interrupted by user request (exit).")

    session_summary = _calculate_session_summary(queue_data)

    print("═══════════════════════════════════════════")
    print("SESSION COMPLETE")
    print(f"Approved mappings       : {session_summary['approved_mappings']}")
    print(f"Rejected mappings       : {session_summary['rejected_mappings']}")
    print(f"False negatives added   : {session_summary['false_negatives_added']}")
    print(f"Reviews completed       : {session_summary['reviews_completed']}")
    print(f"Reviews still pending   : {session_summary['reviews_pending']}")
    print("═══════════════════════════════════════════")

    save_queue(queue_data, queue_dir)

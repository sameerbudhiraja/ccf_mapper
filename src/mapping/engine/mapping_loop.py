"""Core mapping loop — resumable, retryable per control."""
import json
import re
from pathlib import Path

from src.mapping.chat.client import get_client, chat_completion
from src.mapping.chat.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.mapping.output.result_writer import save_result


def _parse_llm_response(raw: str) -> list[dict]:
    """Extract and parse the JSON array from the LLM response.

    Handles cases where the LLM wraps JSON in markdown code fences.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _filter_mappings(raw_mappings: list[dict], framework: str) -> list[dict]:
    """Keep only FULL/PARTIAL mappings and attach framework name."""
    results = []
    for m in raw_mappings:
        if m.get("mapping") in ("FULL", "PARTIAL"):
            results.append({
                "safeguard_id": m["safeguard_id"],
                "framework": framework,
                "mapping": m["mapping"],
                "reason": m.get("reason", ""),
            })
    return results


def run_mapping(
    internal_controls: list[dict],
    safeguards: list[dict],
    results_dir: Path,
    model: str,
    max_retries: int = 2,
) -> None:
    """Map each internal control against all safeguards.

    - Skips controls that already have a result file (resumable).
    - Retries failed LLM calls up to max_retries times.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    client = get_client()
    framework = safeguards[0]["framework"] if safeguards else "Unknown"
    total = len(internal_controls)

    for idx, ic in enumerate(internal_controls, 1):
        ccf_id = ic["CCF ID"]
        result_path = results_dir / f"{ccf_id}.json"

        # Resumable — skip if already processed
        if result_path.exists():
            print(f"[{idx}/{total}] {ccf_id} — already exists, skipping")
            continue

        print(f"[{idx}/{total}] Processing {ccf_id} ...")
        user_prompt = build_user_prompt(ic, safeguards)

        # Retry loop
        for attempt in range(1, max_retries + 1):
            try:
                raw = chat_completion(client, model, SYSTEM_PROMPT, user_prompt)
                raw_mappings = _parse_llm_response(raw)
                mappings = _filter_mappings(raw_mappings, framework)
                save_result(
                    result_path=result_path,
                    ccf_id=ccf_id,
                    control_name=ic["Control Name"],
                    mappings=mappings,
                )
                print(f"  -> {len(mappings)} mappings saved")
                break
            except Exception as e:
                print(f"  Attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    print(f"  SKIPPED {ccf_id} after {max_retries} failed attempts")

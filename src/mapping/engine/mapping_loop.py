"""Core mapping loop — resumable, retryable per control.

Uses a LangChain LCEL chain (prompt | llm | parser) for each mapping call.
"""
import json
import re
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser

from src.mapping.chat.client import get_llm
from src.mapping.chat.prompt_builder import MAPPING_PROMPT, build_chain_input
from src.mapping.output.result_writer import save_result


def _build_chain(llm):
    """Build the LCEL mapping chain: prompt → LLM → JSON parser."""
    parser = JsonOutputParser()
    return MAPPING_PROMPT | llm | parser


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
    llm=None,
    max_retries: int = 2,
) -> None:
    """Map each internal control against all safeguards using a LangChain chain.

    - Skips controls that already have a result file (resumable).
    - Retries failed LLM calls up to max_retries times.
    """
    results_dir.mkdir(parents=True, exist_ok=True)

    if llm is None:
        llm = get_llm()

    chain = _build_chain(llm)
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
        chain_input = build_chain_input(ic, safeguards)

        # Retry loop
        for attempt in range(1, max_retries + 1):
            try:
                raw_mappings = chain.invoke(chain_input)
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

"""Core mapping loop — resumable, retryable per control.

Uses a LangChain LCEL chain (prompt | llm | parser) for each mapping call.
"""
import json
import re
from pathlib import Path
from typing import Any

from src.mapping.chat.client import get_llm
from src.mapping.chat.prompt_builder import MAPPING_PROMPT, build_chain_input
from src.mapping.output.result_writer import save_result


def _build_chain(llm):
    """Build the LCEL mapping chain: prompt → LLM response."""
    return MAPPING_PROMPT | llm


def _coerce_mapping_list(payload: Any) -> list[dict] | None:
    """Return mapping list from supported payload shapes."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        mappings = payload.get("mappings")
        if isinstance(mappings, list):
            return mappings
    return None


def _extract_json_payload(text: str) -> list[dict]:
    """Extract JSON list payload from plain, wrapped, or fenced model output."""
    # 1) Direct JSON
    try:
        parsed = _coerce_mapping_list(json.loads(text))
        if parsed is not None:
            return parsed
    except json.JSONDecodeError:
        pass

    # 2) Fenced code blocks (```json ... ```)
    for block in re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE):
        try:
            parsed = _coerce_mapping_list(json.loads(block))
            if parsed is not None:
                return parsed
        except json.JSONDecodeError:
            continue

    # 3) Embedded JSON payload within extra prose
    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            parsed = _coerce_mapping_list(obj)
            if parsed is not None:
                return parsed
        except json.JSONDecodeError:
            continue

    excerpt = text.strip().replace("\n", " ")[:180]
    raise ValueError(f"Unable to extract JSON mappings from model output: {excerpt}")


def _parse_raw_mappings(response: Any) -> list[dict]:
    """Normalize LangChain response into list[dict] mappings."""
    if isinstance(response, str):
        return _extract_json_payload(response)

    content = getattr(response, "content", None)
    if isinstance(content, str):
        return _extract_json_payload(content)
    if isinstance(content, list):
        text_parts = [part for part in content if isinstance(part, str)]
        if text_parts:
            return _extract_json_payload("\n".join(text_parts))

    raise ValueError(f"Unsupported LLM response type for parsing: {type(response).__name__}")


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
                response = chain.invoke(chain_input)
                raw_mappings = _parse_raw_mappings(response)
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

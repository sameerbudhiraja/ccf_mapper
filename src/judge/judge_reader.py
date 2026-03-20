"""Read persisted judge result files."""
import json
from pathlib import Path


def load_all_judge_results(judge_output_dir: str) -> list[dict]:
    """Load all persisted judge result files from disk."""
    out_dir = Path(judge_output_dir)
    if not out_dir.exists():
        return []

    results: list[dict] = []
    for file_path in sorted(out_dir.glob("*_judge.json")):
        with open(file_path, "r") as f:
            results.append(json.load(f))
    return results


def split_by_verdict(judge_results: list[dict]) -> dict:
    """Split judge results into verdict buckets."""
    buckets = {
        "APPROVED": [],
        "APPROVED_WITH_WARNINGS": [],
        "QUARANTINED": [],
    }
    for result in judge_results:
        verdict = result.get("overall_verdict")
        if verdict in buckets:
            buckets[verdict].append(result)
    return buckets

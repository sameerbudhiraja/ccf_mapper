"""Write one JSON judge result file per internal control."""
import json
from pathlib import Path


def write_judge_result(result: dict, output_dir: str) -> None:
    """Write the judge result for a single internal control to disk."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    internal_control_id = result.get("internal_control_id", "unknown_control")
    result_path = out_dir / f"{internal_control_id}_judge.json"

    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

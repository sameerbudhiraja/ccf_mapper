"""Save one JSON result file per internal control."""
import json
from datetime import datetime, timezone
from pathlib import Path


def save_result(
    result_path: Path,
    ccf_id: str,
    control_name: str,
    mappings: list[dict],
) -> None:
    """Write the mapping result for a single internal control to disk."""
    result = {
        "internal_control_id": ccf_id,
        "internal_control_name": control_name,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "total_mapped": len(mappings),
        "mappings": mappings,
    }
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

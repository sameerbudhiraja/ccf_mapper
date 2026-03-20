"""Persistence helpers for human review queue artifacts."""
import json
from pathlib import Path


def save_queue(queue_data: dict, output_dir: str) -> None:
    """Persist queue payload to disk."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "review_queue.json": queue_data.get("review_queue", []),
        "quarantine_queue.json": queue_data.get("quarantine_queue", []),
        "accepted_results.json": queue_data.get("accepted_results", []),
        "queue_summary.json": queue_data.get("summary", {}),
    }

    for filename, payload in files.items():
        with open(out_dir / filename, "w") as f:
            json.dump(payload, f, indent=2)


def load_queue(output_dir: str) -> dict:
    """Load queue payload from disk."""
    out_dir = Path(output_dir)

    def _read_json(path: Path, default):
        if not path.exists():
            return default
        with open(path, "r") as f:
            return json.load(f)

    review_queue = _read_json(out_dir / "review_queue.json", [])
    quarantine_queue = _read_json(out_dir / "quarantine_queue.json", [])
    accepted_results = _read_json(out_dir / "accepted_results.json", [])
    summary = _read_json(out_dir / "queue_summary.json", {})

    return {
        "accepted_results": accepted_results,
        "review_queue": review_queue,
        "quarantine_queue": quarantine_queue,
        "summary": summary,
    }

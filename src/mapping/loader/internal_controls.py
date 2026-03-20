"""Load internal controls from JSON."""
import json
from pathlib import Path

def load_internal_controls(filepath: Path) -> list[dict]:
    """Load internal controls JSON and return list of control dicts.

    Each dict has: CCF ID, Control Domain, Control Name, Control Description.
    """
    with open(filepath, "r") as f:
        controls = json.load(f)
    return controls

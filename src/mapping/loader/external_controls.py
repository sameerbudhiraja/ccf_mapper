"""Load external controls and flatten to safeguard level."""
import json
from pathlib import Path

print("Loading external controls...")

def load_and_flatten_safeguards(filepath: Path) -> list[dict]:
    """Load external controls JSON and flatten to individual safeguards.

    Input JSON structure:
        { "framework": "...", "controls": [ { "control_id", "control_title",
          "safeguards": [ { "safeguard_id", "safeguard_title", "safeguard_description" } ] } ] }

    Returns list of flat dicts:
        { "framework", "control_id", "control_title",
          "safeguard_id", "safeguard_title", "safeguard_description" }

    example output:
        {
            "framework": "CIS Controls v8",
            "control_id": "1",
            "control_title": "Inventory and Control of Enterprise Assets",
            "safeguard_id": "1.1",
            "safeguard_title": "Utilize an Active Discovery Tool",
            "safeguard_description": "Use an active discovery tool to identify devices connected to the network, including those that are not authorized. This helps maintain an accurate inventory of enterprise assets and reduces the attack surface by ensuring that only authorized devices are connected to the network."
        }
        {
            "framework": "CIS Controls v8",
            "control_id": "1",
            "control_title": "Inventory and Control of Enterprise Assets",
            "safeguard_id": "1.2",
            "safeguard_title": "Maintain a Detailed Enterprise Asset Inventory",
            "safeguard_description": "Maintain a comprehensive inventory of all enterprise assets, including hardware, software, and data."
        }
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    framework = data.get("framework", "Unknown")
    safeguards = []

    for control in data["controls"]:
        for sg in control.get("safeguards", []):
            safeguards.append({
                "framework": framework,
                "control_id": control["control_id"],
                "control_title": control["control_title"],
                "safeguard_id": sg["safeguard_id"],
                "safeguard_title": sg["safeguard_title"],
                "safeguard_description": sg["safeguard_description"],
            })
            
    return safeguards

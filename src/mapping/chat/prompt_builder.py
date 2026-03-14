"""Build the mapping prompt: 1 internal control vs all safeguards."""
import json
from .system_prompt import SYSTEM_PROMPT


def build_user_prompt(internal_control: dict, safeguards: list[dict]) -> str:
    """Build the user prompt containing 1 internal control and all safeguards as JSON."""
    ic_block = (
        f"INTERNAL CONTROL (CCF):\n"
        f"  CCF ID: {internal_control['CCF ID']}\n"
        f"  Control Domain: {internal_control['Control Domain']}\n"
        f"  Control Name: {internal_control['Control Name']}\n"
        f"  Control Description: {internal_control['Control Description']}\n"
    )

    sg_list = []
    for sg in safeguards:
        sg_list.append({
            "safeguard_id": sg["safeguard_id"],
            "safeguard_title": sg["safeguard_title"],
            "safeguard_description": sg["safeguard_description"],
        })

    
    # print("USER PROMPT:\n", ic_block
    #     + "\nEXTERNAL FRAMEWORK SAFEGUARDS:\n"
    #     + json.dumps(sg_list, indent=2)
    #     + "\n\nApply all 15 mapping rules and the evaluation checklist. "
    #     "Return the JSON array of mapped safeguards.")
    
    return (
        ic_block
        + "\nEXTERNAL FRAMEWORK SAFEGUARDS:\n"
        + json.dumps(sg_list, indent=2)
        + "\n\nApply all 15 mapping rules and the evaluation checklist. "
        "Return the JSON array of mapped safeguards."
    )

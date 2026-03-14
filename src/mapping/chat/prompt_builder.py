"""LangChain prompt template for the mapping pipeline.

The system prompt contains raw JSON examples with curly braces, so we use
SystemMessage directly (not a template) to avoid LangChain interpreting
them as template variables.  Only the user message is templated.
"""
import json

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from .system_prompt import SYSTEM_PROMPT


# -----------------------------------------------------------------
# Chat prompt — fixed SystemMessage + templated human message
# -----------------------------------------------------------------
USER_TEMPLATE = """\
INTERNAL CONTROL (CCF):
  CCF ID: {ccf_id}
  Control Domain: {control_domain}
  Control Name: {control_name}
  Control Description: {control_description}

EXTERNAL FRAMEWORK SAFEGUARDS:
{safeguards_json}

Apply all 16 mapping rules and the evaluation checklist. \
Return the JSON array of mapped safeguards."""

MAPPING_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessagePromptTemplate.from_template(USER_TEMPLATE),
])


def build_chain_input(internal_control: dict, safeguards: list[dict]) -> dict:
    """Build the input dict for the LangChain mapping chain.

    Args:
        internal_control: dict with keys CCF ID, Control Domain, Control Name,
                          Control Description.
        safeguards:       list of safeguard dicts with safeguard_id, safeguard_title,
                          safeguard_description.

    Returns:
        A dict ready to be passed to ``chain.invoke()``.
    """
    sg_list = [
        {
            "safeguard_id": sg["safeguard_id"],
            "safeguard_title": sg["safeguard_title"],
            "safeguard_description": sg["safeguard_description"],
        }
        for sg in safeguards
    ]

    return {
        "ccf_id": internal_control["CCF ID"],
        "control_domain": internal_control["Control Domain"],
        "control_name": internal_control["Control Name"],
        "control_description": internal_control["Control Description"],
        "safeguards_json": json.dumps(sg_list, indent=2),
    }

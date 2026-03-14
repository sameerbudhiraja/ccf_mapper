import os
import re
import json
import time
from pathlib import Path
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

llm_client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {},
)

MODEL = os.getenv("LLM_MODEL", "qwen3.5")

# ── paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]
DOC_TREE_PATH = BASE_DIR / "data/cache/doc_tree/CIS_doc_tree.md"
OUTPUT_FILE = BASE_DIR / "data/cache/extracted_controls/CIS_controls.json"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────────
def extract_text_fields(content: str) -> list[str]:
    """Pull every `text: '…'` or `text: "…"` value from the JS-like doc tree."""
    texts = []
    i = 0
    while i < len(content):
        idx = content.find("text:", i)
        if idx == -1:
            break
        j = idx + 5
        # skip whitespace after 'text:'
        while j < len(content) and content[j] in " \t":
            j += 1
        if j >= len(content) or content[j] not in "\"'":
            i = j + 1
            continue
        quote = content[j]
        j += 1
        start = j
        while j < len(content):
            if content[j] == "\\" and j + 1 < len(content):
                j += 2
                continue
            if content[j] == quote:
                break
            j += 1
        raw = content[start:j]
        # unescape
        raw = (
            raw.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
        texts.append(raw)
        i = j + 1
    return texts


def split_into_control_sections(full_text: str) -> dict[int, str]:
    """Split reconstructed document text into per-control chunks."""
    pattern = re.compile(r"CONTROL\s+(\d+)\b")
    matches = list(pattern.finditer(full_text))
    sections: dict[int, str] = {}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if num in sections:
            continue  # skip duplicate (appendix index)
        start = m.start()
        # find the next *different* control boundary
        end = len(full_text)
        for j in range(i + 1, len(matches)):
            if int(matches[j].group(1)) != num:
                end = matches[j].start()
                break
        sections[num] = full_text[start:end].strip()
    return sections


# ── main ─────────────────────────────────────────────────────────────────────
print("Reading doc tree …")
raw = DOC_TREE_PATH.read_text()
text_blocks = extract_text_fields(raw)
full_text = "\n\n".join(text_blocks)
control_sections = split_into_control_sections(full_text)
print(f"Found {len(control_sections)} control sections (expecting 18)")

EXTRACTION_PROMPT = """\
You are a compliance framework document parser.

Your task is to analyze the document section below and extract ALL cybersecurity or compliance controls and their safeguards (sub-controls). Convert the extracted information into a structured JSON format.

STRICT EXTRACTION RULES:

1. Extract controls EXACTLY as written in the document.
2. Do NOT summarize, modify, paraphrase, or infer text.
3. Preserve the hierarchy:
   Control → Safeguards (Sub-controls).
4. Maintain the exact numbering format used in the document.
   Examples: "1", "2", "1.1", "1.2", "6.6".
5. Safeguards must be assigned to the correct parent control.
6. If a control does not contain safeguards, return an empty array [].
7. If a description is not present, return null.
8. If the document contains tables, treat each row as a potential control or safeguard.
9. Extract EVERY control appearing in the text.
10. Preserve the original wording for titles and descriptions.
11. Descriptions must contain the full paragraph text associated with the control or safeguard.
12. Do NOT invent missing information.
13. Ignore unrelated explanatory text that is not part of a control definition.
14. Output ONLY valid JSON — no markdown, no comments, no explanations.

EXPECTED OUTPUT FORMAT:

{
  "framework": "CIS Controls v8",
  "controls": [
    {
      "control_family": "string or null",
      "control_id": "string",
      "control_title": "string",
      "control_description": "string or null",
      "safeguards": [
        {
          "safeguard_id": "string",
          "safeguard_title": "string",
          "safeguard_description": "string or null"
        }
      ]
    }
  ]
}

VALIDATION REQUIREMENTS:

- Safeguard IDs must match their control hierarchy.
- Safeguards must belong to the correct control.
- Maintain the exact numbering format found in the document.
- Preserve the exact wording from the document.
- Extract ALL controls present in the text.

Return ONLY the JSON object.

--- SECTION START ---
{section}
--- SECTION END ---
"""

MAX_RETRIES = 3
all_controls: list[dict] = []

for ctrl_num in sorted(control_sections):
    section = control_sections[ctrl_num]
    print(f"\n▸ Control {ctrl_num} ({len(section)} chars) …")

    for attempt in range(MAX_RETRIES):
        try:
            resp = llm_client.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(section=section),
                    }
                ],
            )
            result = resp["message"]["content"]

            # strip markdown code fences if present
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)

            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                all_controls.extend(parsed)
            elif isinstance(parsed, dict):
                all_controls.append(parsed)

            print(f"  ✓ Control {ctrl_num} extracted")
            break

        except json.JSONDecodeError:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: invalid JSON")
            if attempt == MAX_RETRIES - 1:
                all_controls.append(
                    {
                        "control_id": f"CIS Control {ctrl_num}",
                        "raw_extraction": result,
                        "parse_error": "LLM response was not valid JSON",
                    }
                )
            else:
                time.sleep(3)

        except Exception as e:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print(f"  ✗ Skipped Control {ctrl_num}")

with OUTPUT_FILE.open("w") as f:
    json.dump(all_controls, f, indent=2)

print(f"\nDone — {len(all_controls)} entries saved to {OUTPUT_FILE}")
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

# ══════════════════════════════════════════════════════════════════════════
# ██  SWITCH FRAMEWORK HERE  ██
# Set ACTIVE_FRAMEWORK to either "CIS" or "ISO27001"
# ══════════════════════════════════════════════════════════════════════════
ACTIVE_FRAMEWORK = "ISO27001"  # ← change this to switch
# ══════════════════════════════════════════════════════════════════════════

# ── framework configurations ──────────────────────────────────────────────
FRAMEWORKS = {
    "CIS": {
        "doc_tree":   "CIS_doc_tree.md",
        "output":     "CIS_controls.json",
        "label":      "CIS Controls v8",
        "item_name":  "Control",
        "result_key": "controls",
        "split_fn":   "cis",   # which splitter to use (see below)
        "prompt": """\
You are a compliance framework document parser.

Your task is to analyze the document section below and extract ALL cybersecurity or compliance controls and their safeguards (sub-controls). Convert the extracted information into a structured JSON format.

STRICT EXTRACTION RULES:

1. Extract controls EXACTLY as written in the document.
2. Do NOT summarize, modify, paraphrase, or infer text.
3. Preserve the hierarchy: Control → Safeguards (Sub-controls).
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

{{
  "framework": "CIS Controls v8",
  "controls": [
    {{
      "control_family": "string or null",
      "control_id": "string",
      "control_title": "string",
      "control_description": "string or null",
      "safeguards": [
        {{
          "safeguard_id": "string",
          "safeguard_title": "string",
          "safeguard_description": "string or null"
        }}
      ]
    }}
  ]
}}

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
""",
    },

    "ISO27001": {
        "doc_tree":   "ISO27001_doc_tree.md",
        "output":     "ISO27001_2022.json",
        "label":      "ISO 27001:2022",
        "item_name":  "Clause",
        "result_key": "clauses",
        "split_fn":   "iso27001",   # which splitter to use (see below)
        "prompt": """\
You are a compliance framework document parser.

Your task is to analyze the document section below and extract ALL information security controls from this ISO 27001:2022 clause. Convert the extracted information into a structured JSON format.

STRICT EXTRACTION RULES:

1. Extract controls EXACTLY as written in the document.
2. Do NOT summarize, modify, paraphrase, or infer text.
3. Preserve the hierarchy: Clause → Controls.
4. Maintain the exact numbering format used in the document.
   Examples: "5", "5.1", "5.2", "6.1", "8.34".
5. Do NOT add any "A." prefix to control IDs — use the exact numbering from the document.
6. If a control does not contain sub-controls, return an empty array [].
7. If a description or purpose is not present, return null.
8. Extract EVERY control appearing in the text.
9. Preserve the original wording for titles and descriptions.
10. Descriptions must contain the full paragraph text associated with the control.
11. Do NOT invent missing information.
12. Output ONLY valid JSON — no markdown, no comments, no explanations.

EXPECTED OUTPUT FORMAT:

{{
  "clause_id": "string (e.g. '5')",
  "clause_title": "string (e.g. 'Organizational Controls')",
  "controls": [
    {{
      "control_id": "string (e.g. '5.1')",
      "control_title": "string",
      "control_description": "string or null",
      "purpose": "string or null"
    }}
  ]
}}

VALIDATION REQUIREMENTS:

- Control IDs must match their clause hierarchy (e.g. clause "6" → controls "6.1", "6.2" ...).
- Do NOT prefix IDs with "A." — use exact document numbering.
- Preserve the exact wording from the document.
- Extract ALL controls present in the text.

Return ONLY the JSON object.

--- SECTION START ---
{section}
--- SECTION END ---
""",
    },
}

# ── load active config ────────────────────────────────────────────────────
cfg = FRAMEWORKS[ACTIVE_FRAMEWORK]

BASE_DIR      = Path(__file__).resolve().parents[3]
DOC_TREE_PATH = BASE_DIR / f"data/cache/doc_tree/{cfg['doc_tree']}"
OUTPUT_FILE   = BASE_DIR / f"data/cache/extracted_controls/{cfg['output']}"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

print(f"Framework : {cfg['label']}")
print(f"Doc tree  : {DOC_TREE_PATH}")
print(f"Output    : {OUTPUT_FILE}")

# ── configuration ─────────────────────────────────────────────────────────
MAX_RETRIES = 3


# ── helpers ───────────────────────────────────────────────────────────────
def extract_text_fields(content: str) -> list[str]:
    """Pull every `text: '…'` or `text: "…"` value from the JS-like doc tree."""
    texts = []
    i = 0
    while i < len(content):
        idx = content.find("text:", i)
        if idx == -1:
            break
        j = idx + 5
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


def split_cis(full_text: str) -> dict[str, str]:
    """Split reconstructed text into per-control chunks for CIS."""
    pattern = re.compile(r"CONTROL\s+(\d+)\b")
    matches = list(pattern.finditer(full_text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        if key in sections:
            continue
        start = m.start()
        end = len(full_text)
        for j in range(i + 1, len(matches)):
            if matches[j].group(1) != key:
                end = matches[j].start()
                break
        sections[key] = full_text[start:end].strip()
    return sections


def split_iso27001(full_text: str) -> dict[str, str]:
    """Split reconstructed text into per-clause chunks for ISO 27001:2022.
    Targets top-level clause headers like '5 –', '6 –', '7 –', '8 –'.
    """
    pattern = re.compile(r"(?:^|\n)([5-8])\s*[–-]\s*\w")
    matches = list(pattern.finditer(full_text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1)
        if key in sections:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        sections[key] = full_text[start:end].strip()
    return sections


SPLITTERS = {
    "cis":      split_cis,
    "iso27001": split_iso27001,
}


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


# ── build sections ────────────────────────────────────────────────────────
print("\nReading doc tree ...")
raw         = DOC_TREE_PATH.read_text()
text_blocks = extract_text_fields(raw)
full_text   = "\n\n".join(text_blocks)

splitter  = SPLITTERS[cfg["split_fn"]]
sections  = splitter(full_text)
item_name = cfg["item_name"]

print(f"Found {len(sections)} {item_name.lower()} sections")

# ── extract items one by one ──────────────────────────────────────────────
all_results: list[dict] = []

for key in sorted(sections, key=lambda x: int(x)):
    section = sections[key]
    print(f"\n▸ {item_name} {key} ({len(section)} chars) ...")

    result = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = llm_client.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": cfg["prompt"].format(section=section),
                    }
                ],
            )
            result  = resp["message"]["content"]
            cleaned = strip_code_fences(result)
            parsed  = json.loads(cleaned)

            if isinstance(parsed, list):
                all_results.extend(parsed)
            elif isinstance(parsed, dict):
                all_results.append(parsed)

            print(f"  ✓ {item_name} {key} extracted")
            break

        except json.JSONDecodeError:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: invalid JSON")
            if attempt == MAX_RETRIES - 1:
                all_results.append({
                    "id":          key,
                    "raw":         result,
                    "parse_error": "LLM response was not valid JSON",
                })
            else:
                time.sleep(3)

        except Exception as e:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            else:
                print(f"  ✗ Skipped {item_name} {key}")

# ── save results ──────────────────────────────────────────────────────────
output = {
    "framework":      cfg["label"],
    cfg["result_key"]: all_results,
}

with OUTPUT_FILE.open("w") as f:
    json.dump(output, f, indent=2)

print(f"\nDone — {len(all_results)} {cfg['result_key']} saved to {OUTPUT_FILE}")
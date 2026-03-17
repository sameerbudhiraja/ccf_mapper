import os
import json
import time
from dotenv import load_dotenv
from pageindex import PageIndexClient
from pathlib import Path

load_dotenv()

pi_api_key = os.getenv("PAGEINDEX_API_KEY")
if not pi_api_key:
    raise ValueError("PAGEINDEX_API_KEY not found in environment variables.")

pi_client = PageIndexClient(api_key=pi_api_key)

# ══════════════════════════════════════════════════════════════════════════
# ██  SWITCH FRAMEWORK HERE  ██
# Set ACTIVE_FRAMEWORK to either "CIS" or "ISO27001"
# ══════════════════════════════════════════════════════════════════════════
ACTIVE_FRAMEWORK = "ISO27001"  # ← change this to switch
# ══════════════════════════════════════════════════════════════════════════

# ── framework configurations ──────────────────────────────────────────────
FRAMEWORKS = {
    "CIS": {
        "doc_id":       "pi-cmmlkg7qz008p74qnuc5kwai7",
        "output_file":  "CIS_controls.json",
        "label":        "CIS Controls v8.1",
        "items":        [str(n) for n in range(1, 19)],  # "1" through "18"
        "item_name":    "Control",
        "result_key":   "controls",
        "prompt": """
Extract CIS Control {item} from this document.

Return a JSON object with these fields:
- control_id (string, e.g. "1")
- control_title (string)
- control_description (string — the Overview text)
- safeguards (array of objects with: safeguard_id, safeguard_title, safeguard_description)

Preserve the original wording from the document.
Return strictly valid JSON only. Do not return any text other than the JSON object.
""",
    },

    "ISO27001": {
        "doc_id":       "pi-cmmrhkfbt003h6gpizq6bya0a",
        "output_file":  "ISO27001_2022.json",
        "label":        "ISO 27001:2022",
        "items":        ["5", "6", "7", "8"],
        "item_name":    "Clause",
        "result_key":   "clauses",
        "prompt": """
Extract all controls under clause {item} from this ISO 27001:2022 document.

Return a JSON object with these fields:
- clause_id (string, e.g. "5")
- clause_title (string, e.g. "Organizational Controls")
- controls (array of objects with: control_id, control_title, control_description, purpose)

Where:
- control_id: the full identifier exactly as written in the document (e.g. "5.1", "5.2", "6.1")
- control_title: the short title of the control
- control_description: the main control text (what shall be done)
- purpose: the stated purpose of the control if available, otherwise omit the field

Important: Do NOT add any "A." prefix to control IDs. Use the exact numbering from the document.
Preserve the original wording from the document.
Return strictly valid JSON only. Do not return any text other than the JSON object.
""",
    },
}

# ── load active config ────────────────────────────────────────────────────
cfg = FRAMEWORKS[ACTIVE_FRAMEWORK]

doc_id     = cfg["doc_id"]
item_name  = cfg["item_name"]
result_key = cfg["result_key"]
items      = cfg["items"]

BASE_DIR    = Path(__file__).resolve().parents[3]
OUTPUT_FILE = BASE_DIR / f"data/cache/extracted_controls/{cfg['output_file']}"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

print(f"Framework : {cfg['label']}")
print(f"Output    : {OUTPUT_FILE}")

# ── configuration ─────────────────────────────────────────────────────────
MAX_RETRIES     = 5
INITIAL_BACKOFF = 10  # seconds

# ── wait for document processing ──────────────────────────────────────────
print("\nChecking document status...")
while True:
    doc_info = pi_client.get_document(doc_id)
    status   = doc_info.get("status")
    if status == "completed":
        print(f"Document ready! ({doc_info.get('pageNum', '?')} pages)")
        break
    elif status == "failed":
        raise RuntimeError(f"Document processing failed: {doc_info}")
    print(f"Document status: {status} — waiting...")
    time.sleep(5)


# ── helpers ───────────────────────────────────────────────────────────────
def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_with_streaming(prompt: str) -> str:
    full_response = ""
    for chunk in pi_client.chat_completions(
        messages=[{"role": "user", "content": prompt}],
        doc_id=doc_id,
        stream=True,
    ):
        full_response += chunk
    return full_response


def extract_non_streaming(prompt: str) -> str:
    response = pi_client.chat_completions(
        messages=[{"role": "user", "content": prompt}],
        doc_id=doc_id,
    )
    return response["choices"][0]["message"]["content"]


def parse_result(raw: str) -> dict | list:
    """Strip fences and parse JSON, raises JSONDecodeError on failure."""
    return json.loads(strip_code_fences(raw))


# ── extract items one by one ──────────────────────────────────────────────
all_results = []

for item in items:
    prompt = cfg["prompt"].format(item=item)
    total  = len(items)
    index  = items.index(item) + 1
    print(f"\nExtracting {item_name} {item} ({index}/{total}) ...")

    result = None
    for attempt in range(MAX_RETRIES):
        backoff = INITIAL_BACKOFF * (2 ** attempt)
        try:
            result  = extract_non_streaming(prompt)
            parsed  = parse_result(result)

            if isinstance(parsed, list):
                all_results.extend(parsed)
            elif isinstance(parsed, dict):
                all_results.append(parsed)

            print(f"  OK — extracted {item_name} {item}")
            break

        except json.JSONDecodeError:
            if attempt == 0:
                # one streaming retry before giving up
                print(f"  JSON parse failed, retrying with streaming...")
                try:
                    result = extract_with_streaming(prompt)
                    parsed = parse_result(result)
                    if isinstance(parsed, list):
                        all_results.extend(parsed)
                    elif isinstance(parsed, dict):
                        all_results.append(parsed)
                    print(f"  OK — extracted {item_name} {item} (via streaming)")
                    break
                except json.JSONDecodeError:
                    pass  # fall through to retry loop

            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: JSON parse error")
            if attempt == MAX_RETRIES - 1:
                all_results.append({
                    "id":          item,
                    "raw":         result,
                    "parse_error": True,
                })
                print(f"  Saved raw response for {item_name} {item}")

        except Exception as e:
            error_msg  = str(e)
            is_timeout = any(t in error_msg.lower() for t in ["504", "gateway time-out", "timeout"])
            if is_timeout:
                print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: timeout — retrying in {backoff}s...")
            else:
                print(f"  Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff)
            else:
                print(f"  SKIPPED {item_name} {item} after {MAX_RETRIES} failed attempts.")

    time.sleep(2)  # rate-limit between items

# ── save results ──────────────────────────────────────────────────────────
output = {
    "framework": cfg["label"],
    result_key:  all_results,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nDone. {len(all_results)} {result_key} saved to {OUTPUT_FILE}")
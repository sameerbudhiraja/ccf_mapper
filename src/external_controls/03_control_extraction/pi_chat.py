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

doc_id = "pi-cmmlkg7qz008p74qnuc5kwai7"

# ── paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_FILE = BASE_DIR / "data/cache/extracted_controls/CIS_controls.json"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── wait for document processing ─────────────────────────────────────────
print("Checking document status...")
while True:
    doc_info = pi_client.get_document(doc_id)
    status = doc_info.get("status")
    if status == "completed":
        print(f"Document ready! ({doc_info.get('pageNum', '?')} pages)")
        break
    elif status == "failed":
        raise RuntimeError(f"Document processing failed: {doc_info}")
    print(f"Document status: {status} — waiting...")
    time.sleep(5)

# ── configuration ────────────────────────────────────────────────────────
MAX_RETRIES = 5
INITIAL_BACKOFF = 10  # seconds

# CIS Controls v8.1 has 18 controls
CONTROL_NUMBERS = list(range(1, 19))

EXTRACTION_PROMPT = """
Extract CIS Control {control_num} from this document.

Return a JSON object with these fields:
- control_id (string, e.g. "1")
- control_title (string)
- control_description (string — the Overview text)
- safeguards (array of objects with: safeguard_id, safeguard_title, safeguard_description)

Preserve the original wording from the document.
Return strictly valid JSON only. Do not return any text other than the JSON object.
"""


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_with_streaming(prompt: str) -> str:
    """Use streaming chat to collect the full response."""
    full_response = ""
    for chunk in pi_client.chat_completions(
        messages=[{"role": "user", "content": prompt}],
        doc_id=doc_id,
        stream=True,
    ):
        full_response += chunk
    return full_response


def extract_non_streaming(prompt: str) -> str:
    """Use non-streaming chat to get a single response."""
    response = pi_client.chat_completions(
        messages=[{"role": "user", "content": prompt}],
        doc_id=doc_id,
    )
    return response["choices"][0]["message"]["content"]


# ── extract controls one by one ──────────────────────────────────────────
all_controls = []

for control_num in CONTROL_NUMBERS:
    prompt = EXTRACTION_PROMPT.format(control_num=control_num)
    print(f"\nExtracting Control {control_num}/18 ...")

    for attempt in range(MAX_RETRIES):
        backoff = INITIAL_BACKOFF * (2 ** attempt)

        try:
            result = extract_non_streaming(prompt)
            cleaned = strip_code_fences(result)

            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    all_controls.extend(parsed)
                elif isinstance(parsed, dict):
                    all_controls.append(parsed)
            except json.JSONDecodeError:
                # fallback: try streaming if non-streaming gave bad JSON
                print(f"  JSON parse failed, retrying with streaming...")
                result = extract_with_streaming(prompt)
                cleaned = strip_code_fences(result)
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    all_controls.extend(parsed)
                elif isinstance(parsed, dict):
                    all_controls.append(parsed)

            print(f"  OK — extracted Control {control_num}")
            break

        except json.JSONDecodeError:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: JSON parse error")
            if attempt == MAX_RETRIES - 1:
                all_controls.append({
                    "control_id": str(control_num),
                    "raw": result,
                    "parse_error": True,
                })
                print(f"  Saved raw response for Control {control_num}")

        except Exception as e:
            error_msg = str(e)
            is_timeout = any(t in error_msg.lower() for t in ["504", "gateway time-out", "timeout"])

            if is_timeout:
                print(f"  Attempt {attempt + 1}/{MAX_RETRIES}: timeout — retrying in {backoff}s...")
            else:
                print(f"  Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(backoff)
            else:
                print(f"  SKIPPED Control {control_num} after {MAX_RETRIES} failed attempts.")

    # rate-limit between controls
    time.sleep(2)

# ── save results ─────────────────────────────────────────────────────────
output = {
    "framework": "CIS Controls v8.1",
    "controls": all_controls,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nDone. {len(all_controls)} controls saved to {OUTPUT_FILE}")
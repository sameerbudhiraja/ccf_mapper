"""Entry point for the CCF mapping pipeline."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is on sys.path so `src.` imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.mapping.chat.client import get_llm
from src.mapping.loader.internal_controls import load_internal_controls
from src.mapping.loader.external_controls import load_and_flatten_safeguards
from src.mapping.engine.mapping_loop import run_mapping


def main() -> None:
    model_name = os.getenv("LLM_MODEL")
    if not model_name:
        print("ERROR: LLM_MODEL is not set in .env")
        sys.exit(1)

    # Paths
    internal_path = PROJECT_ROOT / "data" / "input" / "internal_controls" / "adobe_internal_controls.json"
    external_path = PROJECT_ROOT / "data" / "cache" / "extracted_controls" / "CIS_controls_pi.json"
    results_dir = Path(__file__).resolve().parent / "results"

    # Load data
    print("Loading internal controls ...")
    internal_controls = load_internal_controls(internal_path)
    print(f"  {len(internal_controls)} internal controls loaded")

    print("Loading and flattening external safeguards ...")
    safeguards = load_and_flatten_safeguards(external_path)
    print(f"  {len(safeguards)} safeguards loaded")

    # Initialise LangChain LLM
    llm = get_llm()
    print(f"\nStarting mapping with model: {model_name} (via LangChain)")
    print(f"Results directory: {results_dir}\n")

    # Run mapping
    run_mapping(internal_controls, safeguards, results_dir, llm=llm)
    print("\nMapping complete.")


if __name__ == "__main__":
    main()

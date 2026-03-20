"""
Global configuration settings for CCF Mapper.
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
CACHE_DIR = DATA_DIR / "cache"

# Judge / Review / Final Output Paths
JUDGE_OUTPUT_DIR = PROJECT_ROOT / "output" / "judge_results"
REVIEW_QUEUE_DIR = PROJECT_ROOT / "output" / "review_queue"
FINAL_OUTPUT_DIR = PROJECT_ROOT / "output" / "final_output"

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, etc.
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/v1")

# PageIndex Configuration
PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")

# Mapping Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
MAPPING_STATUSES = ["matched", "partial", "not_matched"]

# Processing Configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

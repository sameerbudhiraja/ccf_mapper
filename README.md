# CCF Mapper 3.0

**Automated compliance control mapping** — extracts security controls from PDF frameworks using **Vectorless RAG** (via [PageIndex](https://pageindex.dev)), then maps them against your internal control library using a locally-hosted LLM through Ollama.

> [!NOTE]
> **Current state:** CIS v8 is the only framework with extracted controls available. The pipeline runs entirely from the command line.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Vectorless RAG — Control Extraction](#vectorless-rag--control-extraction)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Setup](#setup)
6. [Configuration](#configuration)
7. [Internal Controls Input Format](#internal-controls-input-format)
8. [External Framework Controls Format](#external-framework-controls-format)
9. [Running the Pipeline](#running-the-pipeline)
10. [Output Format](#output-format)
11. [Resumable Runs](#resumable-runs)

---

## How It Works

CCF Mapper automates the end-to-end process of cross-framework compliance mapping through a **three-stage pipeline**:

```
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│   STAGE 1 — EXTRACT     │     │   STAGE 2 — LOAD        │     │   STAGE 3 — MAP         │
│                         │     │                         │     │                         │
│  PDF Framework Docs     │     │  Internal Controls JSON  │     │  Each internal control   │
│         ↓               │────▶│  External Safeguards JSON │────▶│  vs all safeguards       │
│  Vectorless RAG         │     │         ↓               │     │         ↓               │
│  (PageIndex)            │     │  Flatten & Validate      │     │  LLM Classification     │
│         ↓               │     │                         │     │  (FULL / PARTIAL / NONE) │
│  Structured JSON        │     │                         │     │                         │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

1. **Extract** — PDF framework documents are fed through PageIndex's Vectorless RAG to extract structured controls and safeguards. No vector database, no embeddings — just page-aware retrieval that preserves document structure.
2. **Load** — Internal controls (your organization's CCF) and external safeguards (the extracted framework) are loaded, flattened, and prepared for comparison.
3. **Map** — A locally-running LLM evaluates each internal control against every external safeguard, classifying each pair as `FULL`, `PARTIAL`, or `NONE`. Only meaningful mappings (`FULL` / `PARTIAL`) are persisted.

The run is **fully resumable** — each internal control produces its own result file, so interrupted runs pick up exactly where they left off.

---

## Vectorless RAG — Control Extraction

The most critical (and novel) part of this pipeline is how external framework controls are **extracted from raw PDF documents** — using **Vectorless RAG** powered by [PageIndex](https://pageindex.dev).

### Why Not Traditional RAG?

Traditional RAG pipelines require:
- Chunking documents into fragments
- Generating vector embeddings for each chunk
- Storing embeddings in a vector database (Pinecone, Weaviate, etc.)
- Performing similarity search at query time

This introduces **significant problems** when working with compliance/regulatory PDFs:
- **Tabular data is destroyed** during chunking — control IDs, safeguard descriptions, and hierarchical structures get split across chunks.
- **Context loss** — a safeguard description separated from its parent control loses critical meaning.
- **Embedding drift** — security terminology is dense and nuanced; generic embeddings often fail to distinguish between superficially similar but semantically different controls.

### How Vectorless RAG Works

PageIndex takes a fundamentally different approach:

1. **Page Indexing** — The PDF is indexed page-by-page, preserving the exact layout, tables, and hierarchical relationships as they appear in the document.
2. **Direct Page Retrieval** — Instead of searching through vector embeddings, relevant pages are retrieved directly based on the document's structure and content.
3. **LLM Extraction** — An LLM reads the retrieved pages in their original context and extracts structured control data (IDs, titles, descriptions, safeguards) with full awareness of the document's hierarchy.

### Results

Using Vectorless RAG for control extraction produced **significantly better results** compared to traditional RAG approaches:

| Metric | Traditional RAG | Vectorless RAG (PageIndex) |
|--|--|--|
| Control structure preservation | ❌ Often broken | ✅ Fully preserved |
| Parent-child relationships | ❌ Lost in chunks | ✅ Maintained |
| Tabular data accuracy | ❌ Fragmented | ✅ Intact |
| Extraction setup complexity | High (vector DB + embeddings) | Low (API key only) |

The extracted controls are cached as JSON under `data/cache/extracted_controls/` and reused across mapping runs — extraction only needs to happen once per framework.

### Extraction Notebooks

Reference notebooks demonstrating the PageIndex integration are available in `.pageindex.github/`:

| Notebook | Purpose |
|--|--|
| `agentic_retrieval.ipynb` | Full agentic retrieval workflow |
| `pageIndex_chat_quickstart.ipynb` | Quick-start chat interface |
| `pageindex_RAG_simple.ipynb` | Simple RAG pipeline example |
| `vision_RAG_pageindex.ipynb` | Vision-based RAG for complex layouts |

---

## Project Structure

```
ccf_mapper_3.0/
├── .env                                    # Environment variables (not committed)
├── .env.example                            # Sample env with PageIndex + Ollama config
├── requirements.txt                        # Python dependencies
│
├── .pageindex.github/                      # PageIndex / Vectorless RAG notebooks
│   ├── agentic_retrieval.ipynb
│   ├── pageIndex_chat_quickstart.ipynb
│   ├── pageindex_RAG_simple.ipynb
│   └── vision_RAG_pageindex.ipynb
│
├── documents/                              # Source framework PDFs
│   ├── open-source-ccf.pdf                 # Open-source CCF reference
│   └── ccf-research-notes.pdf              # Research notes
│
├── data/
│   ├── cache/
│   │   └── extracted_controls/             # ← Vectorless RAG output
│   │       ├── CIS_controls_pi.json        #   CIS v8 via PageIndex
│   │       └── CIS_controls_llama.json     #   CIS v8 via LLaMA (comparison)
│   └── input/
│       └── internal_controls/
│           └── adobe_internal_controls.json # Default internal controls file
│
├── examples/
│   └── cis_pi_extracted_controls.json      # Example extracted controls output
│
└── src/
    ├── __init__.py                         # Package init (v3.0.0)
    ├── pipeline.py                         # Pipeline stage definitions
    ├── config/
    │   └── settings.py                     # Global config (paths, LLM, PageIndex)
    ├── internal_controls/
    │   └── internal_control.py             # Loads Adobe internal controls
    ├── external_controls/                  # External control processing (WIP)
    ├── utils/
    │   ├── logger.py                       # Logging configuration
    │   └── validators.py                   # Data quality validators
    └── mapping/
        ├── run_mapping.py                  # CLI entry point
        ├── loader/
        │   ├── internal_controls.py        # Loads internal controls JSON
        │   └── external_controls.py        # Loads + flattens framework controls
        ├── engine/
        │   └── mapping_loop.py             # Core resumable mapping loop
        ├── chat/
        │   ├── client.py                   # Ollama client wrapper
        │   ├── prompt_builder.py           # Builds LLM prompt per control
        │   └── system_prompt.py            # System prompt with 16 mapping rules
        ├── output/
        │   └── result_writer.py            # Writes one JSON file per control
        └── results/
            └── cis_v8/                     # Mapping results for CIS v8
                └── <CCF_ID>.json
```

---

## Prerequisites

| Requirement | Notes |
|--|--|
| Python 3.10+ | |
| [Ollama](https://ollama.com) | Running locally or via cloud |
| An Ollama model | e.g. `llama3.1:8b`, `qwen3.5:397b-cloud` |
| [PageIndex](https://pageindex.dev) API key | For extracting new frameworks (optional if using cached controls) |

Pull and serve your model before running the pipeline:

```bash
ollama pull llama3.1:8b
ollama serve
```

---

## Setup

```bash
# 1. Enter the project directory
cd ccf_mapper_3.0

# 2. Create and activate virtualenv
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env from the example
cp .env.example .env
# Then fill in your PAGEINDEX_API_KEY and OLLAMA_API_KEY
```

---

## Configuration

Add the following to your `.env` file at the project root:

```env
# Vectorless RAG — PageIndex API key for framework extraction
PAGEINDEX_API_KEY=your_api_key_here

# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.1

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=
```

| Variable | Required | Description |
|--|--|--|
| `PAGEINDEX_API_KEY` | For extraction | API key for PageIndex Vectorless RAG |
| `LLM_MODEL` | Yes | Ollama model name to use for mapping |
| `LLM_TEMPERATURE` | No | Controls randomness (default `0.1` — lower = more deterministic) |
| `OLLAMA_API_KEY` | No | Leave blank if running Ollama locally without auth |

---

## Internal Controls Input Format

The internal controls file must be a **JSON array** where every object has exactly these four keys:

| Key | Description |
|--|--|
| `CCF ID` | Unique identifier (e.g. `AM-01`) |
| `Control Domain` | High-level category (e.g. `Asset Management`) |
| `Control Name` | Short title |
| `Control Description` | Full description of what the control requires |

**Example:**

```json
[
  {
    "CCF ID": "AM-01",
    "Control Domain": "Asset Management",
    "Control Name": "Inventory Management",
    "Control Description": "Organization maintains an inventory of information systems, which is reconciled on a periodic basis."
  },
  {
    "CCF ID": "AM-02",
    "Control Domain": "Asset Management",
    "Control Name": "Inventory Management: Applications",
    "Control Description": "Organization maintains an inventory of application assets, which is reconciled on a periodic basis."
  }
]
```

The default file used by the pipeline is `data/input/internal_controls/adobe_internal_controls.json`. To use a different file, update `internal_path` in `src/mapping/run_mapping.py`.

---

## External Framework Controls Format

Framework files live under `data/cache/extracted_controls/`. These are the **output of the Vectorless RAG extraction** from PDF framework documents. Currently only CIS v8 is available.

The required JSON structure:

```json
{
  "framework": "CIS Controls v8",
  "controls": [
    {
      "control_id": "1",
      "control_title": "Inventory and Control of Enterprise Assets",
      "safeguards": [
        {
          "safeguard_id": "1.1",
          "safeguard_title": "Establish and Maintain Detailed Enterprise Asset Inventory",
          "safeguard_description": "Establish and maintain an accurate, detailed, and up-to-date inventory of all enterprise assets..."
        }
      ]
    }
  ]
}
```

To add another framework:
1. Use the PageIndex notebooks in `.pageindex.github/` to extract controls from a new PDF
2. Save the output JSON under `data/cache/extracted_controls/`
3. Update `external_path` in `src/mapping/run_mapping.py`

---

## Running the Pipeline

```bash
# From project root, with venv active
python -m src.mapping.run_mapping
```

The script loads internal controls and the CIS v8 safeguards (pre-extracted via Vectorless RAG), then maps each internal control one by one:

```
Loading internal controls ...
  120 internal controls loaded
Loading and flattening external safeguards ...
  153 safeguards loaded

Starting mapping with model: llama3.1:8b (via LangChain)
Results directory: src/mapping/results

[1/120] Processing AM-01 ...
  -> 4 mappings saved
[2/120] Processing AM-02 ...
  -> 2 mappings saved
[3/120] AM-03 — already exists, skipping
...

Mapping complete.
```

---

## Output Format

Each internal control produces one file at `src/mapping/results/cis_v8/<CCF_ID>.json`:

```json
{
  "internal_control_id": "AM-01",
  "internal_control_name": "Inventory Management",
  "processed_at": "2026-03-14T10:22:05.123456+00:00",
  "total_mapped": 3,
  "mappings": [
    {
      "safeguard_id": "1.1",
      "framework": "CIS Controls v8",
      "mapping": "FULL",
      "reason": "Both controls require maintaining an accurate inventory of information systems."
    },
    {
      "safeguard_id": "1.2",
      "framework": "CIS Controls v8",
      "mapping": "PARTIAL",
      "reason": "CCF control is broader; this safeguard specifically addresses unauthorized assets."
    }
  ]
}
```

| Field | Description |
|--|--|
| `mapping` | `FULL` — complete coverage, `PARTIAL` — partial coverage. `NONE` results are not written to disk. |
| `reason` | LLM-generated justification for the classification |
| `total_mapped` | Count of `FULL` + `PARTIAL` mappings for this control |

---

## Resumable Runs

Before processing each control the engine checks whether a result file already exists. If `results/cis_v8/AM-01.json` is present, that control is skipped. This means:

- You can safely interrupt (`Ctrl+C`) and restart the run at any time.
- To reprocess a specific control, delete its individual result file.
- To rerun everything from scratch, delete the `src/mapping/results/cis_v8/` directory.

---

## LLM Mapping Engine

The mapping engine is built with **LangChain** using an **LCEL chain** (`ChatPromptTemplate → ChatOllama → JsonOutputParser`) and a carefully engineered **16-rule system prompt** that instructs the LLM to reason like a security architect performing framework crosswalks. Key principles:

- **LCEL chain composition** — Prompt, LLM, and output parser are composed into a single reusable chain
- **Structured JSON parsing** — LangChain's `JsonOutputParser` handles markdown-fenced JSON extraction automatically
- **Intent-based matching** — Maps on security intent and required action, not keyword overlap
- **Mechanism class resolution** — Resolves specific technologies (e.g. "ARP scan") to their broader mechanism class (e.g. "active network discovery") before matching
- **Artifact precision** — Distinguishes between superficially similar security artifacts (SBOM ≠ Software Inventory ≠ Application Asset Inventory)
- **Prerequisite filtering** — Excludes safeguards that are merely prerequisites rather than direct coverage
- **Coverage threshold** — Rejects mappings that only address a minor peripheral subset of the control's requirements
- **Exhaustive evaluation** — Every safeguard is evaluated against every internal control; scanning never stops early

The system prompt includes positive and negative examples, a mandatory evaluation checklist, scan completion gates, and an empty-result verification gate to maximize mapping accuracy.

---

## Tech Stack

| Component | Technology |
|--|--|
| Control Extraction | [PageIndex](https://pageindex.dev) — Vectorless RAG |
| LLM Framework | [LangChain](https://python.langchain.com) — LCEL chains, prompt templates, output parsing |
| LLM Inference | [Ollama](https://ollama.com) via `langchain-ollama` (local or cloud) |
| Language | Python 3.10+ |
| Dependencies | `langchain`, `langchain-ollama`, `python-dotenv` |

# CCF Mapper 3.0

Automates mapping of a company's internal security controls to an external compliance framework using a locally-running LLM via Ollama.

**Current state:** CIS v8 is the only framework with extracted controls available. The pipeline runs entirely from the command line.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
5. [Configuration](#configuration)
6. [Internal Controls Input Format](#internal-controls-input-format)
7. [External Framework Controls Format](#external-framework-controls-format)
8. [Running the Pipeline](#running-the-pipeline)
9. [Output Format](#output-format)
10. [Resumable Runs](#resumable-runs)

---

## Overview

CCF Mapper takes your internal control library (exported as JSON) and maps each control against every safeguard in a target compliance framework. The mapping is performed by a locally-hosted LLM through Ollama, which evaluates each control-safeguard pair and classifies the relationship as `FULL`, `PARTIAL`, or `NONE`. `NONE` results are discarded — only meaningful mappings are saved.

The run is fully resumable: each internal control produces its own result file, so if a run is interrupted it continues from where it left off.

---

## Project Structure

```
ccf_mapper_3.0/
├── .env                                  # Environment variables (not committed)
├── requirements.txt                      # Python dependencies
│
├── data/
│   ├── cache/
│   │   └── extracted_controls/
│   │       ├── CIS_controls_pi.json      # CIS v8 extracted via PI model
│   │       └── CIS_controls_llama.json   # CIS v8 extracted via LLaMA model
│   └── input/
│       └── internal_controls/
│           └── adobe_internal_controls.json   # Default internal controls file
│
└── src/
    └── mapping/
        ├── run_mapping.py          # CLI entry point
        ├── loader/
        │   ├── internal_controls.py    # Loads internal controls JSON
        │   └── external_controls.py    # Loads + flattens framework controls JSON
        ├── engine/
        │   └── mapping_loop.py         # Core resumable mapping loop
        ├── chat/
        │   ├── client.py               # Ollama client wrapper
        │   ├── prompt_builder.py       # Builds LLM user prompt per control
        │   └── system_prompt.py        # System prompt with 15 mapping rules
        ├── output/
        │   └── result_writer.py        # Writes one JSON file per control
        └── results/
            └── cis_v8/                 # Mapping results for CIS v8
                └── <CCF_ID>.json
```

---

## Prerequisites

| Requirement                  | Notes                   |
| ---------------------------- | ----------------------- |
| Python 3.10+                 |                         |
| [Ollama](https://ollama.com) |running locally or cloud |
| An Ollama model              | e.g. `llama3.1:8b`      |

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

# 4. Create your .env
touch .env
```

---

## Configuration

Add the following to your `.env` file at the project root:

```env
# Required: the Ollama model name to use
LLM_MODEL=llama3.1:8b

# Optional: temperature (default 0.1 — lower = more deterministic output)
LLM_TEMPERATURE=0.1

# Optional: Ollama API key — leave blank if running locally without auth
OLLAMA_API_KEY=
```

---

## Internal Controls Input Format

The internal controls file must be a **JSON array** where every object has exactly these four keys:

| Key                   | Description                                   |
| --------------------- | --------------------------------------------- |
| `CCF ID`              | Unique identifier (e.g. `AM-01`)              |
| `Control Domain`      | High-level category (e.g. `Asset Management`) |
| `Control Name`        | Short title                                   |
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
  },
  {
    "CCF ID": "AM-03",
    "Control Domain": "Asset Management",
    "Control Name": "Inventory Reconciliation: ARP Table",
    "Control Description": "Organization reconciles network discovery scans against the established device inventory on a quarterly basis; non-inventoried devices are assigned an owner."
  },
  {
    "CCF ID": "AM-04",
    "Control Domain": "Asset Management",
    "Control Name": "Inventory Reconciliation: Logging",
    "Control Description": "Organization reconciles the enterprise log repository against the established device inventory on a quarterly basis; non-inventoried devices are assigned an owner."
  },
  {
    "CCF ID": "AM-05",
    "Control Domain": "Asset Management",
    "Control Name": "Inventory Labels",
    "Control Description": "Organization assets are labeled and have designated owners."
  }
]
```

The default file used by the pipeline is `data/input/internal_controls/adobe_internal_controls.json`. To use a different file, update `internal_path` in `src/mapping/run_mapping.py`.

---

## External Framework Controls Format

Framework files live under `data/cache/extracted_controls/`. Currently only CIS v8 is available. The required JSON structure is:

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
        },
        {
          "safeguard_id": "1.2",
          "safeguard_title": "Address Unauthorized Assets",
          "safeguard_description": "Ensure that a process exists to address unauthorized assets on a weekly basis..."
        }
      ]
    }
  ]
}
```

To add another framework: create a JSON file following this structure, place it under `data/cache/extracted_controls/`, then update `external_path` in `src/mapping/run_mapping.py`.

---

## Running the Pipeline

```bash
# From project root, with venv active
python -m src.mapping.run_mapping
```

The script loads the hardcoded internal controls and CIS v8 safeguards, then processes each internal control one by one:

```
Loading internal controls ...
  120 internal controls loaded
Loading and flattening external safeguards ...
  153 safeguards loaded

Starting mapping with model: llama3.1:8b
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

| Field          | Description                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------- |
| `mapping`      | `FULL` — complete coverage, `PARTIAL` — partial coverage. `NONE` results are not written to disk. |
| `reason`       | LLM-generated justification for the classification                                                |
| `total_mapped` | Count of `FULL` + `PARTIAL` mappings for this control                                             |

---

## Resumable Runs

Before processing each control the engine checks whether a result file already exists. If `results/cis_v8/AM-01.json` is present, that control is skipped. This means:

- You can safely interrupt (`Ctrl+C`) and restart the run at any time.
- To reprocess a specific control, delete its individual result file.
- To rerun everything from scratch, delete the `src/mapping/results/cis_v8/` directory.

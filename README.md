# Common Control Framework Mapper

## 1) Project Overview

CCF Mapper is an end-to-end automation pipeline for compliance control mapping.

In many compliance programs, teams manually compare internal controls against external frameworks, then spend additional time validating whether each suggested mapping is actually correct. That process is slow, repetitive, and difficult to scale.

This project solves that by automating the full mapping + validation loop:

- It ingests internal and external control datasets
- Runs LLM-based control-to-safeguard mapping
- Applies an LLM judge step to validate mapping quality
- Routes uncertain cases into a human review queue
- Produces final auditable outputs

If you run the mapping workflow in this project, you’ll get a 62% exact-match success rate and an 88% acceptable coverage rate (tested across 50 CIS controls) (after the judge step). This automates the mapping + validation loop, significantly reducing effort and review time compared to manual mapping.

---

## 2) Tech Stack / Tools Used

- **Python 3.10+**: Core implementation language for the full pipeline and CLI orchestration.
- **LangChain**: Standardized interface for prompt-driven LLM execution in mapping and judge flows.
- **Ollama (local or hosted)**: LLM runtime used for mapping and judging controls with configurable models.
- **python-dotenv**: Loads environment variables from `.env` for reproducible local setup.
- **PageIndex (Vectorless RAG)**: Used for extracting structured external controls from PDF frameworks while preserving hierarchy.
- **JSON-based data contracts**: Shared format across ingestion, mapping results, judge output, review queue, and final output.
- **CLI workflow**: Single-command pipeline execution for mapping, judge, review, and final bundle generation.

---

## 3) Project Structure

```text
ccf_mapper_3.0/
├── README.md
├── requirements.txt
├── data/
│   ├── cache/
│   │   ├── doc_tree/                    # Cached framework doc trees
│   │   └── extracted_controls/          # Extracted external safeguards (JSON)
│   └── input/
│       ├── external_controls/           # External control inputs (if manually provided)
│       └── internal_controls/           # Internal controls JSON (primary input)
├── documents/                           # Source documents / supporting artifacts
├── examples/
│   └── cis_pi_extracted_controls.json   # Example extracted framework controls
├── output/
│   ├── expected_output/                 # Benchmark/reference outputs
│   ├── final_output/                    # Final approved mappings + stats
│   ├── judge_results/                   # Per-control judge verdict files
│   └── review_queue/                    # Human review session queue data
├── src/
│   ├── pipeline.py                      # Main entrypoint (mapping/judge/review/final)
│   ├── config/settings.py               # Path + model + runtime configuration
│   ├── mapping/                         # Mapping engine, loaders, prompts, result writers
│   ├── judge/                           # Judge loop, parsing, and result serialization
│   ├── review/                          # Queue builder, human CLI, final output builder
│   ├── prompts/                         # System/user/judge prompt templates
│   └── utils/                           # Logging and validators
└── tools/                               # Helper scripts/utilities
```

### What the major modules do

- `src/pipeline.py`: Orchestrates stage execution through command-line flags.
- `src/mapping/`: Runs internal→external control mapping and stores per-control result files.
- `src/judge/`: Re-evaluates mapping outputs and classifies items as approved, warning, or quarantined.
- `src/review/`: Builds review queues for human decisions and compiles final auditable outputs.
- `output/judge_results/`: Judge artifacts used to measure quality and drive review.
- `output/final_output/`: Final accepted mappings, rejected mappings, audit trail, and statistics.

---

## 4) Workflow / How It Works

The pipeline is designed as a staged, resumable workflow:

1. **Data input / ingestion**
   - Loads internal controls from `data/input/internal_controls/...`
   - Loads external safeguards from extracted controls JSON in `data/cache/extracted_controls/...`

2. **Processing / extraction**
   - External framework controls can be extracted from source PDFs (PageIndex-based flow) and cached for reuse.

3. **Mapping logic**
   - For each internal control, the mapper compares against the external safeguard catalog.
   - LLM assigns mapping outcomes and stores per-control JSON outputs.

4. **Validation / judge step**
   - Judge loop reviews mapper decisions, checks rationale quality/rule fit, and emits verdicts.
   - Outcomes are grouped as auto-approved, review-required, or quarantined.

5. **Output generation**
   - Review queues are built for human-in-the-loop handling of non-clean cases.
   - Final output builder generates:
     - `final_output.json`
     - `rejected_results.json`
     - `audit_trail.json`
     - `statistics.json`

---

## 5) Setup & Usage

### Prerequisites

- Python 3.10+
- Ollama installed and running
- A configured LLM model available in Ollama

### Clone and install

```bash
git clone https://github.com/<your-org>/ccf_mapper_3.0.git
cd ccf_mapper_3.0

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment setup

Create `.env` in the project root:

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
LLM_TEMPERATURE=0.1
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=
PAGEINDEX_API_KEY=your_pageindex_key_if_needed
```

Start Ollama:

```bash
ollama pull llama3.1:8b
ollama serve
```

### Run the pipeline

#### A) Mapping only

```bash
python -m src.pipeline
```

#### B) Mapping + judge

```bash
python -m src.pipeline --run-judge
```

#### C) Mapping + judge + human review session

```bash
python -m src.pipeline --run-judge --run-review --reviewer-name "<your-name>"
```

#### D) Build final output from completed review queue

```bash
python -m src.pipeline --build-final
```

#### E) Optional: limit run size for quick evaluation

```bash
python -m src.pipeline --run-judge --max-controls 50
```

---

## 6) Key Features

- **End-to-end automation**: Handles mapping, judging, review queue creation, and final artifact generation.
- **Resumable processing**: Per-control JSON outputs enable interruption-safe runs and incremental progress.
- **LLM-based quality gate**: Judge stage adds a second validation layer before human review.
- **Human-in-the-loop control**: Warning/quarantine cases are routed into an interactive review CLI.
- **Audit-ready outputs**: Produces traceable review decisions and final mapping statistics.
- **Practical scalability**: Designed to process larger control sets without fully manual review overhead.

---

## 7) Results / Performance

### Reported quality (after judge step on 50 controls)

- **62% exact match**
- **88% acceptable coverage**

### What these metrics mean

- **Exact match (62%)**: For 62% of controls, the automated result aligns exactly with expected mapping outcomes.
- **Acceptable coverage (88%)**: For 88% of controls, the output is either exact or practically acceptable with minimal/no correction.

In simple terms, most controls are already usable after automation, and only a smaller subset requires deeper human review.

---

## 8) Future Improvements

- Add benchmark scripts to auto-generate exact-match and coverage reports from test datasets.
- Expand external framework extraction support beyond the current dataset footprint.
- Introduce configurable policy/rule packs for domain-specific mapping standards.
- Add parallelized batch execution and runtime profiling for larger control inventories.
- Add CI checks for schema validation and output regression testing.

# Data Directory

This directory contains input and output data for the CCF Mapper.

## Structure

```
data/
├── input/          # Input files (requirements, controls)
├── output/         # Generated mapping outputs
└── cache/          # Cached page indexes and intermediate results
```

## Input Formats

### Requirements

- JSON: List of requirement objects
- CSV: Tabular requirement data
- PDF: Regulatory framework documents

### Controls

- JSON: List of control objects
- CSV: Tabular control data
- PDF: Internal control documentation

## Output Formats

- JSON: Structured mapping results
- CSV: Tabular mapping results for Excel/GRC systems
- Excel: Formatted workbook with multiple sheets

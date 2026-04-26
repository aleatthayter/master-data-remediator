# Master Data Remediator

An AI agent that reconciles equipment master data across SAP FLOC, AVEVA, drawing registers, PDF drawings, and CAD/DXF files — and proposes corrections for human approval.

## The Problem

Mining and energy operators maintain equipment tag data across multiple disconnected systems. The same physical asset can have different descriptions in SAP, AVEVA, and a drawing register, and no one system is authoritative. Inconsistent master data causes poor maintenance decisions, compliance gaps, and unreliable reporting.

## How It Works

1. **Ingests** data from up to five sources: SAP FLOC export, AVEVA metadata, drawing register CSV, PDF drawings (via Claude Vision), and DXF CAD files (via ezdxf)
2. **Compares** tag-by-tag across all sources and flags discrepancies
3. **Suggests** the most likely correct value using Claude, with Pydantic-structured output covering the proposed value, supporting sources, and reasoning
4. **Outputs** an Excel remediation report — no changes are applied without human sign-off

## Tech Stack

Python · Claude (Anthropic) · Pydantic · ezdxf · openpyxl

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
python agent/remediator.py
```

Output is written to `outputs/remediation_report.xlsx`.

## Data Sources

Place input files in `data/`:

| File | Format | Source |
|------|--------|--------|
| `floc_export.csv` | CSV | SAP FLOC |
| `aveva_export.csv` | CSV | AVEVA / SmartPlant |
| `drawing_register.csv` | CSV | Drawing management system |
| `drawings/` | PDF or PNG | Scanned P&IDs, equipment schedules |
| `cad/` | DXF | CAD drawing files |

Sources are optional — the agent compares across whichever are provided.

---

*Proof of concept. Production use would require additional work on governance, system integration, and change management.*

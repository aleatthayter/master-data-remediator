# Agent 1: Master Data Remediator

An AI agent that reconciles master data across engineering and operational 
systems in mining and energy companies.

## The Problem
Mining and energy companies maintain critical equipment data across multiple 
systems — SAP FLOC, AVEVA, engineering drawings, 3D models — which frequently 
fall out of sync. Inconsistent master data leads to poor maintenance decisions, 
compliance risk, and operational inefficiency.

## What This Agent Does
1. Ingests data from multiple source systems
2. Identifies discrepancies across sources
3. Uses AI to suggest the most likely correct value
4. Generates a report for human approval before any changes are applied

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Set your Anthropic API key: `export ANTHROPIC_API_KEY=your_key_here`
3. Run the agent: `python agent/remediator.py`
4. Review the output in `outputs/remediation_report.json`

## Data Sources Supported
- SAP FLOC data
- AVEVA / SmartPlant metadata
- Engineering drawing registers

## Note
This is a proof of concept. Production implementation would require 
additional work around governance, system integration, and change management.
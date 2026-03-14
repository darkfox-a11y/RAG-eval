# Legal Document RAG System - Evaluation Framework

## Overview
Automated evaluation system for testing a Legal Document Intelligence Platform (RAG-based Q&A system).

This evaluator is intentionally separate from the main application. It downloads public legal case text, generates a standard question set, calls the live API, and produces CSV/graph artifacts for a research workflow.

## Important Integration Notes
- The main application must be running before evaluation.
- The current app login endpoint expects JSON with `email` and `password`.
- The current app upload endpoint accepts `pdf`, `docx`, and `doc`, not plain `.txt`.
- To stay compatible without modifying the app, this evaluator downloads `.txt` source files and converts them to temporary `.docx` files during upload.

## Prerequisites
- Python 3.8+
- Main application running at `http://localhost:8000`
- Internet connection for downloading documents

## Installation
```bash
pip install -r requirements.txt
```

## Quick Start
```bash
chmod +x run_full_evaluation.sh
./run_full_evaluation.sh
```

## Manual Execution
```bash
python3 download_docs.py
python3 generate_questions.py
python3 test_rag_system.py
python3 generate_metrics.py
```

## Output Files
- `pdfs/` - Downloaded legal documents as text files
- `test_results/test_questions.json` - Generated question set
- `test_results/test_questions.csv` - Generated question set in CSV form
- `test_results/evaluation_results.csv` - Raw API evaluation results
- `test_results/metrics_summary.csv` - Aggregated performance metrics
- `test_results/graphs/` - Visualization graphs

## Configuration
Optional environment variables:

```bash
export LEGAL_EVAL_API_URL=http://localhost:8000
export LEGAL_EVAL_EMAIL=user@example.com
export LEGAL_EVAL_PASSWORD=password123
```

Edit script constants to customize:
- Number of documents
- Search queries
- Timeouts and delays

## Expected Runtime
- Download: ~5-10 minutes
- Question generation: under 1 minute
- Evaluation: ~15-20 minutes
- Metrics: under 1 minute
- Total: ~20-30 minutes

## Troubleshooting
- Ensure the main app is running: `curl http://localhost:8000`
- Check credentials if login fails
- Verify internet connectivity if downloads fail
- If fewer than 15 documents download, rerun later or adjust queries

## Citation
If using this evaluation framework in research, cite your paper here.

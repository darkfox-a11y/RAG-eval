#!/usr/bin/env python3
"""Generate a standardized question set for downloaded legal documents."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

PDFS_DIR = Path(os.getenv("LEGAL_EVAL_PDFS_DIR", "pdfs"))
METADATA_PATH = PDFS_DIR / "metadata.csv"
RESULTS_DIR = Path(os.getenv("LEGAL_EVAL_RESULTS_DIR", "test_results"))
QUESTIONS_JSON = RESULTS_DIR / "test_questions.json"
QUESTIONS_CSV = RESULTS_DIR / "test_questions.csv"
REQUIRED_COLUMNS = {"doc_id", "filename", "title", "source", "query", "length"}


def read_title(file_path: Path) -> str:
    """Extract the title from a downloaded text file."""
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("TITLE: "):
            return line.replace("TITLE: ", "", 1).strip()
    raise ValueError(f"Missing TITLE header in {file_path}")


def resolve_document_path(value: str) -> Path:
    """Resolve a metadata filename relative to the evaluator workspace."""
    candidate = Path(value)
    if candidate.exists():
        return candidate
    fallback = PDFS_DIR / candidate.name
    if fallback.exists():
        return fallback
    return candidate


def build_question_rows(doc_id: int, title: str) -> list[dict[str, object]]:
    """Build the five standard questions for one document."""
    return [
        {
            "doc_id": doc_id,
            "question": "What is the title or name of this document?",
            "expected_answer": title,
            "question_type": "factual",
        },
        {
            "doc_id": doc_id,
            "question": "What are the main parties involved in this case?",
            "expected_answer": "Extract from document",
            "question_type": "extraction",
        },
        {
            "doc_id": doc_id,
            "question": "What is the case number or reference number?",
            "expected_answer": "Extract from document",
            "question_type": "factual",
        },
        {
            "doc_id": doc_id,
            "question": "What is the main legal issue in this document?",
            "expected_answer": "Extract from document",
            "question_type": "analytical",
        },
        {
            "doc_id": doc_id,
            "question": "What orders or decisions were made in this case?",
            "expected_answer": "Extract from document",
            "question_type": "extraction",
        },
    ]


def main() -> int:
    """Generate JSON and CSV question artifacts."""
    if not METADATA_PATH.exists():
        print(f"❌ Error: missing metadata file at {METADATA_PATH}")
        return 1

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = pd.read_csv(METADATA_PATH)
    if not REQUIRED_COLUMNS.issubset(metadata.columns):
        print(f"❌ Error: metadata.csv missing columns {sorted(REQUIRED_COLUMNS)}")
        return 1

    questions: list[dict[str, object]] = []
    for row in metadata.to_dict(orient="records"):
        file_path = resolve_document_path(str(row["filename"]))
        if not file_path.exists():
            print(f"❌ Error: missing document file {file_path}")
            return 1
        print(f"📝 Generating questions for doc {row['doc_id']}...")
        title = read_title(file_path)
        questions.extend(build_question_rows(int(row["doc_id"]), title))

    QUESTIONS_JSON.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    pd.DataFrame(questions).to_csv(QUESTIONS_CSV, index=False, encoding="utf-8")
    print(f"✅ Generated {len(questions)} questions!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Exercise the live Legal Document Analyzer API with a fixed question set."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests
from docx import Document as DocxDocument

API_URL = os.getenv("LEGAL_EVAL_API_URL", "http://localhost:8000")
EMAIL = os.getenv("LEGAL_EVAL_EMAIL", "user@example.com")
PASSWORD = os.getenv("LEGAL_EVAL_PASSWORD", "password123")
MODEL_NAME = os.getenv("LEGAL_EVAL_MODEL_NAME", "")
TOP_K = int(os.getenv("LEGAL_EVAL_TOP_K", "3"))
METADATA_PATH = Path("pdfs/metadata.csv")
RESULTS_DIR = Path(os.getenv("LEGAL_EVAL_RESULTS_DIR", "test_results"))
QUESTIONS_PATH = RESULTS_DIR / "test_questions.csv"
RESULTS_PATH = RESULTS_DIR / "evaluation_results.csv"
REQUEST_TIMEOUT = 120
UPLOAD_DELAY_SECONDS = 2
QUERY_DELAY_SECONDS = 1
MAX_PROCESSING_WAIT_SECONDS = 60
REQUIRED_QUESTION_COLUMNS = {"doc_id", "question", "expected_answer", "question_type"}
REQUIRED_METADATA_COLUMNS = {"doc_id", "filename", "title", "source", "query", "length"}


def ensure_api_available(session: requests.Session) -> None:
    """Fail early if the main app is not reachable."""
    response = session.get(f"{API_URL}/", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()


def login(session: requests.Session) -> str:
    """Login with JSON credentials and return a bearer token."""
    payload = {"email": EMAIL, "password": PASSWORD}
    response = session.post(f"{API_URL}/auth/login", json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError("Login response did not include access_token")
    print("✅ Logged in successfully!")
    return token


def text_to_docx(source_path: Path) -> Path:
    """Convert a downloaded text file to DOCX for upload compatibility."""
    doc = DocxDocument()
    for line in source_path.read_text(encoding="utf-8").splitlines():
        doc.add_paragraph(line)
    temp_dir = Path(tempfile.gettempdir()) / "legal-paper-eval"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = temp_dir / f"{source_path.stem}.docx"
    doc.save(output_path)
    return output_path


def resolve_document_path(value: str) -> Path:
    """Resolve a metadata filename relative to the evaluator workspace."""
    candidate = Path(value)
    if candidate.exists():
        return candidate
    fallback = METADATA_PATH.parent / candidate.name
    if fallback.exists():
        return fallback
    return candidate


def upload_document(session: requests.Session, token: str, file_path: Path) -> int:
    """Upload one converted DOCX file and return the system document id."""
    headers = {"Authorization": f"Bearer {token}"}
    with file_path.open("rb") as handle:
        files = {
            "file": (
                file_path.name,
                handle,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        response = session.post(
            f"{API_URL}/documents/upload",
            headers=headers,
            files=files,
            timeout=REQUEST_TIMEOUT,
        )
    response.raise_for_status()
    document_id = response.json().get("id")
    if document_id is None:
        raise ValueError("Upload response did not include document id")
    print(f"✅ Uploaded: {file_path.name} → Document ID: {document_id}")
    return int(document_id)


def wait_for_processing(session: requests.Session, token: str, document_id: int) -> bool:
    """Poll until the uploaded document is ready or errors out."""
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + MAX_PROCESSING_WAIT_SECONDS
    while time.time() < deadline:
        response = session.get(
            f"{API_URL}/documents/{document_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        status = response.json().get("status")
        if status == "ready":
            print(f"✅ Document {document_id} ready!")
            return True
        if status == "error":
            print(f"❌ Document {document_id} error!")
            return False
        time.sleep(1)
    print(f"❌ Document {document_id} timed out!")
    return False


def ask_question(session: requests.Session, token: str, system_doc_id: int, question: str) -> dict[str, object]:
    """Send one question to the RAG API and capture latency and outputs."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "question": question,
        "document_id": system_doc_id,
        "top_k": TOP_K,
        "detail_level": "detailed",
    }
    if MODEL_NAME:
        params["model_name"] = MODEL_NAME
    started = time.time()
    try:
        response = session.post(
            f"{API_URL}/documents/ask",
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        latency_ms = (time.time() - started) * 1000
        response.raise_for_status()
        payload = response.json()
        return {
            "answer": payload.get("answer", ""),
            "confidence": payload.get("confidence", ""),
            "sources": payload.get("sources", []),
            "latency_ms": latency_ms,
            "success": True,
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.time() - started) * 1000
        return {
            "answer": f"ERROR: {exc}",
            "confidence": "error",
            "sources": [],
            "latency_ms": latency_ms,
            "success": False,
        }


def main() -> int:
    """Run the end-to-end API evaluation and save the raw results."""
    if not METADATA_PATH.exists() or not QUESTIONS_PATH.exists():
        print("❌ Error: required input files are missing. Run download_docs.py and generate_questions.py first.")
        return 1

    metadata = pd.read_csv(METADATA_PATH)
    questions = pd.read_csv(QUESTIONS_PATH)
    if not REQUIRED_METADATA_COLUMNS.issubset(metadata.columns):
        print(f"❌ Error: metadata.csv missing columns {sorted(REQUIRED_METADATA_COLUMNS)}")
        return 1
    if not REQUIRED_QUESTION_COLUMNS.issubset(questions.columns):
        print(f"❌ Error: test_questions.csv missing columns {sorted(REQUIRED_QUESTION_COLUMNS)}")
        return 1

    print("🚀 Starting RAG System Evaluation")
    session = requests.Session()
    try:
        ensure_api_available(session)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Error: API is not reachable at {API_URL}: {exc}")
        return 1

    try:
        token = login(session)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Error: login failed: {exc}")
        return 1

    doc_id_mapping: dict[int, int] = {}
    print(f"📤 Uploading {len(metadata)} documents...")
    if MODEL_NAME:
        print(f"🧠 Using model: {MODEL_NAME}")
    print(f"🔎 Retrieval top_k: {TOP_K}")
    for index, row in enumerate(metadata.to_dict(orient='records'), start=1):
        source_file = resolve_document_path(str(row["filename"]))
        print(f"Processing {index}/{len(metadata)} documents...")
        try:
            upload_file = text_to_docx(source_file)
            system_doc_id = upload_document(session, token, upload_file)
            if wait_for_processing(session, token, system_doc_id):
                doc_id_mapping[int(row["doc_id"])] = system_doc_id
            time.sleep(UPLOAD_DELAY_SECONDS)
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Error: failed to upload doc {row['doc_id']}: {exc}")

    if not doc_id_mapping:
        print("❌ Error: no documents were uploaded successfully")
        return 1

    results: list[dict[str, object]] = []
    question_rows = questions.to_dict(orient="records")
    print(f"🧪 Running {len(question_rows)} test queries...")
    for index, row in enumerate(question_rows, start=1):
        print(f"Query {index}/{len(question_rows)}: {row['question'][:50]}...")
        source_doc_id = int(row["doc_id"])
        system_doc_id = doc_id_mapping.get(source_doc_id)
        if system_doc_id is None:
            results.append(
                {
                    "doc_id": source_doc_id,
                    "sys_doc_id": "",
                    "model_name": MODEL_NAME or "default",
                    "question": row["question"],
                    "question_type": row["question_type"],
                    "expected_answer": row["expected_answer"],
                    "actual_answer": "ERROR: document upload failed",
                    "confidence": "error",
                    "latency_ms": 0.0,
                    "num_sources": 0,
                    "success": False,
                }
            )
            continue

        answer = ask_question(session, token, system_doc_id, str(row["question"]))
        results.append(
            {
                "doc_id": source_doc_id,
                "sys_doc_id": system_doc_id,
                "model_name": MODEL_NAME or "default",
                "question": row["question"],
                "question_type": row["question_type"],
                "expected_answer": row["expected_answer"],
                "actual_answer": answer["answer"],
                "confidence": answer["confidence"],
                "latency_ms": answer["latency_ms"],
                "num_sources": len(answer["sources"]),
                "success": answer["success"],
            }
        )
        time.sleep(QUERY_DELAY_SECONDS)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(RESULTS_PATH, index=False, encoding="utf-8")

    success_rate = 100.0 * pd.DataFrame(results)["success"].mean()
    if success_rate < 80:
        print(f"❌ Warning: success rate is below 80% ({success_rate:.1f}%)")
    print("✅ Evaluation complete!")
    print(f"📊 Results saved to: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

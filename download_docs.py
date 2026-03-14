#!/usr/bin/env python3
"""Download a curated public legal-document corpus for evaluation."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

NUM_DOCS = 10
REQUEST_TIMEOUT = 10
DOWNLOAD_DELAY_SECONDS = 2
PDFS_DIR = Path("pdfs")
METADATA_PATH = PDFS_DIR / "metadata.csv"

LEGAL_SOURCES = [
    {
        "title": "Google Terms of Service",
        "url": "https://policies.google.com/terms",
        "query": "terms",
    },
    {
        "title": "Google Privacy Policy",
        "url": "https://policies.google.com/privacy",
        "query": "privacy",
    },
    {
        "title": "Anthropic Consumer Terms",
        "url": "https://www.anthropic.com/legal/consumer-terms",
        "query": "terms",
    },
    {
        "title": "Anthropic Commercial Terms",
        "url": "https://www.anthropic.com/legal/commercial-terms",
        "query": "commercial",
    },
    {
        "title": "Anthropic Privacy Policy",
        "url": "https://www.anthropic.com/legal/privacy",
        "query": "privacy",
    },
    {
        "title": "GitHub Terms of Service",
        "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
        "query": "terms",
    },
    {
        "title": "GitHub General Privacy Statement",
        "url": "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
        "query": "privacy",
    },
    {
        "title": "Cloudflare Self-Serve Subscription Agreement",
        "url": "https://www.cloudflare.com/service-specific-terms-application-services/",
        "query": "subscription",
    },
    {
        "title": "Slack Terms of Service",
        "url": "https://slack.com/terms-of-service",
        "query": "terms",
    },
    {
        "title": "Mozilla Firefox Terms of Use",
        "url": "https://www.mozilla.org/en-US/about/legal/terms/firefox/",
        "query": "terms",
    },
    {
        "title": "Mozilla Privacy Notice",
        "url": "https://www.mozilla.org/en-US/privacy/websites/",
        "query": "privacy",
    },
    {
        "title": "Dropbox Service Agreement",
        "url": "https://www.dropbox.com/terms",
        "query": "terms",
    },
    {
        "title": "Dropbox Privacy Policy",
        "url": "https://www.dropbox.com/privacy",
        "query": "privacy",
    },
    {
        "title": "Atlassian Cloud Terms of Service",
        "url": "https://www.atlassian.com/legal/cloud-terms-of-service",
        "query": "terms",
    },
    {
        "title": "Atlassian Privacy Policy",
        "url": "https://www.atlassian.com/legal/privacy-policy",
        "query": "privacy",
    },
]


def fetch_html(session: requests.Session, url: str) -> BeautifulSoup:
    """Fetch one HTML page and parse it with BeautifulSoup."""
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def strip_unwanted_nodes(soup: BeautifulSoup) -> None:
    """Remove script-like and nav/footer content before text extraction."""
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    for selector in ["header", "footer", "nav", "aside", "[role='navigation']"]:
        for node in soup.select(selector):
            node.decompose()


def candidate_nodes(soup: BeautifulSoup) -> Iterable:
    """Yield likely main-content containers in priority order."""
    selectors = [
        "main",
        "article",
        "[role='main']",
        ".content",
        ".main-content",
        ".policy",
        ".policy-content",
        ".docs-content",
        ".markdown-body",
        "body",
    ]
    seen: set[int] = set()
    for selector in selectors:
        for node in soup.select(selector):
            marker = id(node)
            if marker in seen:
                continue
            seen.add(marker)
            yield node


def extract_document_text(soup: BeautifulSoup) -> str:
    """Extract long-form readable text from a legal/policy web page."""
    strip_unwanted_nodes(soup)
    for node in candidate_nodes(soup):
        text = node.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.splitlines() if line.strip())
        if len(text) >= 1000:
            return text
    raise ValueError("Could not find a main content block with enough text")


def save_document_text(doc_id: int, title: str, source_url: str, query: str, text: str) -> dict[str, object]:
    """Persist one legal document and return its metadata row."""
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    filename = PDFS_DIR / f"doc_{doc_id:02d}.txt"
    payload = (
        f"TITLE: {title}\n"
        f"SOURCE: {source_url}\n"
        f"QUERY: {query}\n"
        f"{'=' * 80}\n\n"
        f"{text}\n"
    )
    filename.write_text(payload, encoding="utf-8")
    return {
        "doc_id": doc_id,
        "filename": str(filename),
        "title": title,
        "source": source_url,
        "query": query,
        "length": len(payload),
    }


def main() -> int:
    """Download up to NUM_DOCS curated public legal documents."""
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "legal-paper-eval/1.0"})

    rows: list[dict[str, object]] = []
    failures: list[str] = []
    min_required = min(10, NUM_DOCS)

    for source in LEGAL_SOURCES[:NUM_DOCS]:
        print(f"🔍 Fetching: {source['title']}")
        try:
            soup = fetch_html(session, source["url"])
            text = extract_document_text(soup)
            row = save_document_text(
                len(rows) + 1,
                source["title"],
                source["url"],
                source["query"],
                text,
            )
            rows.append(row)
            print(f"✅ Saved as: {row['filename']}")
            time.sleep(DOWNLOAD_DELAY_SECONDS)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{source['title']}: {exc}")
            print(f"❌ Error: {exc}")

    if len(rows) < min_required:
        print(f"❌ Error: downloaded only {len(rows)} documents; at least {min_required} are required")
        for failure in failures:
            print(f"❌ Failure detail: {failure}")
        return 1

    pd.DataFrame(rows).to_csv(METADATA_PATH, index=False, encoding="utf-8")
    print(f"✅ Downloaded {len(rows)} documents!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

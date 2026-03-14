#!/usr/bin/env python3
"""Calculate evaluation metrics and generate publication-quality graphs."""

from __future__ import annotations

import sys
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS_DIR = Path(os.getenv("LEGAL_EVAL_RESULTS_DIR", "test_results"))
RESULTS_PATH = RESULTS_DIR / "evaluation_results.csv"
METRICS_PATH = RESULTS_DIR / "metrics_summary.csv"
GRAPHS_DIR = RESULTS_DIR / "graphs"
REQUIRED_COLUMNS = {
    "doc_id",
    "sys_doc_id",
    "question",
    "question_type",
    "expected_answer",
    "actual_answer",
    "confidence",
    "latency_ms",
    "num_sources",
    "success",
}


def pct(series: pd.Series, value: str) -> float:
    """Return the percentage of rows equal to a given value."""
    return 100.0 * (series.fillna("").str.lower() == value).mean()


def build_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Compute overall, latency, confidence, and per-question-type metrics."""
    metrics: dict[str, float] = {
        "total_queries": int(len(df)),
        "success_rate": 100.0 * df["success"].mean(),
        "avg_sources_retrieved": float(df["num_sources"].mean()),
        "latency_mean": float(df["latency_ms"].mean()),
        "latency_median": float(df["latency_ms"].median()),
        "latency_p95": float(np.percentile(df["latency_ms"], 95)),
        "latency_p99": float(np.percentile(df["latency_ms"], 99)),
        "latency_min": float(df["latency_ms"].min()),
        "latency_max": float(df["latency_ms"].max()),
        "high_confidence_pct": pct(df["confidence"], "high"),
        "medium_confidence_pct": pct(df["confidence"], "medium"),
        "low_confidence_pct": pct(df["confidence"], "low"),
    }

    for question_type in sorted(df["question_type"].dropna().unique()):
        subset = df[df["question_type"] == question_type]
        metrics[f"{question_type}_success_rate"] = 100.0 * subset["success"].mean()
        metrics[f"{question_type}_latency"] = float(subset["latency_ms"].mean())
    return metrics


def plot_latency_distribution(df: pd.DataFrame) -> None:
    """Create a histogram of latency with mean and median markers."""
    plt.figure(figsize=(9, 5))
    plt.hist(df["latency_ms"], bins=20, edgecolor="black", alpha=0.8)
    mean_value = df["latency_ms"].mean()
    median_value = df["latency_ms"].median()
    plt.axvline(mean_value, color="red", linestyle="--", label=f"Mean: {mean_value:.0f} ms")
    plt.axvline(median_value, color="green", linestyle="--", label=f"Median: {median_value:.0f} ms")
    plt.title("Query Latency Distribution")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / "latency_distribution.png", dpi=300)
    plt.close()


def plot_confidence_distribution(df: pd.DataFrame) -> None:
    """Create a bar chart of confidence labels."""
    counts = df["confidence"].fillna("unknown").str.lower().value_counts()
    ordered = [counts.get(level, 0) for level in ["high", "medium", "low"]]
    plt.figure(figsize=(7, 5))
    plt.bar(["high", "medium", "low"], ordered, color=["#2e8b57", "#f4a261", "#c0392b"])
    plt.title("Answer Confidence Distribution")
    plt.xlabel("Confidence Level")
    plt.ylabel("Count")
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / "confidence_distribution.png", dpi=300)
    plt.close()


def plot_performance_by_type(df: pd.DataFrame) -> None:
    """Create side-by-side plots for success rate and latency by question type."""
    grouped = df.groupby("question_type", dropna=True)
    labels = list(grouped.size().index)
    success_rates = [100.0 * grouped.get_group(label)["success"].mean() for label in labels]
    latencies = [grouped.get_group(label)["latency_ms"].mean() for label in labels]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].bar(labels, success_rates, color="#457b9d")
    axes[0].set_ylim(0, 100)
    axes[0].set_title("Success Rate by Question Type")
    axes[0].set_ylabel("Success Rate (%)")
    axes[1].bar(labels, latencies, color="orange")
    axes[1].set_title("Latency by Question Type")
    axes[1].set_ylabel("Avg Latency (ms)")
    for axis in axes:
        axis.set_xlabel("Question Type")
        axis.tick_params(axis="x", rotation=15)
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / "performance_by_type.png", dpi=300)
    plt.close()


def print_report(metrics: dict[str, float]) -> None:
    """Print a formatted summary report to the console."""
    print("=" * 80)
    print("RAG SYSTEM EVALUATION REPORT")
    print("📊 OVERALL PERFORMANCE")
    print("─" * 76)
    print(f"Total Queries:          {int(metrics['total_queries'])}")
    print(f"Success Rate:           {metrics['success_rate']:.1f}%")
    print(f"Avg Sources Retrieved:  {metrics['avg_sources_retrieved']:.1f}")
    print("⏱️  LATENCY STATISTICS (milliseconds)")
    print("─" * 76)
    print(f"Mean:      {metrics['latency_mean']:.0f} ms")
    print(f"Median:    {metrics['latency_median']:.0f} ms")
    print(f"P95:       {metrics['latency_p95']:.0f} ms")
    print(f"P99:       {metrics['latency_p99']:.0f} ms")
    print(f"Min:       {metrics['latency_min']:.0f} ms")
    print(f"Max:       {metrics['latency_max']:.0f} ms")
    print("🎯 CONFIDENCE DISTRIBUTION")
    print("─" * 76)
    print(f"High:      {metrics['high_confidence_pct']:.1f}%")
    print(f"Medium:    {metrics['medium_confidence_pct']:.1f}%")
    print(f"Low:       {metrics['low_confidence_pct']:.1f}%")
    print("📝 PERFORMANCE BY QUESTION TYPE")
    print("─" * 76)
    for question_type in ["factual", "extraction", "analytical"]:
        success_key = f"{question_type}_success_rate"
        latency_key = f"{question_type}_latency"
        if success_key in metrics:
            print(
                f"{question_type.title():<14} Success: {metrics[success_key]:5.1f}%"
                f"  |  Latency: {metrics[latency_key]:6.0f} ms"
            )
    print("=" * 80)


def main() -> int:
    """Load raw results, compute summary metrics, and save plots."""
    if not RESULTS_PATH.exists():
        print(f"❌ Error: missing evaluation results at {RESULTS_PATH}")
        return 1

    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RESULTS_PATH)
    if not REQUIRED_COLUMNS.issubset(df.columns):
        print(f"❌ Error: evaluation_results.csv missing columns {sorted(REQUIRED_COLUMNS)}")
        return 1

    df["success"] = df["success"].astype(bool)
    df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce").fillna(0.0)
    df["num_sources"] = pd.to_numeric(df["num_sources"], errors="coerce").fillna(0.0)

    print("📊 Calculating metrics...")
    metrics = build_metrics(df)
    pd.DataFrame([metrics]).to_csv(METRICS_PATH, index=False, encoding="utf-8")

    print("📈 Generating graphs...")
    plot_latency_distribution(df)
    plot_confidence_distribution(df)
    plot_performance_by_type(df)

    if metrics["success_rate"] < 80:
        print(f"❌ Warning: success rate below target at {metrics['success_rate']:.1f}%")
    if metrics["latency_mean"] > 3000:
        print(f"❌ Warning: average latency above target at {metrics['latency_mean']:.0f} ms")

    print_report(metrics)
    print("✅ Report generated!")
    print(f"📊 Metrics saved to: {METRICS_PATH}")
    print(f"📈 Graphs saved to: {GRAPHS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

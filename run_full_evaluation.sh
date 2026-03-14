#!/usr/bin/env bash
set -euo pipefail

echo "🚀 COMPLETE RAG SYSTEM EVALUATION"
echo

echo "Step 1/4: Downloading legal documents..."
python3 download_docs.py || { echo "❌ Step 1 failed!"; exit 1; }
echo

echo "Step 2/4: Generating test questions..."
python3 generate_questions.py || { echo "❌ Step 2 failed!"; exit 1; }
echo

echo "Step 3/4: Testing RAG system (this may take a while)..."
python3 test_rag_system.py || { echo "❌ Step 3 failed!"; exit 1; }
echo

echo "Step 4/4: Generating metrics report..."
python3 generate_metrics.py || { echo "❌ Step 4 failed!"; exit 1; }
echo

echo "✅ COMPLETE!"
echo "📊 Results:"
echo "- Evaluation results: test_results/evaluation_results.csv"
echo "- Metrics summary:    test_results/metrics_summary.csv"
echo "- Graphs:             test_results/graphs/"

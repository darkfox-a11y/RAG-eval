# Evaluation Comparison - 2026-03-14

## Runs

- Baseline: `test_results/run_10docs_20260314`
- Optimized Gemini 2.5: `test_results/run_10docs_optimized_gemini25_20260314`

## Summary Table

| Metric | Baseline 10 Docs | Optimized Gemini 2.5 |
| --- | ---: | ---: |
| Total queries | 50 | 50 |
| Success rate | 100.0% | 100.0% |
| Avg sources retrieved | 5.0 | 3.0 |
| Mean latency | 3998 ms | 2954 ms |
| Median latency | 3756 ms | 2968 ms |
| P95 latency | 6437 ms | 3578 ms |
| P99 latency | 7606 ms | 3849 ms |
| High confidence | 18.0% | 76.0% |
| Medium confidence | 82.0% | 24.0% |
| Low confidence | 0.0% | 0.0% |
| Factual latency | 2607 ms | 2738 ms |
| Extraction latency | 4677 ms | 2978 ms |
| Analytical latency | 5421 ms | 3340 ms |

## Interpretation

- Confidence improved substantially: `18.0%` high confidence to `76.0%`
- Overall mean latency improved: `3998 ms` to `2954 ms`
- Tail latency improved significantly: P95 and P99 were both reduced by roughly 40% or more
- Retrieval depth fell from `5` sources to `3`, which likely contributed to both speed and answer directness
- Analytical questions improved the most on latency

## Current Recommendation

Use the optimized configuration with:

- `top_k = 3`
- smaller chunking (`300 / 50`)
- shorter, question-type-aware prompts
- `gemini-2.5-flash`

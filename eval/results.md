# Evaluation Results — Faculty Research Discovery Assistant

## Retrieval Configuration Comparison

| Configuration | P@5 | R@10 | MRR | nDCG@10 |
|---------------|-----|------|-----|---------|
| BM25-only | 0.8222 | 0.7301 | 0.7778 | 0.806 |
| Vector-only | 0.9111 | 0.8107 | 0.9444 | 0.8918 |
| Hybrid (RRF) | 0.9111 | 0.7475 | 0.8889 | 0.8773 |
| Hybrid + LLM Rerank ✓ | 0.9111 | 0.569 | 0.8889 | 0.9567 |

## Notes

- **P@5**: Precision at rank 5 — what fraction of top-5 results are truly relevant.
- **R@10**: Recall at rank 10 — what fraction of all relevant faculty were retrieved in top 10.
- **MRR**: Mean Reciprocal Rank — where does the first relevant result appear.
- **nDCG@10**: Normalized Discounted Cumulative Gain — accounts for graded relevance (0-3 scale).

- **BM25** is strong on exact keyword matches (faculty names, acronyms).
- **Vector** captures semantic similarity and synonyms.
- **Hybrid (RRF)** merges both lists robustly — no score normalization needed.
- **Hybrid + LLM Rerank** uses Gemini/Groq to re-score top-30 passages for the best final ordering.
  The LLM reranker reads the query and each passage together and outputs a relevance score,
  giving the most accurate final ranking at the cost of an API call.

*Generated: 2026-10-03 14:31*
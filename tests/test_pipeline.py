"""Test the full pipeline directly (no HTTP)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("[test] Loading pipeline...")
from retrieval.pipeline import search

print("[test] Running search: 'machine learning'")
result = search("machine learning", filters={})
print(f"[test] Status: {result['status']}")
print(f"[test] Results: {len(result['results'])}")
if result['results']:
    r = result['results'][0]
    print(f"[test] Top result: {r['display_name']} (basis={r['expertise_basis']}, score={r['score']})")
    print(f"[test] Stated evidence: {len(r['stated_evidence'])}")
    print(f"[test] Inferred evidence: {len(r['inferred_evidence'])}")
print("[test] DONE")

"""
scripts/run_ingest.py — Master ingestion script.
Run: python scripts/run_ingest.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.canonical import build_canonical
from ingest.chunk import build_chunks
from ingest.build_index import main as build_index

if __name__ == "__main__":
    print("=" * 60)
    print("FACULTY RESEARCH DISCOVERY ASSISTANT — Ingest Pipeline")
    print("=" * 60)

    print("\n[1/3] Building canonical faculty records...")
    canonical, needs_review, has_synthetic = build_canonical(
        "data/raw/info.json",
        "data/processed/faculty.json",
        "data/processed/needs_review.json"
    )
    if has_synthetic:
        print("  [!] Synthetic data detected - UI footer will show notice")

    print("\n[2/3] Chunking faculty records...")
    chunks = build_chunks("data/processed/faculty.json", "data/processed/chunks.json")

    print("\n[3/3] Building BM25 + FAISS indexes...")
    build_index()

    print("\n" + "=" * 60)
    print("DONE! Ingest complete!")
    print(f"   * {len(canonical)} faculty records")
    print(f"   * {len(chunks)} chunks indexed")
    print(f"   * {len(needs_review)} pairs flagged for review")
    print("=" * 60)
    print("\nNext: python scripts/run_server.py")

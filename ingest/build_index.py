# ingest/build_index.py
# Builds BM25 and FAISS indexes from chunks.json.
# Run: python -m ingest.build_index

import json
import pickle
import numpy as np
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import faiss
import yaml

def _load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_bm25(chunks: list[dict], out_dir: Path):
    """Tokenize chunk texts and build BM25 index."""
    texts = [c["text"] for c in chunks]
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "bm25.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "chunk_ids": [c["chunk_id"] for c in chunks]}, f)
    print(f"[index] BM25 built over {len(chunks)} chunks")
    return bm25

def build_faiss(chunks: list[dict], model_name: str, out_dir: Path):
    """Embed chunk texts and build FAISS flat-IP index."""
    model = SentenceTransformer(model_name)
    texts = [c["text"] for c in chunks]

    print(f"[index] Embedding {len(texts)} chunks with {model_name}...")
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    out_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_dir / "faiss.index"))

    # Save mapping: faiss position -> chunk_id
    with open(out_dir / "faiss_map.json", "w", encoding="utf-8") as f:
        json.dump([c["chunk_id"] for c in chunks], f)

    # Save embeddings for later
    np.save(str(out_dir / "embeddings.npy"), embeddings)

    print(f"[index] FAISS index built: {dim}d, {len(chunks)} vectors")
    return index

def main():
    cfg = _load_config()
    data_cfg = cfg["data"]
    model_name = cfg["models"]["embedder"]

    chunks_path = Path(data_cfg["processed_dir"]) / "chunks.json"
    index_dir = Path(data_cfg["index_dir"])

    if not chunks_path.exists():
        print(f"[index] chunks.json not found at {chunks_path}. Run build pipeline first.")
        return

    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"[index] Loaded {len(chunks)} chunks")

    build_bm25(chunks, index_dir)
    build_faiss(chunks, model_name, index_dir)

    # Save chunk lookup
    chunk_lookup = {c["chunk_id"]: c for c in chunks}
    with open(index_dir / "chunk_lookup.json", "w", encoding="utf-8") as f:
        json.dump(chunk_lookup, f, ensure_ascii=False)

    print("[index] Done. Index files written to", index_dir)

if __name__ == "__main__":
    main()

"""scripts/run_server.py — Start FastAPI server"""
import sys, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    from retrieval.pipeline import _load_indexes, _get_embedder
    print("[run_server] Preloading indexes and embedder...")
    _load_indexes()
    _get_embedder()
    print("[run_server] Retrieval models loaded. Starting server on http://127.0.0.1:8000 ...")

    import uvicorn
    try:
        uvicorn.run("api.main:app", host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        traceback.print_exc()


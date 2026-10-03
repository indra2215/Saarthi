# retrieval/pipeline.py
# Orchestrates BM25 -> Vector -> RRF -> Cross-encoder -> Evidence classification

import warnings
warnings.filterwarnings("ignore")
import json
import time
import pickle
import numpy as np
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz
import yaml

_cfg = None
_bm25_data = None
_faiss_index = None
_faiss_id_map = None
_chunk_lookup = None
_faculty_lookup = None
_embedder = None
_reranker = None

def _load_config():
    global _cfg
    if _cfg is None:
        with open(Path(__file__).parent.parent / "config.yaml", encoding="utf-8") as f:
            _cfg = yaml.safe_load(f)
    return _cfg

def _load_indexes():
    global _bm25_data, _faiss_index, _chunk_lookup, _faculty_lookup
    cfg = _load_config()
    idx_dir = Path(cfg["data"]["index_dir"])

    if _bm25_data is None:
        with open(idx_dir / "bm25.pkl", "rb") as f:
            _bm25_data = pickle.load(f)

    if _faiss_index is None:
        import faiss
        global _faiss_id_map
        _faiss_index = faiss.read_index(str(idx_dir / "faiss.index"))
        with open(idx_dir / "faiss_map.json", encoding="utf-8") as f:
            _faiss_id_map = json.load(f)

    if _chunk_lookup is None:
        with open(idx_dir / "chunk_lookup.json", encoding="utf-8") as f:
            _chunk_lookup = json.load(f)

    if _faculty_lookup is None:
        fac_path = Path(cfg["data"]["processed_dir"]) / "faculty.json"
        with open(fac_path, encoding="utf-8") as f:
            facs = json.load(f)
        _faculty_lookup = {f["faculty_id"]: f for f in facs}

def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        cfg = _load_config()
        _embedder = SentenceTransformer(cfg["models"]["embedder"])
    return _embedder

def _get_reranker():
    """Return 'llm' string — we use Gemini/Groq API for reranking, no local model."""
    return "llm"

# ─── LLM-based reranker helpers ──────────────────────────────────────────────

def _llm_rerank_scores(query: str, passages: list[tuple[str, str]]) -> list[float]:
    """
    Use Gemini or Groq to score passages for relevance to the query.
    Returns a list of scores (0.0-1.0) for each passage.
    Falls back to uniform scores on failure.
    """
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    cfg = _load_config()
    llm_cfg = cfg.get("llm", {})
    keys = cfg.get("api_keys", {})
    gemini_keys = [k for k in keys.get("gemini", []) if k]
    if os.environ.get("GEMINI_API_KEY"):
        gemini_keys.insert(0, os.environ["GEMINI_API_KEY"])
    groq_keys = [k for k in keys.get("groq", []) if k]
    if os.environ.get("GROQ_API_KEY"):
        groq_keys.insert(0, os.environ["GROQ_API_KEY"])

    fallback_order = llm_cfg.get("fallback_order", ["gemini", "groq", "template"])

    # Build a compact prompt for scoring
    passage_list = ""
    for i, (cid, text) in enumerate(passages):
        # Truncate text to save tokens
        short = text[:300].replace("\n", " ")
        passage_list += f"\nP{i}: {short}"

    prompt = (
        f"Rate each passage's relevance to the query on a 0-10 scale.\n"
        f"Query: \"{query}\"\n"
        f"Passages:{passage_list}\n\n"
        f"Return ONLY a JSON array of numbers, one per passage, e.g. [8, 3, 7, ...]. "
        f"No text, no explanation, just the array."
    )

    for provider in fallback_order:
        if provider == "template":
            break
        try:
            if provider == "gemini":
                import google.generativeai as genai
                for key in gemini_keys:
                    try:
                        genai.configure(api_key=key)
                        model = genai.GenerativeModel(llm_cfg.get("gemini_model", "gemini-1.5-flash"))
                        resp = model.generate_content(prompt)
                        scores = json.loads(resp.text.strip().strip("`").replace("json", "").strip())
                        if isinstance(scores, list) and len(scores) == len(passages):
                            return [max(0.0, min(1.0, s / 10.0)) for s in scores]
                    except Exception:
                        continue

            elif provider == "groq":
                from groq import Groq
                for key in groq_keys:
                    try:
                        client = Groq(api_key=key)
                        resp = client.chat.completions.create(
                            model=llm_cfg.get("groq_model", "llama3-8b-8192"),
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=200,
                            temperature=0,
                        )
                        text = resp.choices[0].message.content.strip().strip("`").replace("json", "").strip()
                        scores = json.loads(text)
                        if isinstance(scores, list) and len(scores) == len(passages):
                            return [max(0.0, min(1.0, s / 10.0)) for s in scores]
                    except Exception:
                        continue
        except Exception:
            continue

    # Fallback: linearly decreasing scores based on RRF position
    return [max(0.1, 1.0 - i * 0.05) for i in range(len(passages))]

# ─── Filters ─────────────────────────────────────────────────────────────────

def _apply_filters(chunk_ids: list[str], filters: dict) -> list[str]:
    if not filters:
        return chunk_ids
    result = []
    for cid in chunk_ids:
        c = _chunk_lookup.get(cid)
        if not c:
            continue
        if filters.get("department") and c.get("department") != filters["department"]:
            continue
        if filters.get("year_from") and c.get("year") and c["year"] < filters["year_from"]:
            continue
        if filters.get("year_to") and c.get("year") and c["year"] > filters["year_to"]:
            continue
        if filters.get("source_type") and c.get("source_type") != filters["source_type"]:
            continue
        if filters.get("evidence_type") and c.get("evidence_type") != filters["evidence_type"]:
            continue
        result.append(cid)
    return result

# ─── BM25 ─────────────────────────────────────────────────────────────────────

def bm25_search(query: str, top_k: int = 50, filters: dict = None) -> list[str]:
    _load_indexes()
    tokens = query.lower().split()
    scores = _bm25_data["bm25"].get_scores(tokens)
    chunk_ids = _bm25_data["chunk_ids"]
    ranked = sorted(zip(chunk_ids, scores), key=lambda x: x[1], reverse=True)
    top = [cid for cid, _ in ranked[:top_k * 3]]  # over-fetch for filters
    if filters:
        top = _apply_filters(top, filters)
    return top[:top_k]

# ─── Vector ──────────────────────────────────────────────────────────────────

def vector_search(query: str, top_k: int = 50, filters: dict = None) -> list[str]:
    _load_indexes()
    model = _get_embedder()
    q_emb = model.encode([query], normalize_embeddings=True).astype(np.float32)
    D, I = _faiss_index.search(q_emb, top_k * 3)
    id_map = _faiss_id_map
    ranked = [id_map[i] for i in I[0] if i < len(id_map)]
    if filters:
        ranked = _apply_filters(ranked, filters)
    return ranked[:top_k]

# ─── RRF ─────────────────────────────────────────────────────────────────────

def rrf(ranked_lists: list[list[str]], k: int = 60, top_n: int = 30) -> list[str]:
    scores = {}
    for lst in ranked_lists:
        for rank, cid in enumerate(lst, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)[:top_n]

# ─── LLM-powered rerank (replaces cross-encoder) ─────────────────────────────

def rerank(query: str, chunk_ids: list[str], top_n: int = 10) -> list[tuple[str, float]]:
    valid = [(cid, _chunk_lookup[cid]["text"]) for cid in chunk_ids if cid in _chunk_lookup]
    if not valid:
        return []
    scores = _llm_rerank_scores(query, valid)
    ranked = sorted(zip([cid for cid, _ in valid], scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]

# ─── Evidence classification ─────────────────────────────────────────────────

FACULTY_AUTHORED = {"PROFILE_KEYWORDS", "PROFILE_BIO", "PROJECT_DESC"}

def _names_topic(text: str, query_topics: list[str]) -> bool:
    """True only if the topic is EXPLICITLY named in faculty-authored text."""
    text_l = text.lower()
    for topic in query_topics:
        if topic.lower() in text_l:
            return True
    return False

def _match_mode(chunk: dict, query_topics: list[str]) -> str:
    """LEXICAL if topic word appears literally; SEMANTIC otherwise."""
    for topic in query_topics:
        if topic.lower() in (chunk.get("raw_text") or chunk.get("text","")).lower():
            return "LEXICAL"
    return "SEMANTIC"

def build_evidence(reranked: list[tuple[str, float]], query_topics: list[str], threshold: float = 0.0):
    """Group reranked chunks by faculty_id and compute expertise_basis."""
    from collections import defaultdict
    by_fac = defaultdict(list)
    for cid, score in reranked:
        chunk = _chunk_lookup.get(cid)
        if not chunk:
            continue
        chunk = dict(chunk)
        chunk["rerank_score"] = float(score)
        by_fac[chunk["faculty_id"]].append(chunk)

    results = []
    for fid, chunks in by_fac.items():
        fac = _faculty_lookup.get(fid, {})

        stated = [c for c in chunks
                  if c["source_type"] in FACULTY_AUTHORED
                  and _names_topic(c["text"], query_topics)]

        inferred = [c for c in chunks
                    if c["source_type"] == "PUBLICATION"
                    and c["rerank_score"] >= threshold]

        if not stated and not inferred:
            # Include anything above very low bar
            inferred = chunks[:3]

        if stated and inferred:
            basis = "BOTH"
        elif stated:
            basis = "STATED"
        else:
            basis = "INFERRED"

        # faculty score = max of top 3 chunk scores
        all_scores = [c["rerank_score"] for c in chunks]
        top3 = sorted(all_scores, reverse=True)[:3]
        fac_score = max(top3) if top3 else 0.0

        stated_evidence = [
            {"source_type": c["source_type"], "passage": c["raw_text"] or c["text"], "url": c.get("url")}
            for c in stated
        ]
        inferred_evidence = [
            {
                "passage": c["raw_text"] or c["text"],
                "source_title": (c.get("pub_id") or c.get("project_id") or "Unknown"),
                "year": c.get("year"),
                "url": c.get("url"),
                "match_mode": _match_mode(c, query_topics),
                "score": round(c["rerank_score"], 4),
            }
            for c in inferred
        ]

        label_map = {"STATED": "Stated expertise", "INFERRED": "Inferred from publications", "BOTH": "Stated + publications"}

        results.append({
            "faculty_id": fid,
            "display_name": fac.get("faculty_name", fid),
            "department": fac.get("department", ""),
            "department_code": fac.get("department_code", ""),
            "designation": fac.get("designation", ""),
            "qualification": fac.get("qualification", ""),
            "email": fac.get("email"),
            "linkedin_url": (fac.get("linkedin") or {}).get("profile_url"),
            "scholar_url": (fac.get("google_scholar") or {}).get("profile_url"),
            "primary_domain": fac.get("primary_domain", ""),
            "research_areas": fac.get("research_areas", []),
            "score": round(fac_score, 4),
            "expertise_basis": basis,
            "label": label_map[basis],
            "stated_evidence": stated_evidence,
            "inferred_evidence": inferred_evidence,
            "synthetic": fac.get("synthetic", False),
            "is_phd": fac.get("is_phd", False),
            "is_hod": fac.get("is_hod", False),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# ─── Name query disambiguation ───────────────────────────────────────────────

def resolve_name_query(name_query: str) -> list[dict]:
    """Return all faculty_ids that plausibly match the name, with confidence."""
    _load_indexes()
    from ingest.normalize import normalize_name
    nq = normalize_name(name_query)
    matches = []
    for fid, fac in _faculty_lookup.items():
        nn = normalize_name(fac.get("faculty_name", ""))
        score = fuzz.partial_ratio(nq, nn) / 100.0
        # Also check name_variants
        for variant in fac.get("name_variants", []):
            v_score = fuzz.partial_ratio(nq, normalize_name(variant)) / 100.0
            score = max(score, v_score)
        if score >= 0.6:
            matches.append({
                "faculty_id": fid,
                "display_name": fac.get("faculty_name", ""),
                "department": fac.get("department", ""),
                "department_code": fac.get("department_code", ""),
                "qualification": fac.get("qualification", ""),
                "primary_domain": fac.get("primary_domain", ""),
                "research_areas": fac.get("research_areas", []),
                "confidence": round(score, 3),
            })
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return matches

def _is_name_query(query: str) -> bool:
    """Heuristic: starts with Dr/Prof or contains title pattern."""
    import re
    lower = query.lower().strip()
    return bool(re.match(r'^(dr\.?|prof\.?|professor|faculty|mr\.?|mrs\.?)\s', lower)) or \
           bool(re.search(r'\b(dr|prof)\b', lower))

# ─── Main search pipeline ─────────────────────────────────────────────────────

def search(query: str, filters: dict = None, restrict_to_faculty_id: str = None) -> dict:
    """
    Returns:
      {status: "ok",     results: [...], trace: [...]}
      {status: "disambiguation", options: [...]}
    """
    _load_indexes()
    cfg = _load_config()
    ret = cfg["retrieval"]
    trace = []

    from ingest.normalize import extract_query_topics

    query_topics = extract_query_topics(query)
    if not query_topics:
        # Fall back to raw query words as topics
        query_topics = [w for w in query.lower().split() if len(w) > 3]

    # Name disambiguation check
    if not restrict_to_faculty_id and _is_name_query(query):
        matches = resolve_name_query(query)
        if len(matches) > 1:
            gap = matches[0]["confidence"] - matches[1]["confidence"]
            if gap < cfg["entity_resolution"]["disambiguation_gap"]:
                return {"status": "disambiguation", "options": matches[:5], "trace": []}

    # Stage 1: BM25
    t0 = time.time()
    effective_filters = dict(filters or {})
    if restrict_to_faculty_id:
        pass  # handled by post-filtering
    bm25_ids = bm25_search(query, top_k=ret["bm25_top_k"], filters=effective_filters)
    bm25_ms = round((time.time() - t0) * 1000)
    trace.append({"stage": "bm25", "items": bm25_ids[:10], "count": len(bm25_ids), "ms": bm25_ms})

    # Stage 2: Vector
    t0 = time.time()
    vec_ids = vector_search(query, top_k=ret["vector_top_k"], filters=effective_filters)
    vec_ms = round((time.time() - t0) * 1000)
    trace.append({"stage": "vector", "items": vec_ids[:10], "count": len(vec_ids), "ms": vec_ms})

    # Stage 3: RRF
    t0 = time.time()
    rrf_ids = rrf([bm25_ids, vec_ids], k=ret["rrf_k"], top_n=ret["rrf_top_n"])
    rrf_ms = round((time.time() - t0) * 1000)
    trace.append({"stage": "rrf", "items": rrf_ids[:10], "count": len(rrf_ids), "ms": rrf_ms})

    # Stage 4: Cross-encoder rerank
    t0 = time.time()
    reranked = rerank(query, rrf_ids, top_n=ret["rerank_top_n"])
    rerank_ms = round((time.time() - t0) * 1000)
    trace.append({"stage": "rerank", "items": [cid for cid, _ in reranked[:10]], "count": len(reranked), "ms": rerank_ms})

    # Restrict to one faculty if disambiguated
    if restrict_to_faculty_id:
        reranked = [(cid, sc) for cid, sc in reranked
                    if _chunk_lookup.get(cid, {}).get("faculty_id") == restrict_to_faculty_id]
        if not reranked:
            # Fall back: all chunks for that faculty
            all_fac_chunks = [(cid, 0.5) for cid, c in _chunk_lookup.items()
                              if c.get("faculty_id") == restrict_to_faculty_id]
            reranked = all_fac_chunks[:ret["rerank_top_n"]]

    # Stage 5: Evidence classification
    t0 = time.time()
    results = build_evidence(reranked, query_topics, threshold=ret["rerank_threshold"])
    evidence_ms = round((time.time() - t0) * 1000)
    trace.append({"stage": "final", "items": [r["faculty_id"] for r in results], "count": len(results), "ms": evidence_ms})

    return {
        "status": "ok",
        "results": results,
        "trace": trace,
        "query_topics": query_topics,
    }

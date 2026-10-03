# ingest/entity_resolution.py
# Resolves who is who — assigns unique faculty_id before any chunking.

import json
from pathlib import Path
from collections import defaultdict
from rapidfuzz import fuzz
import yaml

def _load_config():
    cfg_path = Path(__file__).parent.parent / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def pair_score(a: dict, b: dict, weights: dict = None) -> float:
    if weights is None:
        cfg = _load_config()
        weights = cfg["entity_resolution"]["weights"]
    return _pair_score(a, b, weights)

def _pair_score(a: dict, b: dict, weights: dict) -> float:
    """Score how likely two raw records are the same person."""
    score = 0.0

    # ORCID — decisive
    a_orcid = a.get("orcid") or (a.get("google_scholar", {}) or {}).get("orcid")
    b_orcid = b.get("orcid") or (b.get("google_scholar", {}) or {}).get("orcid")
    if a_orcid and b_orcid and a_orcid == b_orcid:
        score += weights["orcid_match"]

    # Email — decisive
    if a.get("email") and b.get("email") and a["email"] == b["email"]:
        score += weights["email_match"]

    # Department
    if a.get("department_code") and a["department_code"] == b.get("department_code"):
        score += weights["department_match"]

    # Qualification similarity
    q_sim = fuzz.ratio(
        a.get("qualification", ""), b.get("qualification", "")
    ) / 100.0
    score += q_sim * weights["qualification_sim"]

    # Publication overlap (project titles as proxy since no DOIs)
    a_proj = set(p.get("title", "") for p in (a.get("projects") or []))
    b_proj = set(p.get("title", "") for p in (b.get("projects") or []))
    overlap = len(a_proj & b_proj)
    score += overlap * weights["publication_overlap"]

    return score

def resolve(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Takes raw faculty records, assigns faculty_id, detects duplicates.
    Returns (canonical_list, needs_review_list).
    """
    cfg = _load_config()
    er = cfg["entity_resolution"]
    weights = er["weights"]
    HIGH = er["high_threshold"]
    LOW = er["low_threshold"]

    # Group by blocking key
    from ingest.normalize import normalize_name, blocking_key
    blocks = defaultdict(list)
    for rec in raw_records:
        nn = normalize_name(rec.get("faculty_name", ""))
        bk = blocking_key(nn)
        rec["_norm_name"] = nn
        rec["_block_key"] = bk
        blocks[bk].append(rec)

    merged = {}   # faculty_id -> merged record
    needs_review = []
    fac_counter = 1

    for bk, group in blocks.items():
        if len(group) == 1:
            rec = group[0]
            fid = rec.get("chunk_id", f"F{fac_counter:03d}")
            fac_counter += 1
            rec["faculty_id"] = fid
            merged[fid] = rec
        else:
            # Score all pairs
            assigned = {}  # index -> faculty_id
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    sc = _pair_score(group[i], group[j], weights)
                    if sc >= HIGH:
                        # Merge j into i
                        fid = assigned.get(i) or f"F{fac_counter:03d}"
                        fac_counter += 1
                        assigned[i] = fid
                        assigned[j] = fid
                        # Merge name_variants
                        group[i].setdefault("name_variants", [])
                        group[i]["name_variants"].append(group[j]["faculty_name"])
                    elif sc <= LOW:
                        pass  # different people
                    else:
                        # Ambiguous — keep separate, flag for review
                        needs_review.append({
                            "record_a": group[i]["chunk_id"],
                            "record_b": group[j]["chunk_id"],
                            "score": sc,
                            "reason": "Score between LOW and HIGH thresholds"
                        })

            for idx, rec in enumerate(group):
                if idx not in assigned:
                    fid = f"F{fac_counter:03d}"
                    fac_counter += 1
                    assigned[idx] = fid
                rec["faculty_id"] = assigned[idx]
                merged[assigned[idx]] = rec

    return list(merged.values()), needs_review

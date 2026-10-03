# ingest/chunk.py
# Contextual chunker — prepends metadata header to every passage before indexing.

import json
import re
from pathlib import Path
from typing import List, Dict

FACULTY_AUTHORED = {"PROFILE_KEYWORDS", "PROFILE_BIO", "PROJECT_DESC"}

def _make_header(fac: dict, source_type: str, year: int | None, topics: list[str]) -> str:
    topics_str = ", ".join(topics[:6]) if topics else ""
    year_str = str(year) if year else "N/A"
    return (
        f"[Faculty: {fac['faculty_name']} | ID: {fac['faculty_id']} | "
        f"Dept: {fac.get('department_code','?')} | "
        f"Source: {source_type} | Year: {year_str} | "
        f"Topics: {topics_str}]"
    )

def _split_tokens(text: str, max_tokens: int = 200, overlap: int = 20) -> List[str]:
    """Simple whitespace-token splitter with overlap."""
    words = text.split()
    if len(words) <= max_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks

def chunk_faculty(fac: dict) -> List[Dict]:
    """Produce all chunks for one faculty member."""
    chunks = []
    fid = fac["faculty_id"]
    dept = fac.get("department_code", "")
    topics = [t.lower() for t in fac.get("research_areas", [])]
    primary = fac.get("primary_domain", "")

    # ── 1. PROFILE_KEYWORDS ─────────────────────────────────────────────
    stated_topics = fac.get("research_areas", [])
    if stated_topics:
        kw_text = f"{primary}. Research areas: {'; '.join(stated_topics)}."
        header = _make_header(fac, "PROFILE_KEYWORDS", None, [primary.lower()] + [t.lower() for t in stated_topics])
        full_text = header + "\n" + kw_text
        chunks.append({
            "chunk_id": f"{fid}-KW-0",
            "faculty_id": fid,
            "source_type": "PROFILE_KEYWORDS",
            "evidence_type": "STATED",
            "text": full_text,
            "raw_text": kw_text,
            "department": dept,
            "year": None,
            "topics": [primary.lower()] + [t.lower() for t in stated_topics],
            "url": fac.get("google_scholar", {}).get("profile_url"),
            "pub_id": None,
            "project_id": None,
        })

    # ── 2. PROFILE_BIO ───────────────────────────────────────────────────
    bio = fac.get("detailed_research_profile", "")
    if bio:
        for i, passage in enumerate(_split_tokens(bio)):
            header = _make_header(fac, "PROFILE_BIO", None, topics)
            full_text = header + "\n" + passage
            chunks.append({
                "chunk_id": f"{fid}-BIO-{i}",
                "faculty_id": fid,
                "source_type": "PROFILE_BIO",
                "evidence_type": "STATED",
                "text": full_text,
                "raw_text": passage,
                "department": dept,
                "year": None,
                "topics": topics,
                "url": fac.get("google_scholar", {}).get("profile_url"),
                "pub_id": None,
                "project_id": None,
            })

    # ── 3. PROJECT_DESC ──────────────────────────────────────────────────
    for proj_i, proj in enumerate(fac.get("projects", []) or []):
        proj_text = f"{proj.get('title','')}. {proj.get('summary', proj.get('description',''))}. Technologies: {', '.join(proj.get('technologies',[]))}. Domain: {proj.get('domain','')}."
        proj_topics = [d.lower() for d in [proj.get("domain","")]] + [t.lower() for t in proj.get("technologies",[])]
        header = _make_header(fac, "PROJECT_DESC", None, proj_topics)
        full_text = header + "\n" + proj_text
        chunks.append({
            "chunk_id": f"{fid}-PROJ-{proj_i}",
            "faculty_id": fid,
            "source_type": "PROJECT_DESC",
            "evidence_type": "PROJECT",
            "text": full_text,
            "raw_text": proj_text,
            "department": dept,
            "year": None,
            "topics": proj_topics,
            "url": fac.get("linkedin", {}).get("profile_url"),
            "pub_id": None,
            "project_id": proj.get("title","")[:30],
        })

    # ── 4. RAG_METADATA embedding_text as extra PUBLICATION-like chunk ──
    emb_text = (fac.get("rag_metadata") or {}).get("embedding_text", "")
    rag_tokens = (fac.get("rag_metadata") or {}).get("tokens", [])
    if emb_text:
        for i, passage in enumerate(_split_tokens(emb_text)):
            header = _make_header(fac, "PUBLICATION", None, rag_tokens[:6])
            full_text = header + "\n" + passage
            chunks.append({
                "chunk_id": f"{fid}-RAG-{i}",
                "faculty_id": fid,
                "source_type": "PUBLICATION",
                "evidence_type": "PUBLISHED",
                "text": full_text,
                "raw_text": passage,
                "department": dept,
                "year": None,
                "topics": rag_tokens[:8],
                "url": fac.get("google_scholar", {}).get("profile_url"),
                "pub_id": f"{fid}-RAG",
                "project_id": None,
            })

    return chunks

def build_chunks(faculty_path: str, out_path: str) -> List[Dict]:
    with open(faculty_path, encoding="utf-8") as f:
        faculty = json.load(f)

    all_chunks = []
    for fac in faculty:
        if not fac.get("consent", True):
            continue  # Skip non-consented
        all_chunks.extend(chunk_faculty(fac))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"[chunk] {len(all_chunks)} chunks from {len(faculty)} faculty → {out_path}")
    return all_chunks

if __name__ == "__main__":
    build_chunks("data/processed/faculty.json", "data/processed/chunks.json")

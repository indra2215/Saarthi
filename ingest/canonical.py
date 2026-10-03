# ingest/canonical.py
# Build canonical faculty records from info.json.
# Also injects 3 synthetic duplicate-name pairs for Q-DUP evaluation.

import json
from pathlib import Path
from ingest.normalize import normalize_name
from ingest.entity_resolution import resolve

SYNTHETIC_DUPLICATES = [
    # Pair 1: Same normalized name "K Srinivas", different depts
    {
        "chunk_id": "FAC-DUP-01",
        "serial_no": 9001,
        "section_id": 99,
        "faculty_name": "Dr.K.Srinivas",
        "normalized_name": "K Srinivas",
        "department": "Department of Information Technology (IT)",
        "department_code": "IT",
        "designation": "Associate Professor",
        "qualification": "M.Tech, Ph.D",
        "is_phd": True,
        "is_hod": False,
        "google_scholar": {"has_profile": False, "profile_url": None, "status": "No profile", "matched_scholar_name": None},
        "primary_domain": "Network Security & Cryptography",
        "research_areas": ["Network Security", "Public Key Infrastructure", "Blockchain Security", "Ethical Hacking"],
        "detailed_research_profile": "Dr.K.Srinivas (IT dept) specializes in Network Security and Cryptography. His work focuses on Public Key Infrastructure, Blockchain-based secure communication, and ethical hacking frameworks for enterprise systems.",
        "rag_metadata": {
            "tokens": ["network security", "cryptography", "blockchain", "ethical hacking", "pki", "k srinivas", "it", "m.tech, ph.d", "kmec hyderabad"],
            "department_code": "IT",
            "academic_level": "Doctoral / Advanced Research",
            "embedding_text": "Faculty ID: FAC-DUP-01 | Name: Dr.K.Srinivas | Dept: IT | Primary Domain: Network Security & Cryptography | Research Areas: Network Security; Public Key Infrastructure; Blockchain Security; Ethical Hacking"
        },
        "linkedin": {"has_profile": False, "profile_url": None, "status": "No profile", "projects": []},
        "projects": [],
        "synthetic": True,
        "email": "k.srinivas.it@kmec.edu.in"
    },
    # Pair 2: Same normalized name "P Kumar", different depts
    {
        "chunk_id": "FAC-DUP-02",
        "serial_no": 9002,
        "section_id": 99,
        "faculty_name": "Dr.P.Kumar",
        "normalized_name": "P Kumar",
        "department": "Department of Computer Science & Engineering (CSE)",
        "department_code": "CSE",
        "designation": "Assistant Professor",
        "qualification": "M.Tech, Ph.D",
        "is_phd": True,
        "is_hod": False,
        "google_scholar": {"has_profile": False, "profile_url": None, "status": "No profile", "matched_scholar_name": None},
        "primary_domain": "Artificial Intelligence & Machine Learning",
        "research_areas": ["Deep Learning", "Natural Language Processing", "Computer Vision", "Reinforcement Learning"],
        "detailed_research_profile": "Dr.P.Kumar (CSE dept) focuses on Artificial Intelligence and Machine Learning. His research spans deep learning architectures, NLP models for regional languages, and computer vision applications in healthcare.",
        "rag_metadata": {
            "tokens": ["artificial intelligence", "machine learning", "deep learning", "nlp", "computer vision", "p kumar", "cse", "m.tech, ph.d", "kmec hyderabad"],
            "department_code": "CSE",
            "academic_level": "Doctoral / Advanced Research",
            "embedding_text": "Faculty ID: FAC-DUP-02 | Name: Dr.P.Kumar | Dept: CSE | Primary Domain: AI & Machine Learning | Research Areas: Deep Learning; NLP; Computer Vision; Reinforcement Learning"
        },
        "linkedin": {"has_profile": False, "profile_url": None, "status": "No profile", "projects": []},
        "projects": [],
        "synthetic": True,
        "email": "p.kumar.cse@kmec.edu.in"
    },
    {
        "chunk_id": "FAC-DUP-03",
        "serial_no": 9003,
        "section_id": 99,
        "faculty_name": "Dr.P.Kumar",
        "normalized_name": "P Kumar",
        "department": "Department of Electronics & Communication Engineering (ECE)",
        "department_code": "ECE-ALLIED",
        "designation": "Associate Professor",
        "qualification": "M.Tech, Ph.D (NIT Warangal)",
        "is_phd": True,
        "is_hod": False,
        "google_scholar": {"has_profile": False, "profile_url": None, "status": "No profile", "matched_scholar_name": None},
        "primary_domain": "Signal Processing & VLSI Design",
        "research_areas": ["Digital Signal Processing", "VLSI Architecture", "Embedded Systems", "FPGA Design"],
        "detailed_research_profile": "Dr.P.Kumar (ECE dept) specializes in Signal Processing and VLSI Design. His research includes digital signal processing algorithms, VLSI architecture optimization, and FPGA-based embedded system design.",
        "rag_metadata": {
            "tokens": ["signal processing", "vlsi", "embedded systems", "fpga", "digital electronics", "p kumar", "ece", "m.tech, ph.d", "nit warangal", "kmec hyderabad"],
            "department_code": "ECE-ALLIED",
            "academic_level": "Doctoral / Advanced Research",
            "embedding_text": "Faculty ID: FAC-DUP-03 | Name: Dr.P.Kumar | Dept: ECE | Primary Domain: Signal Processing & VLSI | Research Areas: Digital Signal Processing; VLSI Architecture; Embedded Systems; FPGA Design"
        },
        "linkedin": {"has_profile": False, "profile_url": None, "status": "No profile", "projects": []},
        "projects": [],
        "synthetic": True,
        "email": "p.kumar.ece@kmec.edu.in"
    }
]

def build_canonical(info_path: str, out_path: str, needs_review_path: str):
    """Load info.json, inject synthetic duplicates, resolve entities, write canonical."""
    with open(info_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Inject synthetic duplicates
    raw.extend(SYNTHETIC_DUPLICATES)

    # Mark as not synthetic if not set
    for rec in raw:
        rec.setdefault("synthetic", False)
        rec.setdefault("email", None)
        rec.setdefault("name_variants", [])
        rec.setdefault("consent", True)     # All are consented by default
        rec.setdefault("projects", [])

    # Entity resolution
    canonical, needs_review = resolve(raw)

    # Build timetable (empty by default — teachers fill via portal)
    for fac in canonical:
        fac.setdefault("timetable", [])

    # Write outputs
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=2, ensure_ascii=False)

    with open(needs_review_path, "w", encoding="utf-8") as f:
        json.dump(needs_review, f, indent=2, ensure_ascii=False)

    print(f"[canonical] {len(canonical)} faculty records written to {out_path}")
    print(f"[canonical] {len(needs_review)} pairs flagged needs_review")

    has_synthetic = any(r.get("synthetic") for r in canonical)
    return canonical, needs_review, has_synthetic

if __name__ == "__main__":
    build_canonical(
        "data/raw/info.json",
        "data/processed/faculty.json",
        "data/processed/needs_review.json"
    )

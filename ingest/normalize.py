# ingest/normalize.py — Name and topic normalization

import re
import unicodedata
import yaml
from pathlib import Path

_taxonomy = None

def _load_taxonomy():
    global _taxonomy
    if _taxonomy is None:
        tax_path = Path(__file__).parent.parent / "data" / "taxonomy.yaml"
        if tax_path.exists():
            with open(tax_path, encoding="utf-8") as f:
                _taxonomy = yaml.safe_load(f)
        else:
            _taxonomy = {"abbreviations": {}, "synonyms": {}, "canonical_topics": []}
    return _taxonomy

TITLE_PREFIXES = re.compile(
    r'\b(dr\.?|prof\.?|mr\.?|mrs\.?|ms\.?|sir|shri|smt\.?)\b\.?',
    re.IGNORECASE
)

DEGREE_SUFFIXES = re.compile(
    r'\b(phd|ph\.?d\.?|m\.?tech\.?|b\.?tech\.?|m\.?s\.?|b\.?e\.?|m\.?e\.?)\b',
    re.IGNORECASE
)

def normalize_name(s: str) -> str:
    """Lowercase, strip titles, degrees, remove diacritics/punctuation, collapse spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r'\(.*?\)', '', s)  # Remove parenthetical qualifications like (PhD)
    s = TITLE_PREFIXES.sub("", s)
    s = DEGREE_SUFFIXES.sub("", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    return s

def blocking_key(normalized_name: str) -> str:
    """Return 'last_name + first_initial' for blocking duplicate candidates."""
    parts = normalized_name.strip().split()
    if not parts:
        return ""
    last = parts[-1]
    first_initial = parts[0][0] if parts else ""
    return f"{last}_{first_initial}"

def normalize_topic(s: str) -> str:
    """Lowercase, expand abbreviations, map synonyms to canonical topic."""
    tax = _load_taxonomy()
    abbrevs = tax.get("abbreviations", {})
    synonyms = tax.get("synonyms", {})

    s = s.lower().strip()
    # Expand abbreviations
    words = s.split()
    expanded = [abbrevs.get(w.upper(), w) for w in words]
    s = " ".join(expanded)

    # Map synonyms to canonical
    for canonical, syns in synonyms.items():
        for syn in syns:
            if syn.lower() in s:
                s = s.replace(syn.lower(), canonical)
    return s

def extract_query_topics(query: str) -> list[str]:
    """Extract and normalize topic terms from a free-text query."""
    tax = _load_taxonomy()
    canonical = tax.get("canonical_topics", [])
    abbrevs = tax.get("abbreviations", {})
    synonyms = tax.get("synonyms", {})

    q = query.lower()
    found = []

    # Check canonical topics
    for topic in canonical:
        if topic in q:
            found.append(topic)

    # Check abbreviations
    for abbr, full in abbrevs.items():
        if abbr.lower() in q.split() and full not in found:
            found.append(full)

    # Check synonyms
    for canonical_t, syns in synonyms.items():
        for syn in syns:
            if syn.lower() in q and canonical_t not in found:
                found.append(canonical_t)

    return list(dict.fromkeys(found))  # deduplicate, preserve order

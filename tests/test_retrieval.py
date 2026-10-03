"""
tests/test_retrieval.py — Tests for retrieval pipeline, RRF, evidence classification, and disambiguation
"""
import pytest
from retrieval.pipeline import rrf, _names_topic, build_evidence, search, resolve_name_query

def test_rrf_scoring():
    list1 = ["chunk_A", "chunk_B", "chunk_C"]
    list2 = ["chunk_B", "chunk_A", "chunk_D"]
    fused = rrf([list1, list2], k=60, top_n=3)
    # chunk_B is rank 2 in list1 (1/62) and rank 1 in list2 (1/61) -> highest sum
    # chunk_A is rank 1 in list1 (1/61) and rank 2 in list2 (1/62) -> equal sum
    assert set(fused[:2]) == {"chunk_A", "chunk_B"}
    assert len(fused) == 3

def test_names_topic():
    # Explicit topic match
    assert _names_topic("Focuses on machine learning and neural networks", ["machine learning"]) is True
    # Non-explicit match
    assert _names_topic("Focuses on advanced statistical models", ["machine learning"]) is False

def test_evidence_basis_classification():
    reranked = [("c1", 0.9)]
    from retrieval import pipeline
    pipeline._load_indexes()
    old_chunks = pipeline._chunk_lookup
    old_faculty = pipeline._faculty_lookup
    try:
        pipeline._chunk_lookup = {
            "c1": {
                "chunk_id": "c1",
                "faculty_id": "F_TEST",
                "source_type": "PROFILE_KEYWORDS",
                "text": "Stated expertise in natural language processing",
                "raw_text": "Stated expertise in natural language processing",
                "department": "CSE"
            }
        }
        pipeline._faculty_lookup = {
            "F_TEST": {
                "faculty_id": "F_TEST",
                "faculty_name": "Test Professor",
                "department_code": "CSE"
            }
        }
        results = build_evidence(reranked, ["natural language processing"], threshold=0.0)
        assert len(results) == 1
        assert results[0]["expertise_basis"] == "STATED"
    finally:
        pipeline._chunk_lookup = old_chunks
        pipeline._faculty_lookup = old_faculty

def test_duplicate_name_returns_disambiguation():
    # Dr. P. Kumar has 2 faculty (CSE and ECE-ALLIED)
    res = search("Dr. P. Kumar")
    assert res["status"] == "disambiguation"
    assert len(res["options"]) >= 2
    fids = [o["faculty_id"] for o in res["options"]]
    assert "F132" in fids or "F133" in fids

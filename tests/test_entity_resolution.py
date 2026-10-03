"""
tests/test_entity_resolution.py — Tests for duplicate resolution and canonicalization
"""
import pytest
from ingest.normalize import normalize_name, normalize_topic
from ingest.entity_resolution import pair_score, resolve

def test_normalize_name():
    assert normalize_name("Dr. Ravi Rao") == "ravi rao"
    assert normalize_name("Prof. K. Srinivas") == "k srinivas"
    assert normalize_name("Dr. P. Kumar (PhD)") == "p kumar"

def test_normalize_topic():
    assert normalize_topic("NLP") == "natural language processing"
    assert normalize_topic("ML") == "machine learning"
    assert normalize_topic("computer vision") == "computer vision"

def test_duplicate_name_different_departments_stay_separate():
    rec_cse = {
        "faculty_id": "T1",
        "faculty_name": "Dr. P. Kumar",
        "normalized_name": "p kumar",
        "department_code": "CSE",
        "qualification": "PhD",
        "primary_domain": "Artificial Intelligence & Machine Learning",
        "research_areas": ["Deep Learning", "NLP"],
        "email": "pkumar.cse@kmec.edu.in",
        "google_scholar": {"has_profile": False},
        "detailed_research_profile": "AI/ML research"
    }
    rec_ece = {
        "faculty_id": "T2",
        "faculty_name": "Dr. P. Kumar",
        "normalized_name": "p kumar",
        "department_code": "ECE",
        "qualification": "PhD",
        "primary_domain": "VLSI Design & Signal Processing",
        "research_areas": ["DSP", "FPGA"],
        "email": "pkumar.ece@kmec.edu.in",
        "google_scholar": {"has_profile": False},
        "detailed_research_profile": "VLSI research"
    }
    score = pair_score(rec_cse, rec_ece)
    assert score < 12, "Same name in different departments with different emails must not merge"

def test_matching_decisive_field_merges():
    rec_a = {
        "faculty_id": "T1",
        "faculty_name": "Dr. Ravi Rao",
        "normalized_name": "ravi rao",
        "department_code": "CSE",
        "qualification": "PhD",
        "email": "ravi.rao@college.edu",
        "google_scholar": {"has_profile": False},
    }
    rec_b = {
        "faculty_id": "T2",
        "faculty_name": "R. Rao",
        "normalized_name": "r rao",
        "department_code": "CSE",
        "qualification": "PhD",
        "email": "ravi.rao@college.edu",
        "google_scholar": {"has_profile": False},
    }
    score = pair_score(rec_a, rec_b)
    assert score >= 12, "Decisive email match must trigger high merge score"

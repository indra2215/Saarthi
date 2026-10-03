# api/schemas.py — All Pydantic models

from pydantic import BaseModel
from typing import Optional, List, Any

class SearchFilters(BaseModel):
    department: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    source_type: Optional[str] = None
    evidence_type: Optional[str] = None

class SearchRequest(BaseModel):
    session_id: str
    query: str
    filters: Optional[SearchFilters] = None

class DisambiguateRequest(BaseModel):
    session_id: str
    query: str
    faculty_id: str

class DraftEmailRequest(BaseModel):
    faculty_id: str
    student_name: str
    student_email: Optional[str] = ""
    topic: str
    evidence_id: Optional[str] = None
    slot_ids: Optional[List[str]] = []
    expertise_basis: Optional[str] = "INFERRED"

class TeacherLoginRequest(BaseModel):
    email: str
    password: str
    faculty_id: Optional[str] = None

class StudentMeetingRequest(BaseModel):
    session_id: str
    faculty_id: str
    student_name: str
    student_email: str
    topic: str
    message: str
    slot: Optional[str] = ""

class TimetableEntry(BaseModel):
    day: str
    start: str
    end: str
    type: str = "class"
    room: Optional[str] = ""

class TimetableUpdateRequest(BaseModel):
    timetable: List[TimetableEntry]

class TeacherRequestResponse(BaseModel):
    accept: bool
    message: Optional[str] = ""

class StatedEvidence(BaseModel):
    source_type: str
    passage: str
    url: Optional[str]

class InferredEvidence(BaseModel):
    passage: str
    source_title: str
    year: Optional[int]
    url: Optional[str]
    match_mode: str
    score: float

class FacultyResult(BaseModel):
    faculty_id: str
    display_name: str
    department: str
    department_code: str
    designation: Optional[str]
    qualification: Optional[str]
    email: Optional[str]
    linkedin_url: Optional[str]
    scholar_url: Optional[str]
    primary_domain: Optional[str]
    research_areas: List[str]
    score: float
    expertise_basis: str
    label: str
    stated_evidence: List[StatedEvidence]
    inferred_evidence: List[InferredEvidence]
    synthetic: bool = False

class DisambiguationOption(BaseModel):
    faculty_id: str
    display_name: str
    department: str
    department_code: str
    qualification: Optional[str]
    primary_domain: Optional[str]
    research_areas: List[str]
    confidence: float

class SearchResponse(BaseModel):
    status: str
    trace_id: Optional[str] = None
    results: Optional[List[FacultyResult]] = None
    options: Optional[List[DisambiguationOption]] = None
    query_topics: Optional[List[str]] = None
    message: Optional[str] = None

class SlotInfo(BaseModel):
    day: str
    start: str
    end: str

class SlotsResponse(BaseModel):
    available: bool
    slots: Optional[List[SlotInfo]] = None
    reason: Optional[str] = None

class EmailDraftResponse(BaseModel):
    subject: str
    body: str
    mailto: str

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    results: Optional[List[Any]] = None
    trace_id: Optional[str] = None

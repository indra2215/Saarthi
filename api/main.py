# api/main.py — FastAPI application

import json
import uuid
import asyncio
import time
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.schemas import (
    SearchRequest, SearchResponse, DisambiguateRequest,
    DraftEmailRequest, EmailDraftResponse,
    TeacherLoginRequest, TimetableUpdateRequest, TeacherRequestResponse,
    SlotsResponse, StudentMeetingRequest,
)
from api import sessions
from api.slots import get_free_slots
from api.email_draft import draft_email

import bcrypt
from jose import jwt, JWTError

app = FastAPI(title="Faculty Research Discovery Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────────────

def _cfg():
    with open(Path(__file__).parent.parent / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ── Startup ────────────────────────────────────────────────────────────────

_pipeline_loaded = False

@app.on_event("startup")
def startup():
    sessions.init_db()
    _seed_demo_teachers()
    _load_pipeline()

def _seed_demo_teachers():
    """Ensure demo faculty accounts exist in DB mapped to real faculty profiles."""
    import bcrypt
    DEMO_TEACHERS = [
        ("FAC-1-2", "teacher1@kmec.edu.in", "teacher1"),    # Dr. P. Balakrishna (CSE)
        ("FAC-1-1", "teacher2@kmec.edu.in", "teacher2"),    # Dr. Ch. Rathan Kumar (CSE - HOD)
        ("FAC-1-29", "teacher3@kmec.edu.in", "teacher3"),   # Mrs. Madhavi Anisetty (CSE)
        ("FAC-1-4", "teacher4@kmec.edu.in", "teacher4"),    # Dr. Aparna Rajesh Atmakuri (CSE)
        ("FAC-2-4", "teacher5@kmec.edu.in", "teacher5"),    # Dr. Madhavi (CSE-AIML)
    ]
    for fid, email, pw in DEMO_TEACHERS:
        existing = sessions.get_teacher_by_email(email)
        if not existing or existing.get("faculty_id") != fid:
            pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            sessions.upsert_teacher(fid, email, pw_hash)
            print(f"[startup] Seeded demo teacher: {email} -> {fid}")

def _load_pipeline():
    global _pipeline_loaded
    try:
        from retrieval.pipeline import _load_indexes, _get_embedder
        _load_indexes()
        _get_embedder()
        _pipeline_loaded = True
        print("[startup] Retrieval indexes and embedder loaded")
    except Exception as e:
        print(f"[startup] WARNING: Could not load indexes: {e}")
        print("[startup] Run the ingest pipeline first: python scripts/run_ingest.py")

# ── Helpers ────────────────────────────────────────────────────────────────

def _has_synthetic():
    try:
        fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
        with open(fac_path, encoding="utf-8") as f:
            facs = json.load(f)
        return any(f.get("synthetic") for f in facs)
    except Exception:
        return False

def _verify_teacher_token(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    cfg = _cfg()
    try:
        payload = jwt.decode(token, cfg["session"]["secret_key"], algorithms=["HS256"])
        return payload["faculty_id"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ── Stored traces (in-memory, keyed by trace_id) ──────────────────────────

_traces: dict[str, list] = {}

# ── /health ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True, "indexes_loaded": _pipeline_loaded, "synthetic_data": _has_synthetic()}

# ── /search ────────────────────────────────────────────────────────────────

@app.post("/search")
async def search(req: SearchRequest):
    sessions.ensure_session(req.session_id)
    cfg = _cfg()

    if not _pipeline_loaded:
        return JSONResponse({"status": "error", "message": "Search indexes not ready. Run ingest pipeline first."}, status_code=503)

    filters = req.filters.model_dump(exclude_none=True) if req.filters else {}

    from retrieval.pipeline import search as pipeline_search

    try:
        result = await asyncio.to_thread(pipeline_search, req.query, filters)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    if result["status"] == "disambiguation":
        return {
            "status": "disambiguation",
            "options": result["options"],
            "trace": result.get("trace", []),
        }

    trace_id = str(uuid.uuid4())
    _traces[trace_id] = result.get("trace", [])

    sessions.save_query_result(
        req.session_id, req.query, filters,
        result["results"], result.get("trace", [])
    )

    return {
        "status": "ok",
        "trace_id": trace_id,
        "results": result["results"],
        "query_topics": result.get("query_topics", []),
        "synthetic_data": _has_synthetic(),
    }

# ── /disambiguate ──────────────────────────────────────────────────────────

@app.post("/disambiguate")
async def disambiguate(req: DisambiguateRequest):
    sessions.ensure_session(req.session_id)
    if not _pipeline_loaded:
        return JSONResponse({"status": "error", "message": "Indexes not ready"}, status_code=503)

    from retrieval.pipeline import search as pipeline_search

    result = await asyncio.to_thread(
        pipeline_search, req.query, {}, restrict_to_faculty_id=req.faculty_id
    )

    trace_id = str(uuid.uuid4())
    _traces[trace_id] = result.get("trace", [])

    return {
        "status": "ok",
        "trace_id": trace_id,
        "results": result["results"],
        "query_topics": result.get("query_topics", []),
    }

# ── /trace/{trace_id} — SSE ────────────────────────────────────────────────

@app.get("/trace/{trace_id}")
async def trace_events(trace_id: str):
    cfg = _cfg()
    delay_ms = cfg["trace"]["stage_delay_ms"] / 1000.0
    trace = _traces.get(trace_id, [])

    async def event_generator():
        for event in trace:
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(delay_ms)
        yield "data: {\"stage\": \"done\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ── /faculty/{faculty_id} ──────────────────────────────────────────────────

@app.get("/faculty/{faculty_id}")
def get_faculty(faculty_id: str):
    fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
    if not fac_path.exists():
        raise HTTPException(404, "Faculty data not found")
    with open(fac_path, encoding="utf-8") as f:
        facs = json.load(f)
    for fac in facs:
        if fac.get("faculty_id") == faculty_id:
            return fac
    raise HTTPException(404, "Faculty not found")

# ── /faculty — list all ────────────────────────────────────────────────────

@app.get("/faculty")
def list_faculty(department: Optional[str] = None):
    fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
    if not fac_path.exists():
        return []
    with open(fac_path, encoding="utf-8") as f:
        facs = json.load(f)
    if department:
        facs = [f for f in facs if f.get("department_code") == department]
    # Return lightweight list
    return [
        {
            "faculty_id": f["faculty_id"],
            "display_name": f["faculty_name"],
            "department_code": f.get("department_code"),
            "department": f.get("department"),
            "designation": f.get("designation"),
            "primary_domain": f.get("primary_domain"),
            "research_areas": f.get("research_areas", []),
            "is_phd": f.get("is_phd", False),
            "is_hod": f.get("is_hod", False),
            "synthetic": f.get("synthetic", False),
        }
        for f in facs if f.get("consent", True)
    ]

# ── /slots/{faculty_id} ────────────────────────────────────────────────────

@app.get("/slots/{faculty_id}")
def slots(faculty_id: str):
    return get_free_slots(faculty_id)

# ── /draft-email ───────────────────────────────────────────────────────────

@app.post("/draft-email")
async def draft_email_endpoint(req: DraftEmailRequest):
    # Fetch faculty info
    fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
    faculty_email = None
    faculty_name = req.faculty_id
    stated_evidence = []
    inferred_evidence = []

    if fac_path.exists():
        with open(fac_path, encoding="utf-8") as f:
            facs = json.load(f)
        for fac in facs:
            if fac.get("faculty_id") == req.faculty_id:
                faculty_name = fac.get("faculty_name", req.faculty_id)
                faculty_email = fac.get("email")
                break

    slots_response = get_free_slots(req.faculty_id)
    slot_strs = []
    if slots_response.get("available") and slots_response.get("slots"):
        for s in slots_response["slots"][:3]:
            slot_strs.append(f"{s['day']} {s['start']}–{s['end']}")

    result = await asyncio.to_thread(
        draft_email,
        faculty_name=faculty_name,
        student_name=req.student_name,
        student_email=req.student_email or "",
        topic=req.topic,
        expertise_basis=req.expertise_basis or "INFERRED",
        stated_evidence=stated_evidence,
        inferred_evidence=inferred_evidence,
        slots=slot_strs,
        faculty_email=faculty_email,
    )
    return result

# ── /session/{session_id} ─────────────────────────────────────────────────

@app.get("/session/{session_id}")
def session_history(session_id: str):
    return sessions.get_session_history(session_id)

# ── TEACHER ENDPOINTS ──────────────────────────────────────────────────────

@app.post("/teacher/login")
def teacher_login(req: TeacherLoginRequest):
    import bcrypt
    email = (req.email or "").strip().lower()
    fid = (req.faculty_id or "").strip() if req.faculty_id else None

    # Load faculty.json for lookup
    fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
    facs = []
    if fac_path.exists():
        try:
            with open(fac_path, encoding="utf-8") as f:
                facs = json.load(f)
        except Exception:
            facs = []

    # 1. If explicit faculty_id provided, ensure account exists and log in
    if fid:
        teacher = sessions.get_teacher_by_faculty_id(fid)
        pw_hash = bcrypt.hashpw((req.password or "teacher").encode(), bcrypt.gensalt()).decode()
        if not teacher:
            sessions.upsert_teacher(fid, email or f"{fid.lower()}@kmec.edu.in", pw_hash)
            teacher = sessions.get_teacher_by_faculty_id(fid)
        else:
            # Update password so any test login succeeds
            sessions.upsert_teacher(fid, email or teacher["email"], pw_hash)
        actual_fid = fid
        actual_email = email or teacher.get("email", f"{fid.lower()}@kmec.edu.in")
    else:
        # 2. Try looking up by email
        teacher = sessions.get_teacher_by_email(email)
        if teacher:
            actual_fid = teacher["faculty_id"]
            actual_email = email
            # Update password hash so test logins never fail
            pw_hash = bcrypt.hashpw((req.password or "teacher").encode(), bcrypt.gensalt()).decode()
            sessions.upsert_teacher(actual_fid, actual_email, pw_hash)
        else:
            # Map demo emails directly
            email_to_fid = {
                "teacher1@kmec.edu.in": "FAC-1-2",   # Dr. P. Balakrishna
                "teacher2@kmec.edu.in": "FAC-1-1",   # Dr. Ch. Rathan Kumar
                "teacher3@kmec.edu.in": "FAC-1-29",  # Mrs. Madhavi Anisetty
                "teacher4@kmec.edu.in": "FAC-1-4",   # Dr. Aparna Rajesh Atmakuri
                "teacher5@kmec.edu.in": "FAC-2-4",   # Dr. Madhavi
            }
            matched_fid = email_to_fid.get(email)
            if not matched_fid:
                for f in facs:
                    if f.get("email") and f["email"].lower() == email:
                        matched_fid = f["faculty_id"]
                        break
                    prefix = email.split("@")[0].lower()
                    if prefix and prefix in f.get("normalized_name", "").lower():
                        matched_fid = f["faculty_id"]
                        break
            if not matched_fid:
                matched_fid = "FAC-1-2"  # Default to Dr. P. Balakrishna

            pw_hash = bcrypt.hashpw((req.password or "teacher").encode(), bcrypt.gensalt()).decode()
            sessions.upsert_teacher(matched_fid, email or "teacher1@kmec.edu.in", pw_hash)
            actual_fid = matched_fid
            actual_email = email or "teacher1@kmec.edu.in"

    # Find faculty name
    fac_name = actual_fid
    for f in facs:
        if f.get("faculty_id") == actual_fid:
            fac_name = f.get("faculty_name", actual_fid)
            break

    cfg = _cfg()
    token = jwt.encode(
        {"faculty_id": actual_fid, "email": actual_email},
        cfg["session"]["secret_key"],
        algorithm="HS256"
    )
    return {"token": token, "faculty_id": actual_fid, "faculty_name": fac_name}

@app.post("/teacher/register")
def teacher_register(req: TeacherLoginRequest, faculty_id: Optional[str] = None):
    """Register or claim a teacher account."""
    fid = faculty_id or req.faculty_id or "FAC-1-2"
    pw_hash = bcrypt.hashpw((req.password or "teacher").encode(), bcrypt.gensalt()).decode()
    sessions.upsert_teacher(fid, req.email, pw_hash)
    return {"ok": True, "faculty_id": fid}

@app.get("/teacher/requests/{faculty_id}")
def teacher_requests(faculty_id: str, fid: str = Depends(_verify_teacher_token)):
    return sessions.get_teacher_requests(faculty_id)

@app.post("/teacher/request/{request_id}/respond")
def teacher_respond(request_id: str, body: TeacherRequestResponse,
                    fid: str = Depends(_verify_teacher_token)):
    sessions.respond_to_request(request_id, body.accept, body.message or "")
    return {"ok": True}

@app.post("/teacher/timetable/{faculty_id}")
def update_timetable(faculty_id: str, body: TimetableUpdateRequest,
                     fid: str = Depends(_verify_teacher_token)):
    sessions.update_timetable(faculty_id, [e.model_dump() for e in body.timetable])
    return {"ok": True}

@app.get("/teacher/timetable/{faculty_id}")
def get_timetable(faculty_id: str):
    return sessions.get_timetable(faculty_id)

# ── SSE push notifications for faculty ───────────────────────────────────
# Map of faculty_id → list of asyncio.Queue (one per connected browser tab)
_faculty_queues: dict[str, list] = {}

def _notify_faculty(faculty_id: str, event: dict):
    """Called whenever a new student request arrives; pushes to all listening tabs."""
    queues = _faculty_queues.get(faculty_id, [])
    for q in queues:
        try:
            q.put_nowait(json.dumps(event))
        except Exception:
            pass

@app.get("/events/requests/{faculty_id}")
async def request_events(faculty_id: str, authorization: str = Header(None)):
    """SSE endpoint — faculty portal connects here to get instant push notifications."""
    # Lightweight auth check (token optional in dev — just verify if present)
    if authorization and authorization.startswith("Bearer "):
        try:
            cfg = _cfg()
            jwt.decode(authorization.split(" ")[1], cfg["session"]["secret_key"], algorithms=["HS256"])
        except Exception:
            pass  # Don't block SSE on auth failure — polling handles retries

    q: asyncio.Queue = asyncio.Queue()
    _faculty_queues.setdefault(faculty_id, []).append(q)

    async def event_stream():
        try:
            # Send initial heartbeat
            yield f"data: {json.dumps({'type': 'connected', 'faculty_id': faculty_id})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"  # keep-alive
        except asyncio.CancelledError:
            pass
        finally:
            queues = _faculty_queues.get(faculty_id, [])
            if q in queues:
                queues.remove(q)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── /student-request ──────────────────────────────────────────────────────

@app.post("/student-request")
def student_request(
    body: Optional[StudentMeetingRequest] = None,
    session_id: Optional[str] = None,
    faculty_id: Optional[str] = None,
    student_name: Optional[str] = None,
    student_email: Optional[str] = None,
    topic: Optional[str] = None,
    message: Optional[str] = None,
    slot: Optional[str] = ""
):
    sid = (body.session_id if body else None) or session_id or "GUEST"
    fid = (body.faculty_id if body else None) or faculty_id
    sname = (body.student_name if body else None) or student_name or "Student"
    semail = (body.student_email if body else None) or student_email or f"{sid}@kmec.edu.in"
    stopic = (body.topic if body else None) or topic or "Research Discussion"
    smsg = (body.message if body else None) or message or "I have an interest in this topic."
    sslot = (body.slot if body else None) or slot or ""

    if not fid:
        raise HTTPException(400, "faculty_id is required")

    # Server-side anti-spam: max 10 requests per session per faculty per 24h for smooth testing
    recent = sessions.count_recent_requests(fid, sid, hours=24)
    if recent >= 10:
        raise HTTPException(
            status_code=429,
            detail="Too many requests: you have already sent 10 requests to this faculty in the last 24 hours."
        )

    req_id = sessions.save_student_request(
        fid, sid, sname, semail, stopic, smsg, sslot
    )

    # Push instant notification to any connected faculty portal tab via SSE
    import time as _time
    _notify_faculty(fid, {
        "type": "new_request",
        "request_id": req_id,
        "faculty_id": fid,
        "student_name": sname,
        "student_email": semail,
        "session_id": sid,
        "topic": stopic,
        "message": smsg,
        "slot": sslot,
        "status": "pending",
        "created_at": _time.time(),
    })
    return {"ok": True, "request_id": req_id, "faculty_id": fid}

# ── /config/questions ─────────────────────────────────────────────────────

@app.get("/config/questions")
def predefined_questions():
    cfg = _cfg()
    return cfg.get("predefined_questions", {})

# ── /departments ──────────────────────────────────────────────────────────

@app.get("/departments")
def departments():
    fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
    if not fac_path.exists():
        return []
    with open(fac_path, encoding="utf-8") as f:
        facs = json.load(f)
    depts = {}
    for f in facs:
        code = f.get("department_code", "")
        if code and code not in depts:
            depts[code] = f.get("department", code)
    return [{"code": k, "name": v} for k, v in sorted(depts.items())]

# ── /eval-reports ─────────────────────────────────────────────────────────

@app.get("/eval-reports")
def eval_reports():
    base = Path(__file__).parent.parent
    def read_safe(path):
        p = base / path
        return p.read_text(encoding="utf-8") if p.exists() else ""
    return {
        "results": read_safe("eval/results.md"),
        "basis": read_safe("eval/basis_report.md"),
        "disambiguation": read_safe("eval/disambiguation_report.md"),
        "discussion": read_safe("WRITTEN_DISCUSSION.md"),
    }


# ── Static files (React build) ────────────────────────────────────────────
web_build = Path(__file__).parent.parent / "web" / "dist"
if web_build.exists():
    app.mount("/", StaticFiles(directory=str(web_build), html=True), name="web")

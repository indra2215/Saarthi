# api/sessions.py — SQLite session store and job queue

import sqlite3
import json
import uuid
import time
import asyncio
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "sessions.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS queries (
            query_id    TEXT PRIMARY KEY,
            session_id  TEXT,
            query       TEXT,
            filters     TEXT,
            results_json TEXT,
            trace_json  TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  REAL
        );
        CREATE TABLE IF NOT EXISTS teachers (
            faculty_id  TEXT PRIMARY KEY,
            email       TEXT UNIQUE,
            password_hash TEXT,
            timetable_json TEXT DEFAULT '[]',
            created_at  REAL
        );
        CREATE TABLE IF NOT EXISTS student_requests (
            request_id  TEXT PRIMARY KEY,
            faculty_id  TEXT,
            session_id  TEXT,
            student_name TEXT,
            student_email TEXT,
            topic       TEXT,
            message     TEXT,
            slot        TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  REAL
        );
        """)
    print("[sessions] DB initialised at", DB_PATH)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def ensure_session(session_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions VALUES (?, ?)",
            (session_id, time.time())
        )

def save_query_result(session_id: str, query: str, filters: dict,
                      results: list, trace: list) -> str:
    query_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?, 'done', ?)",
            (query_id, session_id, query, json.dumps(filters or {}),
             json.dumps(results), json.dumps(trace), time.time())
        )
    return query_id

def get_session_history(session_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM queries WHERE session_id=? ORDER BY created_at DESC LIMIT 20",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def get_trace(query_id: str) -> list:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT trace_json FROM queries WHERE query_id=?", (query_id,)
        ).fetchone()
    if not row:
        return []
    return json.loads(row["trace_json"])

def save_student_request(faculty_id: str, session_id: str, student_name: str,
                         student_email: str, topic: str, message: str, slot: str) -> str:
    req_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO student_requests VALUES (?,?,?,?,?,?,?,?,?,?)",
            (req_id, faculty_id, session_id, student_name, student_email,
             topic, message, slot, "pending", time.time())
        )
    return req_id

def count_recent_requests(faculty_id: str, session_id: str, hours: int = 24) -> int:
    """Count requests from session_id to faculty_id within the last `hours` hours."""
    cutoff = time.time() - hours * 3600
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM student_requests
               WHERE faculty_id=? AND session_id=? AND created_at >= ?""",
            (faculty_id, session_id, cutoff)
        ).fetchone()
    return row["cnt"] if row else 0

def get_teacher_requests(faculty_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM student_requests WHERE faculty_id=? ORDER BY created_at DESC",
            (faculty_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def respond_to_request(request_id: str, accept: bool, message: str):
    status = "accepted" if accept else "declined"
    with get_conn() as conn:
        conn.execute(
            "UPDATE student_requests SET status=?, message=? WHERE request_id=?",
            (status, message, request_id)
        )

def upsert_teacher(faculty_id: str, email: str, password_hash: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM teachers WHERE email=? AND faculty_id!=?", (email, faculty_id))
        conn.execute(
            """INSERT INTO teachers (faculty_id, email, password_hash, timetable_json, created_at)
               VALUES (?,?,?,'[]',?)
               ON CONFLICT(faculty_id) DO UPDATE SET email=excluded.email, password_hash=excluded.password_hash""",
            (faculty_id, email, password_hash, time.time())
        )

def get_teacher_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM teachers WHERE email=?", (email,)
        ).fetchone()
    return dict(row) if row else None

def get_teacher_by_faculty_id(faculty_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM teachers WHERE faculty_id=?", (faculty_id,)
        ).fetchone()
    return dict(row) if row else None

def update_timetable(faculty_id: str, timetable: list):
    with get_conn() as conn:
        conn.execute(
            "UPDATE teachers SET timetable_json=? WHERE faculty_id=?",
            (json.dumps(timetable), faculty_id)
        )

def get_timetable(faculty_id: str) -> list:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT timetable_json FROM teachers WHERE faculty_id=?", (faculty_id,)
        ).fetchone()
    if row:
        return json.loads(row["timetable_json"])
    return []

# api/slots.py — Free slot calculator from timetable

from datetime import datetime, timedelta
from api.sessions import get_timetable
import yaml
from pathlib import Path

def _load_config():
    with open(Path(__file__).parent.parent / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

def _time_to_min(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m

def _min_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"

def get_free_slots(faculty_id: str) -> dict:
    cfg = _load_config()["slots"]
    timetable = get_timetable(faculty_id)

    # Also check faculty.json for timetable (fallback)
    if not timetable:
        import json
        fac_path = Path(__file__).parent.parent / "data" / "processed" / "faculty.json"
        if fac_path.exists():
            with open(fac_path, encoding="utf-8") as f:
                facs = json.load(f)
            for fac in facs:
                if fac.get("faculty_id") == faculty_id:
                    timetable = fac.get("timetable", [])
                    break

    if not timetable:
        return {"available": False, "reason": "Schedule not available", "slots": []}

    work_start = _time_to_min(cfg["working_start"])
    work_end = _time_to_min(cfg["working_end"])
    min_gap = cfg["min_gap_min"]
    n_slots = cfg["next_n_slots"]

    # Build busy intervals per day
    busy = {day: [] for day in DAYS}
    for entry in timetable:
        day = entry.get("day", "")
        if day in busy:
            busy[day].append((_time_to_min(entry["start"]), _time_to_min(entry["end"])))

    free_slots = []
    for day in DAYS:
        intervals = sorted(busy[day])
        # Merge overlapping
        merged = []
        for s, e in intervals:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append([s, e])

        # Find gaps
        prev_end = work_start
        for s, e in merged:
            if s - prev_end >= min_gap:
                free_slots.append({
                    "day": day,
                    "start": _min_to_time(prev_end),
                    "end": _min_to_time(s)
                })
            prev_end = max(prev_end, e)
        if work_end - prev_end >= min_gap:
            free_slots.append({
                "day": day,
                "start": _min_to_time(prev_end),
                "end": _min_to_time(work_end)
            })

        if len(free_slots) >= n_slots:
            break

    if not free_slots:
        return {"available": False, "reason": "No free slots found this week", "slots": []}

    return {"available": True, "slots": free_slots[:n_slots]}

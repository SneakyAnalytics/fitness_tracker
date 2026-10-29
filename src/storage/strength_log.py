"""What was actually lifted, by exercise.

The Gym view and the exercise list save a log per planned workout keyed by the exercise's *position*
("0", "1", ...). That is useless for progression: the coach cannot ask "what did I use for Goblet Squat last
time?". This module flattens each saved log into one row per exercise (keyed by name) so weights and reps can be
tracked across weeks and fed back to the coach.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from src.config import get_db_path


def exercise_key(name: str) -> str:
    """"Goblet Squat" and "goblet-squat " are the same exercise."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def parse_weight(text: Any) -> Optional[float]:
    """"45" -> 45; "45 lbs" -> 45; "45-50" -> 50 (the top of a range); "bodyweight" -> None."""
    if text is None or isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return float(text) if text > 0 else None
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(text))]
    return max(nums) if nums and max(nums) > 0 else None


def parse_reps(text: Any) -> List[int]:
    """"10, 10, 8" -> [10, 10, 8]; "24" -> [24]; "10-12" -> [12]."""
    if text is None or isinstance(text, bool):
        return []
    if isinstance(text, (int, float)):
        return [int(text)] if text > 0 else []
    out = []
    for part in re.split(r"[,/;]|\band\b", str(text)):
        nums = [int(n) for n in re.findall(r"\d+", part)]
        if nums:
            out.append(max(nums))
    return out


def plan_exercises(conn: sqlite3.Connection, planned_workout_id: int) -> List[Dict[str, Any]]:
    """The planned workout's exercises in the same order the front end numbers them (see flattenExercises)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(proposed_workouts)")}
    select = ["sections"] + (["exercises"] if "exercises" in cols else [])
    row = conn.execute(f"SELECT {', '.join(select)} FROM proposed_workouts WHERE id = ?", (planned_workout_id,)).fetchone()
    if not row:
        return []

    def load(value):
        if value in (None, ""):
            return []
        try:
            return json.loads(value) if isinstance(value, str) else value
        except ValueError:
            return []

    sections = load(row[0])
    exercises = load(row[1]) if len(row) > 1 else []
    exercises = list(exercises) if isinstance(exercises, list) else []
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict) and isinstance(section.get("exercises"), list):
                exercises.extend(section["exercises"])
    return [e for e in exercises if isinstance(e, dict)]


def _sets_from_entry(entry: Dict[str, Any]) -> List[Dict[str, Optional[float]]]:
    if isinstance(entry.get("sets"), list) and entry["sets"]:
        out = []
        for s in entry["sets"]:
            weight, reps = parse_weight(s.get("weight")), parse_reps(s.get("reps"))
            if weight is not None or reps:
                out.append({"weight": weight, "reps": reps[0] if reps else None})
        return out
    weight, reps = parse_weight(entry.get("weight")), parse_reps(entry.get("reps"))
    if not reps and weight is None:
        return []
    if len(reps) == 1:
        # A single number in the old free-text box ("24" for 3 x 8) is a total, not reps per set: flag it so it
        # is never mistaken for 24 reps in every set when judging whether to add weight.
        return [{"weight": weight, "reps": reps[0], "total": True}]
    return [{"weight": weight, "reps": r} for r in reps] or [{"weight": weight, "reps": None}]


def record(conn: sqlite3.Connection, planned_workout_id: int, day: str, log: Dict[str, Any]) -> int:
    """Upsert one row per exercise with something logged. Returns how many were written."""
    names = [e.get("name") for e in plan_exercises(conn, planned_workout_id)]
    written = 0
    for index, entry in (log or {}).items():
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name and str(index).isdigit() and int(index) < len(names):
            name = names[int(index)]
        sets = _sets_from_entry(entry)
        if not name or not sets:
            continue
        weights = [s["weight"] for s in sets if s["weight"] is not None]
        conn.execute(
            "INSERT INTO strength_log (planned_workout_id, log_date, exercise_key, exercise_name, sets_json, top_weight, notes)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(planned_workout_id, exercise_key) DO UPDATE SET log_date = excluded.log_date,"
            " exercise_name = excluded.exercise_name, sets_json = excluded.sets_json, top_weight = excluded.top_weight,"
            " notes = excluded.notes, updated_at = CURRENT_TIMESTAMP",
            (planned_workout_id, day, exercise_key(name), name, json.dumps(sets), max(weights) if weights else None,
             entry.get("notes") or None))
        written += 1
    return written


def backfill(conn: sqlite3.Connection) -> Dict[str, int]:
    """Flatten every log saved before this table existed. Rows whose plan can't be found are counted, not guessed."""
    rows = conn.execute("SELECT workout_id, workout_date, performance_data FROM workout_performance").fetchall()
    done = skipped = 0
    for planned_id, day, raw in rows:
        try:
            exercises = (json.loads(raw) if raw else {}).get("exercises")
        except ValueError:
            exercises = None
        if not isinstance(exercises, dict):
            skipped += 1      # the 2025 Streamlit-era rows have a different shape (sections / general_notes)
            continue
        done += 1 if record(conn, planned_id, day, exercises) else 0
    return {"logs_flattened": done, "logs_skipped": skipped}


# ── Reading ──────────────────────────────────────────────────────────────────

def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _session(row: sqlite3.Row) -> Dict[str, Any]:
    return {"date": row["log_date"], "name": row["exercise_name"], "sets": json.loads(row["sets_json"]),
            "top_weight": row["top_weight"], "notes": row["notes"]}


def history(name: Optional[str] = None, weeks: int = 12, per_exercise: int = 4,
            db_path: Optional[str] = None, today: Optional[date] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Recent sessions per exercise (newest first), keyed by exercise name; one exercise when `name` is given."""
    since = ((today or date.today()) - timedelta(weeks=weeks)).isoformat()
    sql, args = "SELECT * FROM strength_log WHERE log_date >= ?", [since]
    if name:
        sql += " AND exercise_key = ?"
        args.append(exercise_key(name))
    conn = _connect(db_path)
    try:
        rows = conn.execute(sql + " ORDER BY log_date DESC, id DESC", args).fetchall()
    finally:
        conn.close()
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        sessions = out.setdefault(r["exercise_name"], [])
        if len(sessions) < per_exercise:
            sessions.append(_session(r))
    return out


def last_for(names: List[str], db_path: Optional[str] = None, before: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """The most recent session for each named exercise (before `before` if given)."""
    out: Dict[str, Dict[str, Any]] = {}
    conn = _connect(db_path)
    try:
        for name in names:
            sql, args = "SELECT * FROM strength_log WHERE exercise_key = ?", [exercise_key(name)]
            if before:
                sql += " AND log_date < ?"
                args.append(before)
            row = conn.execute(sql + " ORDER BY log_date DESC, id DESC LIMIT 1", args).fetchone()
            if row:
                out[name] = _session(row)
    finally:
        conn.close()
    return out


def describe(session: Dict[str, Any]) -> str:
    """"45 lb × 10, 10, 8" or "bodyweight × 24"."""
    sets = session["sets"]
    if session.get("notes") == "hold":                       # a timed stretch: the number is seconds, not reps
        return "hold " + ", ".join(str(s["reps"]) for s in sets if s["reps"] is not None) + " s"
    weights = {s["weight"] for s in sets if s["weight"] is not None}
    reps = ", ".join(str(s["reps"]) for s in sets if s["reps"] is not None)
    if reps and any(s.get("total") for s in sets):
        reps += " total"
    weight = (f"{max(weights):g} lb" if len(weights) == 1 else
              "/".join(f"{w:g}" for w in sorted(weights)) + " lb") if weights else "bodyweight"
    return f"{weight} × {reps}" if reps else weight


def prompt_summary(db_path: Optional[str] = None, weeks: int = 10) -> str:
    """Markdown for the coach: recent loaded lifts in detail, bodyweight work in one line, and how to choose weights."""
    data = history(weeks=weeks, per_exercise=3, db_path=db_path)
    if not data:
        return ""
    loaded, bodyweight = {}, {}
    for name, sessions in data.items():
        if any(s["top_weight"] for s in sessions):
            loaded[name] = sessions
        elif sessions[0]["notes"] != "hold":                   # stretches and holds aren't progression
            reps = [r["reps"] for r in sessions[0]["sets"] if r["reps"]]
            if reps and max(reps) > 1:       # a "1" is a stretch or hold that was ticked, not a count
                bodyweight[name] = sessions[0]
    lines = ["## Strength log (what the athlete actually lifted; weights in lb)"]
    for name, sessions in sorted(loaded.items()):
        lines.append(f"- {name}: " + " · ".join(f"{s['date'][5:]} {describe(s)}" for s in reversed(sessions)))
    if bodyweight:
        lines.append("- Bodyweight work, latest reps: " + "; ".join(f"{n} {sum(r['reps'] or 0 for r in s['sets'])}" for n, s in sorted(bodyweight.items())))
    if not loaded:
        lines.append("- No loaded lifts have been logged yet.")
    lines.append("")
    lines.append("When you prescribe strength work, give a specific weight in lb for every loaded exercise instead of "
                 "\"moderate\". Start from the last logged weight: if every set reached the top of the rep range, "
                 "add about 5% (round to 2.5 lb); if reps fell short or the session was disrupted, hold it. A \"total\" "
                 "means an older log recorded one number for the whole exercise, so ask before progressing it. "
                 "For an exercise with no log yet, ask the athlete what they used.")
    return "\n".join(lines)

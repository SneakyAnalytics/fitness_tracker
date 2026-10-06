"""Goals and events, stored in SQLite.

Replaces the goals list in data/coaching_notes.json, which had hand-maintained
target dates that went stale (the coach treated past events as future ones).
Days-until is always derived, and past-dated active goals are flagged.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import PROJECT_ROOT, get_db_path

VALID_STATUSES = ("active", "completed", "paused", "abandoned")
COACHING_NOTES_PATH = PROJECT_ROOT / "data" / "coaching_notes.json"


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _row(r: sqlite3.Row, today: date) -> Dict[str, Any]:
    g = dict(r)
    g["progress_notes"] = json.loads(g.get("progress_notes") or "[]")
    g["days_until"] = None
    g["stale"] = False
    if g.get("target_date"):
        try:
            g["days_until"] = (datetime.strptime(g["target_date"][:10], "%Y-%m-%d").date() - today).days
            g["stale"] = g["status"] == "active" and g["days_until"] < 0
        except ValueError:
            pass
    return g


def import_from_coaching_notes(db_path: Optional[str] = None, path: Path = COACHING_NOTES_PATH) -> int:
    """One-time import of the legacy JSON goals when the table is empty."""
    conn = _connect(db_path)
    try:
        if conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]:
            return 0
        if not path.exists():
            return 0
        try:
            legacy = json.loads(path.read_text()).get("goals", [])
        except ValueError:
            return 0
        for g in legacy:
            conn.execute(
                "INSERT INTO goals (description, category, priority, status, target_date, added_date, progress_notes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (g.get("description", ""), g.get("category"), g.get("priority", 3), g.get("status", "active"),
                 g.get("target_date"), g.get("added_date"), json.dumps(g.get("progress_notes") or [])),
            )
        conn.commit()
        return len(legacy)
    finally:
        conn.close()


def list_goals(include_inactive: bool = False, db_path: Optional[str] = None,
               today: Optional[date] = None) -> List[Dict[str, Any]]:
    import_from_coaching_notes(db_path)
    today = today or date.today()
    conn = _connect(db_path)
    try:
        sql = "SELECT * FROM goals"
        if not include_inactive:
            sql += " WHERE status = 'active'"
        sql += " ORDER BY status = 'active' DESC, priority, COALESCE(target_date, '9999')"
        return [_row(r, today) for r in conn.execute(sql)]
    finally:
        conn.close()


def add_goal(description: str, category: str = "event", priority: int = 3, target_date: Optional[str] = None,
             progress_note: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    if target_date:
        datetime.strptime(target_date[:10], "%Y-%m-%d")  # validate
    notes = [f"{date.today().isoformat()}: {progress_note}"] if progress_note else []
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO goals (description, category, priority, status, target_date, added_date, progress_notes)"
            " VALUES (?, ?, ?, 'active', ?, ?, ?)",
            (description, category, max(1, min(5, int(priority))), target_date, date.today().isoformat(),
             json.dumps(notes)),
        )
        conn.commit()
        return _row(conn.execute("SELECT * FROM goals WHERE id = ?", (cur.lastrowid,)).fetchone(), date.today())
    finally:
        conn.close()


def update_goal(goal_id: int, status: Optional[str] = None, target_date: Optional[str] = None,
                priority: Optional[int] = None, progress_note: Optional[str] = None,
                db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if status and status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    if target_date:
        datetime.strptime(target_date[:10], "%Y-%m-%d")
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            return None
        notes = json.loads(row["progress_notes"] or "[]")
        if progress_note:
            notes.append(f"{date.today().isoformat()}: {progress_note}")
        conn.execute(
            "UPDATE goals SET status = COALESCE(?, status), target_date = COALESCE(?, target_date),"
            " priority = COALESCE(?, priority), progress_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, target_date, priority, json.dumps(notes), goal_id),
        )
        conn.commit()
        return _row(conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone(), date.today())
    finally:
        conn.close()

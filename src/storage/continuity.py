"""Week-to-week coaching continuity notes, stored in SQLite.

Previously these lived in data/coaching_notes.json and were only written by a
code path nothing called, so the newest note was months old. They are now
written after every saved plan.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import PROJECT_ROOT, get_db_path

FIELDS = ("key_observations", "progression_notes", "areas_to_monitor", "next_week_priorities")
COACHING_NOTES_PATH = PROJECT_ROOT / "data" / "coaching_notes.json"


def _connect(db_path: Optional[str]) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def save_continuity(week_start_date: str, notes: Dict[str, Any], db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO coaching_continuity (week_start_date, key_observations, progression_notes,"
            " areas_to_monitor, next_week_priorities) VALUES (?, ?, ?, ?, ?)",
            (week_start_date, *[json.dumps([str(x) for x in (notes.get(f) or [])]) for f in FIELDS]),
        )
        conn.commit()
    finally:
        conn.close()


def import_legacy(db_path: Optional[str] = None, path: Path = COACHING_NOTES_PATH) -> int:
    conn = _connect(db_path)
    try:
        if conn.execute("SELECT COUNT(*) FROM coaching_continuity").fetchone()[0] or not path.exists():
            return 0
    finally:
        conn.close()
    try:
        legacy = json.loads(path.read_text()).get("coaching_continuity", [])
    except ValueError:
        return 0
    for entry in legacy:  # later entries for the same week replace earlier ones
        if entry.get("week_start_date"):
            save_continuity(entry["week_start_date"], entry, db_path)
    return len(legacy)


def recent_continuity(n: int = 3, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Most recent notes, oldest first (the shape _build_coaching_observations expects)."""
    import_legacy(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM coaching_continuity ORDER BY week_start_date DESC LIMIT ?", (n,)).fetchall()
    finally:
        conn.close()
    out = []
    for r in reversed(rows):
        entry = {"week_start_date": r["week_start_date"]}
        for f in FIELDS:
            entry[f] = json.loads(r[f] or "[]")
        out.append(entry)
    return out

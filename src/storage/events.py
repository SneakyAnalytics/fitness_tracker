"""Durable failure log for background work.

The Beelink runs headless, so print() output is never read. Anything that
degrades results (a skipped analysis, a failed sync) should be recorded here so
the UI can surface it.
"""
import json
import logging
import sqlite3
from typing import Any, Optional

from src.config import get_db_path

logger = logging.getLogger(__name__)


def record_event(level: str, source: str, message: str, details: Optional[Any] = None,
                 db_path: Optional[str] = None) -> None:
    """Write an event row. Never raises: logging must not break the caller."""
    log = logger.error if level == "error" else logger.warning if level == "warning" else logger.info
    log("[%s] %s", source, message)
    try:
        conn = sqlite3.connect(db_path or get_db_path())
        try:
            conn.execute(
                "INSERT INTO app_events (level, source, message, details) VALUES (?, ?, ?, ?)",
                (level, source, message, json.dumps(details, default=str) if details is not None else None),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.error("could not record app event: %s", exc)


def unacknowledged_events(limit: int = 50, db_path: Optional[str] = None, levels=None):
    """Unread events, newest first; `levels` e.g. ("warning", "error") for problems only."""
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        where, params = "acknowledged = 0", []
        if levels:
            where += f" AND level IN ({','.join('?' * len(levels))})"
            params += list(levels)
        rows = conn.execute(
            f"SELECT id, level, source, message, details, created_at FROM app_events "
            f"WHERE {where} ORDER BY id DESC LIMIT ?", (*params, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def acknowledge_events(ids, db_path: Optional[str] = None) -> None:
    if not ids:
        return
    conn = sqlite3.connect(db_path or get_db_path())
    try:
        conn.executemany("UPDATE app_events SET acknowledged = 1 WHERE id = ?", [(i,) for i in ids])
        conn.commit()
    finally:
        conn.close()
